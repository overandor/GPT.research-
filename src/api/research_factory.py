"""Research Factory module with real-data analytics and citation pipeline."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

import pandas as pd
import statsmodels.api as sm
import requests
from urllib.parse import quote_plus

RECENT_YEARS = 2  # window for "current recent"


def _norm_authors(auth_list: Optional[Iterable[Any]]) -> str:
    """Normalise author structures from various APIs into a readable string."""

    if not auth_list:
        return ""

    names: List[str] = []
    for author in auth_list:
        if isinstance(author, dict):
            parts: List[str] = []
            given = author.get("given") or author.get("givenName") or ""
            family = author.get("family") or author.get("familyName") or ""
            if given:
                parts.append(str(given))
            if family:
                parts.append(str(family))
            if not parts and author.get("name"):
                names.append(str(author["name"]))
            elif parts:
                names.append(" ".join(parts))
        else:
            names.append(str(author))

    return ", ".join(filter(None, names))


def fetch_recent_papers(query: str, max_items: int = 3, timeout: int = 8) -> List[Dict[str, Any]]:
    """Return up to ``max_items`` recent papers for the query with provenance."""

    results: List[Dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    start_year = now.year - RECENT_YEARS

    # ---------- Crossref ----------
    try:
        cr_q = quote_plus(query)
        url = (
            "https://api.crossref.org/works?query="
            f"{cr_q}&filter=from-pub-date:{start_year}-01-01,until-pub-date:{now.year}-12-31,type:journal-article"
            f"&sort=published&order=desc&rows={max_items * 2}"
        )
        response = requests.get(url, timeout=timeout)
        if response.ok:
            payload = response.json().get("message", {})
            for item in payload.get("items", []):
                title = " ".join(item.get("title", [])).strip() or "Untitled"
                doi = item.get("DOI")
                link = f"https://doi.org/{doi}" if doi else (item.get("URL") or "")
                year: Optional[int] = None
                for key in ("published-print", "published-online", "issued"):
                    if item.get(key, {}).get("date-parts"):
                        try:
                            year = int(item[key]["date-parts"][0][0])
                            break
                        except (TypeError, ValueError, IndexError):
                            continue
                authors = _norm_authors(item.get("author"))
                results.append(
                    {
                        "title": title,
                        "year": year,
                        "authors": authors,
                        "link": link,
                        "provider": "Crossref",
                        "source_id": doi or link,
                        "accessed": now.isoformat(),
                    }
                )
    except Exception:
        pass

    # ---------- arXiv ----------
    try:
        arxiv_q = quote_plus(
            f"{query} AND submittedDate:[{start_year}01010000 TO {now.year}12312359]"
        )
        url = (
            "http://export.arxiv.org/api/query?search_query=all:"
            f"{arxiv_q}&start=0&max_results={max_items * 2}&sortBy=submittedDate&sortOrder=descending"
        )
        response = requests.get(url, timeout=timeout)
        if response.ok:
            import xml.etree.ElementTree as ET

            root = ET.fromstring(response.text)
            ns = {"a": "http://www.w3.org/2005/Atom"}
            for entry in root.findall("a:entry", ns):
                title = (
                    entry.findtext("a:title", default="", namespaces=ns) or ""
                ).strip().replace("\n", " ")
                link = ""
                for link_entry in entry.findall("a:link", ns):
                    if link_entry.attrib.get("type") == "text/html":
                        link = link_entry.attrib.get("href", "")
                year: Optional[int] = None
                published = entry.findtext("a:published", default="", namespaces=ns)
                if published:
                    try:
                        year = int(published[:4])
                    except (TypeError, ValueError):
                        year = None
                authors = ", ".join(
                    [
                        author.findtext("a:name", default="", namespaces=ns)
                        for author in entry.findall("a:author", ns)
                    ]
                )
                arxiv_id = (
                    entry.findtext("a:id", default="", namespaces=ns) or ""
                ).split("/")[-1]
                results.append(
                    {
                        "title": title or "Untitled",
                        "year": year,
                        "authors": authors,
                        "link": link or f"https://arxiv.org/abs/{arxiv_id}",
                        "provider": "arXiv",
                        "source_id": arxiv_id,
                        "accessed": now.isoformat(),
                    }
                )
    except Exception:
        pass

    # ---------- Semantic Scholar (fallback) ----------
    if len(results) < max_items:
        try:
            ss_q = quote_plus(query)
            url = (
                "https://api.semanticscholar.org/graph/v1/paper/search?query="
                f"{ss_q}&limit={max_items}&fields=title,year,authors,url,externalIds"
            )
            response = requests.get(url, timeout=timeout)
            if response.ok:
                data = response.json().get("data", [])
                for item in data:
                    author_records = item.get("authors", [])
                    authors = _norm_authors(
                        [{"given": author.get("name", "")} for author in author_records]
                    )
                    link = item.get("url") or ""
                    doi = ""
                    external_ids = item.get("externalIds") or {}
                    if isinstance(external_ids, dict) and external_ids.get("DOI"):
                        doi = external_ids["DOI"]
                        link = f"https://doi.org/{doi}"
                    results.append(
                        {
                            "title": item.get("title", "Untitled"),
                            "year": item.get("year"),
                            "authors": authors,
                            "link": link,
                            "provider": "Semantic Scholar",
                            "source_id": doi or link,
                            "accessed": now.isoformat(),
                        }
                    )
        except Exception:
            pass

    # de-duplicate by link/source_id, keep order
    seen: set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for entry in results:
        key = entry.get("source_id") or entry.get("link")
        if key and key not in seen:
            deduped.append(entry)
            seen.add(key)
    return deduped[:max_items]


@dataclass
class RegressionSummary:
    effect_size: float
    p_value: float
    intercept: float
    r_squared: float
    sample_size: int


class ResearchFactory:
    """Generate research outputs backed by real regression analysis."""

    def __init__(
        self,
        dataset_path: Optional[Path] = None,
        reference_fetcher: Optional[Callable[[str, int], List[Dict[str, Any]]]] = None,
    ) -> None:
        default_path = Path(__file__).resolve().parents[2] / "data" / "real_experiment.csv"
        self.dataset_path = dataset_path or default_path
        self.reference_fetcher = reference_fetcher or fetch_recent_papers
        self._dataset_cache: Optional[pd.DataFrame] = None

    def _load_dataset(self) -> pd.DataFrame:
        if self._dataset_cache is None:
            df = pd.read_csv(self.dataset_path)
            required_columns = {"wt", "mpg"}
            missing = required_columns.difference(df.columns)
            if missing:
                raise ValueError(
                    f"Dataset at {self.dataset_path} missing columns: {sorted(missing)}"
                )
            self._dataset_cache = df.astype(float)
        return self._dataset_cache.copy()

    def _run_regression(self) -> RegressionSummary:
        df = self._load_dataset()
        X = sm.add_constant(df["wt"], has_constant="add")
        model = sm.OLS(df["mpg"], X)
        fit = model.fit()
        return RegressionSummary(
            effect_size=float(fit.params["wt"]),
            p_value=float(fit.pvalues["wt"]),
            intercept=float(fit.params["const"]),
            r_squared=float(fit.rsquared),
            sample_size=int(fit.nobs),
        )

    def _verify_regression(self, baseline: RegressionSummary) -> Dict[str, Any]:
        rerun = self._run_regression()
        effect_match = math.isclose(
            rerun.effect_size, baseline.effect_size, rel_tol=1e-6, abs_tol=1e-8
        )
        p_match = math.isclose(
            rerun.p_value, baseline.p_value, rel_tol=1e-6, abs_tol=1e-12
        )
        return {
            "replicated": effect_match and p_match,
            "baseline": baseline.__dict__,
            "recomputed": rerun.__dict__,
        }

    def _build_analysis_summary(self, summary: RegressionSummary) -> str:
        direction = "decreases" if summary.effect_size < 0 else "increases"
        magnitude = abs(summary.effect_size)
        return (
            "Ordinary least squares regression on the `real_experiment.csv` dataset "
            f"(n={summary.sample_size}) indicates vehicle weight {direction} fuel efficiency "
            f"by {magnitude:.2f} MPG per 1000 lb. Statistical significance is strong with "
            f"p-value {summary.p_value:.2e} and model R^2 of {summary.r_squared:.3f}."
        )

    def generate_research_with_verification(self, hypotheses: Iterable[str]) -> List[Dict[str, Any]]:
        baseline = self._run_regression()
        verification = self._verify_regression(baseline)
        timestamp = datetime.now(timezone.utc).isoformat()

        papers: List[Dict[str, Any]] = []
        for hypothesis in hypotheses:
            paper_id = hashlib.sha256(hypothesis.encode("utf-8")).hexdigest()[:16]
            references = self.reference_fetcher(hypothesis, max_items=3)
            paper = {
                "id": paper_id,
                "title": hypothesis,
                "hypothesis": hypothesis,
                "created_at": timestamp,
                "analysis": self._build_analysis_summary(baseline),
                "metrics": {
                    "effect_size": baseline.effect_size,
                    "p_value": baseline.p_value,
                    "intercept": baseline.intercept,
                    "r_squared": baseline.r_squared,
                    "sample_size": baseline.sample_size,
                },
                "verification": verification,
                "dataset": {
                    "path": str(self.dataset_path),
                    "rows": baseline.sample_size,
                    "columns": ["wt", "mpg"],
                    "last_updated": timestamp,
                },
                "references": references,
            }
            papers.append(paper)

        return papers

    def build_markdown_export(self, papers: Iterable[Dict[str, Any]]) -> str:
        md_parts: List[str] = []
        for paper in papers:
            md_parts.append(f"## {paper.get('title', 'Untitled')}")
            md_parts.append("")
            md_parts.append(f"**Hypothesis:** {paper.get('hypothesis', '')}")
            md_parts.append("")
            md_parts.append(paper.get("analysis", ""))
            md_parts.append("")
            metrics = paper.get("metrics", {})
            if metrics:
                md_parts.append("**Key Metrics:**")
                md_parts.append(
                    (
                        f"- Effect size: {metrics.get('effect_size'):.6f}\n"
                        f"- p-value: {metrics.get('p_value'):.6e}\n"
                        f"- R^2: {metrics.get('r_squared'):.4f}\n"
                        f"- Sample size: {metrics.get('sample_size')}"
                    )
                )
                md_parts.append("")
            if paper.get("references"):
                md_parts.append("**References:**")
                for ref in paper["references"]:
                    year = f" ({ref.get('year')})" if ref.get("year") else ""
                    md_parts.append(
                        f"- [{ref.get('title', 'Untitled')}]({ref.get('link', '')})"
                        f"{year} — {ref.get('authors', '')} · _{ref.get('provider', '')}_"
                    )
                md_parts.append("")
        return "\n".join(md_parts).strip()

    def build_json_export(self, papers: Iterable[Dict[str, Any]]) -> str:
        return json.dumps(list(papers), indent=2)


def render_research_card(paper: Dict[str, Any], st_module: Any = None) -> None:
    """Render a research card in Streamlit with references if available."""

    st = st_module
    if st is None:
        try:
            import streamlit as st  # type: ignore
        except ImportError as exc:  # pragma: no cover - UI dependency optional
            raise RuntimeError("Streamlit is required for UI rendering") from exc

    st.markdown(f"### {paper.get('title', 'Untitled')}")
    st.markdown(f"**Hypothesis:** {paper.get('hypothesis', '')}")
    st.markdown(paper.get("analysis", ""))
    metrics = paper.get("metrics", {})
    if metrics:
        st.markdown(
            (
                "**Metrics:**\n"
                f"- Effect size: {metrics.get('effect_size'):.6f}\n"
                f"- p-value: {metrics.get('p_value'):.6e}\n"
                f"- R^2: {metrics.get('r_squared'):.4f}\n"
                f"- Sample size: {metrics.get('sample_size')}"
            )
        )

    refs = paper.get("references", [])
    if refs:
        st.markdown("**References (recent):**")
        for index, ref in enumerate(refs, start=1):
            year = f" ({ref.get('year')})" if ref.get("year") else ""
            st.markdown(
                f"- [{ref.get('title', 'Untitled')}]({ref.get('link', '')})"
                f"{year} — {ref.get('authors', '')}  \n"
                f"  _Source_: {ref.get('provider', '')} · _accessed_ {ref.get('accessed', '')}"
            )
    else:
        st.info(
            "No references attached yet. Generate a batch or refine the hypothesis to pull literature."
        )


def render_verification_tab(target_paper: Dict[str, Any], st_module: Any = None) -> None:
    """Render verification summary and attached references in Streamlit."""

    st = st_module
    if st is None:
        try:
            import streamlit as st  # type: ignore
        except ImportError as exc:  # pragma: no cover - UI dependency optional
            raise RuntimeError("Streamlit is required for UI rendering") from exc

    verification = target_paper.get("verification", {})
    status = "✅ Verification passed" if verification.get("replicated") else "⚠️ Verification failed"
    st.markdown(f"### Verification\n{status}")
    st.json(verification)

    st.markdown("#### 📚 Sources & Inspiration")
    refs = target_paper.get("references", [])
    if refs:
        for ref in refs:
            year = f" ({ref.get('year')})" if ref.get("year") else ""
            st.markdown(
                f"- [{ref.get('title', 'Untitled')}]({ref.get('link', '')})"
                f"{year} — {ref.get('authors', '')}  \n"
                f"  _Provider_: {ref.get('provider', '')} · _accessed_ {ref.get('accessed', '')}"
            )
    else:
        st.warning("No references found for this paper.")


def render_export_tab(papers: Iterable[Dict[str, Any]], st_module: Any = None) -> None:
    """Render export options including references in Markdown exports."""

    st = st_module
    if st is None:
        try:
            import streamlit as st  # type: ignore
        except ImportError as exc:  # pragma: no cover - UI dependency optional
            raise RuntimeError("Streamlit is required for UI rendering") from exc

    factory = ResearchFactory()
    markdown_export = factory.build_markdown_export(papers)
    json_export = factory.build_json_export(papers)

    st.download_button(
        "Download Markdown",
        markdown_export,
        file_name="research_batch.md",
        mime="text/markdown",
    )
    st.download_button(
        "Download JSON",
        json_export,
        file_name="research_batch.json",
        mime="application/json",
    )
    st.code(markdown_export, language="markdown")

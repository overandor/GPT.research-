#!/usr/bin/env python3
"""
paper2endpoint_unique_api/app.py

Paper2Endpoint unique-route runtime.

Doctrine:
- Every paper receives a deterministic paper_id.
- Every computable claim/formula/algorithm receives a route under that paper_id.
- No two papers share the same compute endpoint URL.
- The runtime computes only operator-supplied formula manifests; it does not invent formulas.

Run:
  pip install fastapi uvicorn
  PAPER_MANIFEST_DIR=paper_manifests uvicorn app:app --host 0.0.0.0 --port 7860

Manifest directory layout:
  paper_manifests/*.json
"""

from __future__ import annotations

import ast
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
except Exception as exc:  # pragma: no cover
    raise SystemExit("Install dependencies first: pip install fastapi uvicorn") from exc


APP_NAME = "Paper2Endpoint Unique API"
APP_VERSION = "0.1.0"
MANIFEST_DIR = Path(os.getenv("PAPER_MANIFEST_DIR", "paper_manifests"))

SLUG_RE = re.compile(r"[^a-z0-9-]+")

SAFE_FUNCTIONS: dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "floor": math.floor,
    "ceil": math.ceil,
}

SAFE_NODES = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.Mod,
    ast.USub,
    ast.UAdd,
    ast.Load,
    ast.Name,
    ast.Constant,
    ast.Call,
)


@dataclass(frozen=True)
class VariableSpec:
    name: str
    type: str = "number"
    unit: str | None = None
    description: str | None = None
    required: bool = True
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class EndpointSpec:
    slug: str
    name: str
    description: str
    formula: str
    variables: list[VariableSpec]
    output_unit: str | None
    citation: str | None
    assumptions: list[str]


@dataclass(frozen=True)
class PaperSpec:
    paper_id: str
    slug: str
    title: str
    version: str
    source_hash: str
    doi: str | None
    citation: str | None
    endpoints: list[EndpointSpec]
    manifest_hash: str


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_short(text: str, n: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def slugify(value: str) -> str:
    slug = value.strip().lower().replace("_", "-").replace(" ", "-")
    slug = SLUG_RE.sub("-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "paper"


def make_paper_id(manifest: dict[str, Any]) -> tuple[str, str]:
    slug = slugify(str(manifest.get("paper_slug") or manifest.get("title") or "paper"))
    manifest_hash = sha256_short(canonical_json(manifest), 16)
    return f"{slug}-{manifest_hash[:12]}", manifest_hash


def parse_variable(raw: dict[str, Any]) -> VariableSpec:
    name = slugify(str(raw.get("name", ""))).replace("-", "_")
    if not name:
        raise ValueError("Variable name is required")
    var_type = str(raw.get("type", "number")).lower()
    if var_type != "number":
        raise ValueError(f"Only number variables are supported by the formula runtime: {name}")
    return VariableSpec(
        name=name,
        type=var_type,
        unit=raw.get("unit"),
        description=raw.get("description"),
        required=bool(raw.get("required", True)),
        minimum=raw.get("minimum"),
        maximum=raw.get("maximum"),
    )


def parse_endpoint(raw: dict[str, Any]) -> EndpointSpec:
    slug = slugify(str(raw.get("slug") or raw.get("name") or "compute"))
    name = str(raw.get("name") or slug).strip()
    formula = str(raw.get("formula") or "").strip()
    if not formula:
        raise ValueError(f"Endpoint {slug} is missing formula")
    variables = [parse_variable(v) for v in raw.get("variables", [])]
    if not variables:
        raise ValueError(f"Endpoint {slug} must define at least one variable")
    return EndpointSpec(
        slug=slug,
        name=name,
        description=str(raw.get("description") or "").strip(),
        formula=formula,
        variables=variables,
        output_unit=raw.get("output_unit"),
        citation=raw.get("citation"),
        assumptions=[str(x) for x in raw.get("assumptions", [])],
    )


def parse_manifest(raw: dict[str, Any]) -> PaperSpec:
    paper_id, manifest_hash = make_paper_id(raw)
    slug = slugify(str(raw.get("paper_slug") or raw.get("title") or "paper"))
    title = str(raw.get("title") or slug).strip()
    version = str(raw.get("version") or "0.1").strip()
    source_hash = str(raw.get("source_hash") or manifest_hash).strip()
    endpoints = [parse_endpoint(item) for item in raw.get("endpoints", [])]
    if not endpoints:
        raise ValueError(f"Paper {title} must define at least one endpoint")

    endpoint_slugs = [endpoint.slug for endpoint in endpoints]
    if len(endpoint_slugs) != len(set(endpoint_slugs)):
        raise ValueError(f"Paper {title} contains duplicate endpoint slugs")

    return PaperSpec(
        paper_id=paper_id,
        slug=slug,
        title=title,
        version=version,
        source_hash=source_hash,
        doi=raw.get("doi"),
        citation=raw.get("citation"),
        endpoints=endpoints,
        manifest_hash=manifest_hash,
    )


def load_papers(manifest_dir: Path) -> list[PaperSpec]:
    papers: list[PaperSpec] = []
    if not manifest_dir.exists():
        return papers
    for path in sorted(manifest_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        papers.append(parse_manifest(raw))

    ids = [paper.paper_id for paper in papers]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate paper_id detected. Paper endpoints must be unique.")
    return papers


def validate_formula(formula: str, allowed_names: set[str]) -> ast.Expression:
    try:
        tree = ast.parse(formula, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid formula syntax: {exc}") from exc

    for node in ast.walk(tree):
        if not isinstance(node, SAFE_NODES):
            raise ValueError(f"Unsafe formula node: {type(node).__name__}")
        if isinstance(node, ast.Name):
            if node.id not in allowed_names and node.id not in SAFE_FUNCTIONS:
                raise ValueError(f"Unknown formula name: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in SAFE_FUNCTIONS:
                raise ValueError("Only allowlisted math functions may be called")
    return tree


def compute_formula(endpoint: EndpointSpec, payload: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, float] = {}
    for variable in endpoint.variables:
        if variable.required and variable.name not in payload:
            raise HTTPException(status_code=422, detail=f"Missing required input: {variable.name}")
        if variable.name not in payload:
            continue
        try:
            value = float(payload[variable.name])
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Input must be numeric: {variable.name}") from exc
        if variable.minimum is not None and value < float(variable.minimum):
            raise HTTPException(status_code=422, detail=f"Input below minimum: {variable.name}")
        if variable.maximum is not None and value > float(variable.maximum):
            raise HTTPException(status_code=422, detail=f"Input above maximum: {variable.name}")
        values[variable.name] = value

    allowed_names = set(values.keys())
    tree = validate_formula(endpoint.formula, allowed_names)
    compiled = compile(tree, "<paper-formula>", "eval")
    result = eval(compiled, {"__builtins__": {}}, {**SAFE_FUNCTIONS, **values})
    return {
        "endpoint": endpoint.slug,
        "formula": endpoint.formula,
        "inputs": values,
        "result": result,
        "output_unit": endpoint.output_unit,
        "citation": endpoint.citation,
        "assumptions": endpoint.assumptions,
    }


def endpoint_contract(paper: PaperSpec, endpoint: EndpointSpec) -> dict[str, Any]:
    return {
        "paper_id": paper.paper_id,
        "paper_title": paper.title,
        "paper_version": paper.version,
        "endpoint": endpoint.slug,
        "path": f"/api/v1/papers/{paper.paper_id}/compute/{endpoint.slug}",
        "method": "POST",
        "description": endpoint.description,
        "formula": endpoint.formula,
        "inputs": [variable.__dict__ for variable in endpoint.variables],
        "output_unit": endpoint.output_unit,
        "citation": endpoint.citation or paper.citation,
        "assumptions": endpoint.assumptions,
    }


PAPERS = load_papers(MANIFEST_DIR)
PAPER_BY_ID = {paper.paper_id: paper for paper in PAPERS}

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        "Unique API endpoint runtime for computable research papers. "
        "Every paper gets deterministic paper-scoped endpoints."
    ),
)


@app.get("/healthz")
def healthz() -> dict[str, Any]:
    return {
        "ok": True,
        "app": APP_NAME,
        "version": APP_VERSION,
        "manifest_dir": str(MANIFEST_DIR),
        "paper_count": len(PAPERS),
        "endpoint_count": sum(len(paper.endpoints) for paper in PAPERS),
    }


@app.get("/api/v1/papers")
def list_papers() -> dict[str, Any]:
    return {
        "papers": [
            {
                "paper_id": paper.paper_id,
                "slug": paper.slug,
                "title": paper.title,
                "version": paper.version,
                "doi": paper.doi,
                "source_hash": paper.source_hash,
                "manifest_hash": paper.manifest_hash,
                "endpoint_count": len(paper.endpoints),
                "spec_path": f"/api/v1/papers/{paper.paper_id}/spec",
            }
            for paper in PAPERS
        ]
    }


@app.get("/api/v1/papers/{paper_id}/spec")
def paper_spec(paper_id: str) -> dict[str, Any]:
    paper = PAPER_BY_ID.get(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Unknown paper_id")
    return {
        "paper_id": paper.paper_id,
        "slug": paper.slug,
        "title": paper.title,
        "version": paper.version,
        "doi": paper.doi,
        "citation": paper.citation,
        "source_hash": paper.source_hash,
        "manifest_hash": paper.manifest_hash,
        "endpoints": [endpoint_contract(paper, endpoint) for endpoint in paper.endpoints],
    }


@app.get("/api/v1/papers/{paper_id}/openapi-fragment")
def openapi_fragment(paper_id: str) -> dict[str, Any]:
    paper = PAPER_BY_ID.get(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Unknown paper_id")
    paths: dict[str, Any] = {}
    for endpoint in paper.endpoints:
        path = f"/api/v1/papers/{paper.paper_id}/compute/{endpoint.slug}"
        paths[path] = {
            "post": {
                "summary": endpoint.name,
                "description": endpoint.description,
                "tags": [paper.paper_id],
                "x-paper-id": paper.paper_id,
                "x-paper-title": paper.title,
                "x-paper-source-hash": paper.source_hash,
                "x-formula": endpoint.formula,
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    variable.name: {"type": "number", "description": variable.description or ""}
                                    for variable in endpoint.variables
                                },
                                "required": [variable.name for variable in endpoint.variables if variable.required],
                            }
                        }
                    },
                },
                "responses": {"200": {"description": "Computed paper endpoint result"}},
            }
        }
    return {"openapi": "3.1.0", "info": {"title": paper.title, "version": paper.version}, "paths": paths}


def make_compute_handler(paper: PaperSpec, endpoint: EndpointSpec):
    async def handler(request: Request) -> JSONResponse:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=422, detail="JSON object payload required")
        computed = compute_formula(endpoint, payload)
        return JSONResponse({
            "paper_id": paper.paper_id,
            "paper_title": paper.title,
            "paper_version": paper.version,
            "source_hash": paper.source_hash,
            "manifest_hash": paper.manifest_hash,
            **computed,
            "provenance": {
                "doi": paper.doi,
                "paper_citation": paper.citation,
                "endpoint_citation": endpoint.citation,
            },
        })

    return handler


REGISTERED_PATHS: set[str] = set()
for _paper in PAPERS:
    for _endpoint in _paper.endpoints:
        _path = f"/api/v1/papers/{_paper.paper_id}/compute/{_endpoint.slug}"
        if _path in REGISTERED_PATHS:
            raise RuntimeError(f"Duplicate endpoint path detected: {_path}")
        REGISTERED_PATHS.add(_path)
        app.add_api_route(
            _path,
            make_compute_handler(_paper, _endpoint),
            methods=["POST"],
            name=f"{_paper.paper_id}:{_endpoint.slug}",
            tags=[_paper.paper_id],
            summary=f"Compute {_endpoint.name}",
        )


@app.exception_handler(ValueError)
async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"ok": False, "error": str(exc)})

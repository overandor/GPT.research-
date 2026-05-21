import os
import re
from datetime import date
from typing import Any

import requests
import streamlit as st

ZENODO_ENDPOINTS = {
    "sandbox": "https://sandbox.zenodo.org/api",
    "production": "https://zenodo.org/api",
}

DEFAULT_ENV = os.getenv("ZENODO_ENV", "sandbox").strip().lower()
if DEFAULT_ENV not in ZENODO_ENDPOINTS:
    DEFAULT_ENV = "sandbox"

REQUEST_TIMEOUT_SECONDS = int(os.getenv("ZENODO_REQUEST_TIMEOUT_SECONDS", "30"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024


def streamlit_secret(name: str, default: str = "") -> str:
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return str(value or "")


def sanitize_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip())
    safe = safe.strip(".-_")
    return safe or "manuscript.pdf"


def get_token(source: str) -> str:
    if source == "Environment variable":
        return os.getenv("ZENODO_ACCESS_TOKEN", "") or streamlit_secret("ZENODO_ACCESS_TOKEN", "")
    return st.session_state.get("session_token", "")


def api_request(method: str, api_base: str, path: str, token: str, **kwargs: Any) -> requests.Response:
    params = dict(kwargs.pop("params", {}) or {})
    params["access_token"] = token
    headers = dict(kwargs.pop("headers", {}) or {})
    headers.setdefault("User-Agent", "zenodo-research-submission-dashboard/1.0")
    response = requests.request(
        method,
        f"{api_base}{path}",
        params=params,
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
        **kwargs,
    )
    response.raise_for_status()
    return response


def require_token(token: str) -> bool:
    if not token:
        st.error("Missing Zenodo token. Set ZENODO_ACCESS_TOKEN, add it to Streamlit secrets, or paste it for this session.")
        return False
    return True


def validate_pdf(uploaded_file: Any) -> bool:
    if uploaded_file is None:
        st.error("Upload a PDF first.")
        return False
    file_bytes = uploaded_file.getvalue()
    if len(file_bytes) > MAX_UPLOAD_BYTES:
        st.error(f"File is too large. Limit is {MAX_UPLOAD_MB} MB.")
        return False
    if not file_bytes.startswith(b"%PDF"):
        st.error("The uploaded file does not appear to be a valid PDF.")
        return False
    return True


def metadata_is_valid(title: str, creator_name: str, description: str, keywords: list[str]) -> bool:
    missing = []
    if not title.strip():
        missing.append("title")
    if not creator_name.strip():
        missing.append("creator name")
    if not description.strip():
        missing.append("description")
    if not keywords:
        missing.append("at least one keyword")
    if missing:
        st.error("Missing required metadata: " + ", ".join(missing))
        return False
    return True


def init_state() -> None:
    defaults = {
        "deposit_id": None,
        "bucket_url": None,
        "record_url": None,
        "doi": None,
        "latest_api_response": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


st.set_page_config(
    page_title="Zenodo Research Submission Dashboard",
    page_icon="📄",
    layout="wide",
)

init_state()

st.title("Zenodo Research Submission Dashboard")
st.caption("Create a Zenodo draft deposit, upload your manuscript, save metadata, and publish only after explicit confirmation.")

with st.sidebar:
    st.header("Zenodo Access")
    zenodo_env = st.selectbox(
        "Zenodo target",
        ["sandbox", "production"],
        index=0 if DEFAULT_ENV == "sandbox" else 1,
        help="Use sandbox for dry runs. Production creates real Zenodo records.",
    )
    api_base = ZENODO_ENDPOINTS[zenodo_env]

    token_source = st.radio(
        "Token source",
        ["Environment variable", "Paste for this session"],
        index=0,
    )

    if token_source == "Paste for this session":
        st.text_input("Zenodo access token", type="password", key="session_token")
    else:
        st.info("Uses ZENODO_ACCESS_TOKEN from the environment or Streamlit secrets.")

    token = get_token(token_source)
    st.code(api_base, language="text")
    st.warning("Never commit or share your token. If it appears in chat, logs, or GitHub, revoke it immediately.")

    st.divider()
    existing_deposit = st.text_input("Resume existing draft deposit ID", value="")
    if st.button("Load Existing Draft", use_container_width=True):
        if require_token(token) and existing_deposit.strip().isdigit():
            try:
                response = api_request("GET", api_base, f"/deposit/depositions/{existing_deposit.strip()}", token)
                deposit = response.json()
                st.session_state.deposit_id = deposit.get("id")
                st.session_state.bucket_url = deposit.get("links", {}).get("bucket")
                st.session_state.record_url = deposit.get("links", {}).get("html")
                st.session_state.doi = deposit.get("doi")
                st.session_state.latest_api_response = deposit
                st.success("Draft loaded.")
            except Exception as exc:
                st.error(f"Failed to load draft: {exc}")

st.subheader("1. Manuscript File")
uploaded_file = st.file_uploader("Upload manuscript PDF", type=["pdf"])

st.subheader("2. Research Metadata")
col1, col2 = st.columns(2)

with col1:
    title = st.text_input(
        "Title",
        value="Bearinglessfull Collateral: A Risk Primitive for Distributed Hedge Capacity",
    )
    creator_name = st.text_input("Creator name", value="Skrobynets, Joseph")
    version = st.text_input("Version", value="0.2")
    publication_date = st.date_input("Publication date", value=date.today())

with col2:
    upload_type = st.selectbox("Upload type", ["publication"], index=0)
    publication_type = st.selectbox(
        "Publication type",
        ["workingpaper", "article", "preprint", "report", "technicalnote", "other"],
        index=0,
    )
    access_right = st.selectbox("Access right", ["open", "restricted", "closed", "embargoed"], index=0)
    license_id = st.text_input("License", value="cc-by-4.0")

language = st.text_input("Language", value="eng", help="ISO 639-3 code, for example eng.")

description = st.text_area(
    "Description / abstract",
    value=(
        "This working paper introduces Bearinglessfull Collateral, a risk primitive "
        "for distributed hedge-capacity systems. The framework evaluates whether "
        "collateral is not merely sufficient in nominal value, but structurally "
        "resilient across venue distribution, liquidation distance, reserve buffers, "
        "rebalance readiness, and access risk. It also introduces the Bearinglessfull "
        "Score, AlphaSignalLLM, and a GMX Hedge Adapter as components of a research-only "
        "architecture for collateral-aware hedge verification."
    ),
    height=180,
)

keywords_text = st.text_area(
    "Keywords, one per line",
    value="""Bearinglessfull Collateral
Bearinglessfull Score
BFS
collateral topology
hedge capacity
distributed collateral
margin risk
DeFi
market microstructure
LLM-assisted research""",
    height=180,
)
keywords = [k.strip() for k in keywords_text.splitlines() if k.strip()]

metadata_payload: dict[str, Any] = {
    "metadata": {
        "title": title.strip(),
        "upload_type": upload_type,
        "publication_type": publication_type,
        "description": description.strip(),
        "creators": [{"name": creator_name.strip()}],
        "keywords": keywords,
        "version": version.strip(),
        "publication_date": str(publication_date),
        "language": language.strip() or "eng",
        "access_right": access_right,
    }
}

if access_right == "open":
    metadata_payload["metadata"]["license"] = license_id.strip() or "cc-by-4.0"

with st.expander("Preview metadata JSON", expanded=False):
    st.json(metadata_payload)

st.subheader("3. Submission Controls")
if zenodo_env == "production":
    st.error("Production mode is active. Publishing can create a real, durable public Zenodo record.")
else:
    st.info("Sandbox mode is active. Use it for dry runs before switching to production.")

c1, c2, c3, c4 = st.columns(4)

with c1:
    if st.button("Create Zenodo Draft", use_container_width=True):
        if require_token(token):
            try:
                response = api_request("POST", api_base, "/deposit/depositions", token, json={})
                deposit = response.json()
                st.session_state.deposit_id = deposit["id"]
                st.session_state.bucket_url = deposit["links"]["bucket"]
                st.session_state.latest_api_response = deposit
                st.success(f"Draft created: {st.session_state.deposit_id}")
            except Exception as exc:
                st.error(f"Failed to create draft: {exc}")

with c2:
    if st.button("Upload PDF", use_container_width=True):
        if require_token(token):
            if not st.session_state.deposit_id or not st.session_state.bucket_url:
                st.error("Create or load a Zenodo draft first.")
            elif validate_pdf(uploaded_file):
                try:
                    file_name = sanitize_filename(uploaded_file.name)
                    response = requests.put(
                        f"{st.session_state.bucket_url}/{file_name}",
                        params={"access_token": token},
                        data=uploaded_file.getvalue(),
                        timeout=REQUEST_TIMEOUT_SECONDS,
                        headers={"Content-Type": "application/pdf"},
                    )
                    response.raise_for_status()
                    st.session_state.latest_api_response = response.json()
                    st.success(f"Uploaded: {file_name}")
                except Exception as exc:
                    st.error(f"Failed to upload file: {exc}")

with c3:
    if st.button("Save Metadata", use_container_width=True):
        if require_token(token) and metadata_is_valid(title, creator_name, description, keywords):
            if not st.session_state.deposit_id:
                st.error("Create or load a Zenodo draft first.")
            else:
                try:
                    response = api_request(
                        "PUT",
                        api_base,
                        f"/deposit/depositions/{st.session_state.deposit_id}",
                        token,
                        json=metadata_payload,
                    )
                    st.session_state.latest_api_response = response.json()
                    st.success("Metadata saved.")
                except Exception as exc:
                    st.error(f"Failed to save metadata: {exc}")

with c4:
    publish_confirm = st.text_input(
        "Type PUBLISH-REAL to enable publishing",
        placeholder="PUBLISH-REAL",
    )
    publish_enabled = publish_confirm == "PUBLISH-REAL" and zenodo_env == "production"

    if st.button("Publish DOI", disabled=not publish_enabled, use_container_width=True):
        if require_token(token):
            if not st.session_state.deposit_id:
                st.error("Create or load a Zenodo draft first.")
            else:
                try:
                    response = api_request(
                        "POST",
                        api_base,
                        f"/deposit/depositions/{st.session_state.deposit_id}/actions/publish",
                        token,
                    )
                    record = response.json()
                    st.session_state.doi = record.get("doi")
                    st.session_state.record_url = record.get("links", {}).get("html")
                    st.session_state.latest_api_response = record
                    st.success("Published successfully.")
                except Exception as exc:
                    st.error(f"Failed to publish: {exc}")

st.subheader("4. Current Submission State")
state_col1, state_col2, state_col3 = st.columns(3)

with state_col1:
    st.metric("Deposit ID", st.session_state.deposit_id or "Not created")

with state_col2:
    st.metric("DOI", st.session_state.doi or "Not published")

with state_col3:
    if st.session_state.record_url:
        st.link_button("Open Zenodo Record", st.session_state.record_url)
    else:
        st.write("No public record yet.")

with st.expander("Latest Zenodo API response", expanded=False):
    if st.session_state.latest_api_response:
        st.json(st.session_state.latest_api_response)
    else:
        st.write("No API response captured yet.")

st.divider()
st.subheader("Recommended Flow")
st.write("Sandbox dry run → Create Draft → Upload PDF → Save Metadata → inspect draft → switch to production → repeat → type PUBLISH-REAL → Publish DOI.")
st.caption("Publishing is durable. Review metadata, files, licensing, authorship, and access settings before minting the DOI.")

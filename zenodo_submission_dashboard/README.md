# Zenodo Research Submission Dashboard

Production-ready Streamlit dashboard for creating Zenodo draft deposits, uploading PDF manuscripts, saving research metadata, and publishing a DOI only after explicit confirmation.

## Production boundaries

- Defaults to the Zenodo sandbox API for safe dry runs.
- Production publishing is disabled unless `ZENODO_ENV=production` and the operator types `PUBLISH-REAL`.
- Access tokens are loaded from environment variables, Streamlit secrets, or a temporary session field.
- Uploaded files are checked for PDF magic bytes and maximum file size before upload.
- Filenames are sanitized before they are sent to the Zenodo bucket API.
- No token should ever be committed to GitHub.

## Run locally

```bash
cd zenodo_submission_dashboard
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export ZENODO_ENV=sandbox
export ZENODO_ACCESS_TOKEN=your_sandbox_token_here
streamlit run app.py
```

## Run with Docker

```bash
cd zenodo_submission_dashboard
docker build -t zenodo-submission-dashboard .
docker run --rm -p 7860:7860 \
  -e ZENODO_ENV=sandbox \
  -e ZENODO_ACCESS_TOKEN=your_sandbox_token_here \
  zenodo-submission-dashboard
```

Open `http://localhost:7860`.

## Deploy to Hugging Face Spaces

Use a Streamlit or Docker Space. Store the token in Space secrets as `ZENODO_ACCESS_TOKEN`. Keep `ZENODO_ENV=sandbox` for rehearsals. Switch to `ZENODO_ENV=production` only when you are ready to create real Zenodo records.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `ZENODO_ENV` | `sandbox` | `sandbox` or `production`. |
| `ZENODO_ACCESS_TOKEN` | empty | Zenodo API token. Use secrets, not committed files. |
| `ZENODO_REQUEST_TIMEOUT_SECONDS` | `30` | HTTP request timeout. |
| `MAX_UPLOAD_MB` | `100` | Maximum uploaded manuscript size. |

## Operator flow

1. Start in sandbox mode.
2. Create a draft.
3. Upload the PDF.
4. Save metadata.
5. Inspect the latest API response and draft page.
6. Repeat the same flow in production only when final.
7. Type `PUBLISH-REAL` and click publish.

## Important warning

Zenodo publication is intended for durable scholarly citation. Review author names, abstract, license, file, access right, and publication type before publishing a DOI.

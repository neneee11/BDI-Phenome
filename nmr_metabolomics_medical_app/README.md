# Connected NMR Metabolomics Medical App

This folder is the connected version of `../nmr_metabolomics_medical_app.html`.

It keeps the medical-dashboard concept, but replaces demo/random values with real backend data from:

- `../eda_outputs/`
- `../modeling_outputs/`
- `backend/`

## Run

From the project root:

```bash
python nmr_metabolomics_medical_app/backend/server.py --host 127.0.0.1 --port 8766
```

Open:

```text
http://127.0.0.1:8766
```

## Deploy Backend on Render

Create a Render Web Service from this repository. Use the repository root so the backend
can read `eda_outputs/` and `modeling_outputs/`.

```text
Environment: Python
Build Command: pip install -r nmr_metabolomics_medical_app/backend/requirements.txt
Start Command: python nmr_metabolomics_medical_app/backend/server.py --host 0.0.0.0
Health Check Path: /api/health
```

The included `render.yaml` contains the same configuration for Render Blueprint deploys.
After Render gives you a public URL, update the Vercel frontend config:

```js
window.NMR_API_BASE = "https://your-render-service.onrender.com";
```

If you open `frontend/index.html` with VS Code Live Server, keep the backend running on
`127.0.0.1:8766` so the dashboard can call the real API. The SQLite database is generated
automatically at runtime from the cleaned EDA and modeling outputs.

## Added Compared With the HTML Mockup

- Real API connection: `/api/summary`, `/api/samples`, `/api/sample/{sample_name}`, `/api/performance`, `/api/trajectories`
- Upload/input page for `.csv` or `.tsv`
- Real prediction output: label, post-op probability, recovery score, recovery state, nutrition follow-up flag
- Rule-based recovery score section with all six rules
- LLM chat routed through backend: `POST /api/assistant`
- Privacy/deployment block: de-identification, secure logs, access control, on-premise/BDI cloud
- Correct top-6 metabolite names from the final model

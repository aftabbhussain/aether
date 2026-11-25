# Aether

Aether is a file-level software defect prediction web application for GitHub repositories. Given a repository URL and a commit SHA, it inspects Java, Python, and C++ source files, extracts static code metrics and Git commit-history process metrics, and scores each file's defect risk using a trained XGBoost classifier with SHAP explanations.

## Project Layout

- `server/` — FastAPI backend (`app.py`, `settings.py`, `schemas/`, `core/`, `spec/`, `storage/`)
- `client/` — React + TypeScript + Vite frontend (`src/views/`, `src/ui/`, `src/net/`, `src/models/`, `src/helpers/`, `src/css/`)
- `ml_engine/` — Dataset collection, feature enrichment, model training scripts (`jobs/`), datasets (`datasets/`), serialized artifacts (`artifacts/`), and evaluation outputs (`outputs/`)

## What Aether Does

1. **Repository & Commit Selection**: Connects to public GitHub repositories (either via local mirror caching or temporary request-scoped PAT cloning) to list branches, tags, and commits.
2. **Metric Extraction**:
   - **Static metrics**: `loc`, `wmc`, `rfc`, `cbo`, `dit`, `lcom`, `nosi`, `comparisonsQty`, `returnQty`, `totalMethods`
   - **Git process metrics**: `file_change_count`, `file_bug_fix_count`, `recent_file_change_count`, `days_since_last_change`, `last_change_lines_added`, `last_change_lines_deleted`, `last_change_churn`, `last_change_file_count`, `author_file_change_count`
3. **Defect Scoring & Explainability**: Applies `log1p` compression and training-split standard scaling to process features, runs the trained XGBoost model (default threshold `0.34`, configurable per scan), and computes per-file SHAP feature contributions plus plain-language risk summaries.
4. **Dashboard, History & Export**: Displays risk breakdowns, language summaries, filterable results tables (separating potential test files), persistent scan history (SQLite locally or PostgreSQL via `DATABASE_URL`), public feedback, and CSV/PDF report exports.

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 20+
- Git installed and available on `PATH`

### 1. Backend (`server/`)

```powershell
# From the project root
.\.venv\Scripts\python.exe -m pip install -r server\requirements.txt
cd server
..\.venv\Scripts\python.exe -m uvicorn app:app --reload
```

The API runs at `http://127.0.0.1:8000` (`/health`, `/docs`).

### 2. Frontend (`client/`)

```powershell
cd client
npm install
npm run dev
```

The UI runs at `http://127.0.0.1:5173` and reads `VITE_API_BASE_URL` from `client/.env`.

## Running Tests

### Backend

```powershell
.\.venv\Scripts\python.exe -m unittest server\spec\test_core.py -v
.\.venv\Scripts\python.exe -m unittest server.spec.test_api_flows.PipelineSmokeTests -v
```

### Frontend

```powershell
cd client
npm test -- --run
npm run build
```

## Retraining the Model (`ml_engine/`)

Run scripts from inside `ml_engine/` so relative paths (`datasets/`, `artifacts/`, `outputs/`) resolve correctly:

```powershell
cd ml_engine
..\.venv\Scripts\python.exe jobs\fit_defect_model.py
```

## Notes & Limitations

- Only `.java`, `.py`, `.cpp`, `.cc`, `.cxx`, `.hpp`, `.h`, and `.hh` files are scanned; directories like `node_modules/`, `dist/`, `build/`, `target/`, `vendor/`, `third_party/`, and `generated/` are skipped.
- Predictions are statistical risk estimates to help prioritize code review, not guarantees of runtime bugs.

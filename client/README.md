# Aether Client

React + TypeScript + Vite web interface for Aether.

## Structure

- `src/views/` — Route views (`LandingView`, `ScanInputView`, `ResultsView`, `GuideView`, `HistoryView`, `FeedbackView`)
- `src/ui/` — Shared UI components (`TopBar`, `ResultsGrid`, `MetricChips`, `FactorHints`, `MetricsModal`, `CommitDrawer`, `RefDrawer`)
- `src/net/` — Axios API client (`http.ts`) and error formatting
- `src/models/` — TypeScript interfaces for API payloads and responses (`api_types.ts`)
- `src/helpers/` — Progress and ETA helpers (`eta.ts`)
- `src/css/` — Stylesheets imported via `src/index.css`

## Scripts

```powershell
npm install
npm run dev      # Start Vite dev server on http://127.0.0.1:5173
npm test -- --run # Run Vitest unit tests
npm run build    # Type-check with tsc and build production bundle
npm run lint     # Run ESLint
```

## Environment Variables

Configure in `client/.env`:
- `VITE_API_BASE_URL` — Backend base URL (defaults to `http://127.0.0.1:8000`)
- `VITE_ENABLE_LOCAL_CACHE_MODE` — Set to `false` to disable local-cache toggle in hosted deployments
- `VITE_ENABLE_HISTORY_DELETE` — Set to `false` to hide delete buttons on prediction history

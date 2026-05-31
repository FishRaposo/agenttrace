# Entry Points

## SDK
- **Install:** `cd sdk && pip install -e .`
- **Entry:** `sdk/agenttrace/__init__.py`

## Backend
- **Dev:** `cd backend && uvicorn main:app --reload` → http://localhost:8000
- **Metrics:** http://localhost:8000/metrics

## Dashboard
- **Dev:** `cd dashboard && npm run dev` → http://localhost:3000

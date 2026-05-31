# Entry Points

## SDK
- **Install:** `cd sdk && pip install -e ".[dev]"`
- **Entry:** `sdk/agenttrace/__init__.py`

## Server
- **Dev:** `cd server && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` → http://localhost:8000
- **Health:** http://localhost:8000/health
- **API Docs:** http://localhost:8000/docs

## Dashboard
- **Dev:** `cd dashboard && npm run dev` → http://localhost:3000

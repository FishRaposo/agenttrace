# AgentTrace entry points

## SDK

- Install: `python -m pip install -e "sdk[dev]"`
- Package entry: `sdk/agenttrace/__init__.py`
- Offline demo: `python examples/run_demo.py`

## Server

- Development: `cd server && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- Health: `http://localhost:8000/health`
- API docs: `http://localhost:8000/docs`
- Evidence: `python scripts/portfolio_demo.py` then `python scripts/verify_portfolio_evidence.py`

## Dashboard

- Install: `cd dashboard && npm ci`
- Development: `npm run dev` -> `http://localhost:3000`
- Unit/lint/build: `npm test`, `npm run lint`, `npm run build`
- Browser smoke: `npx playwright test --project=chromium`

The dashboard's offline demo fixtures are explicit and visibly labeled. No
legacy backend entry point exists.

# AgentTrace server

Self-contained FastAPI collector for the AgentTrace SDK. The default SQLite
configuration, in-memory realtime publisher, and offline demo require no
external compatibility package.

```bash
pip install -e "server[dev]"
uvicorn app.main:app --reload
```

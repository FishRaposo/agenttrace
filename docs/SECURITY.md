# Security Guide

## Secrets Management

### Environment Variables

All secrets are loaded from environment variables.

```bash
cp .env.example .env
# Edit with your secrets
```

### Required Secrets

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Database connection (SQLite or PostgreSQL) |
| `OPENAI_API_KEY` | LLM API (optional, only for real mode) |
| `ANTHROPIC_API_KEY` | Anthropic API (optional, only for real mode) |

### Authentication

- User passwords are hashed with bcrypt before storage
- JWT tokens are used for API authentication
- Demo user (`admin` / `admin123`) is seeded on first startup

## Security Checklist

- [ ] Change default demo password in production
- [ ] Use PostgreSQL instead of SQLite for production
- [ ] Database not exposed publicly
- [ ] CORS origins restricted to known domains

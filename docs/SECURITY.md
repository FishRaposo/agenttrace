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
| `DATABASE_URL` | PostgreSQL connection |
| `OPENAI_API_KEY` | LLM API (optional) |

### API Key Security

- Keys are hashed with bcrypt before storage
- Keys can be revoked via admin dashboard
- Rate limiting per API key

## Security Checklist

- [ ] Keys use `gk-` prefix convention
- [ ] Dashboard protected with auth
- [ ] Database not exposed publicly

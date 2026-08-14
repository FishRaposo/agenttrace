# RBAC and audit logging

The server is single-tenant and defines three local roles:

| Role | Permissions |
| --- | --- |
| `viewer` | Read runs, traces, alerts, and replay |
| `ingestor` | Viewer permissions plus run, trace, and OTLP writes |
| `admin` | Ingestor permissions plus deletion, alert rules, users, and audit read |

Set `AUTH_REQUIRED=true` outside the offline demo. With the default `false`,
protected routes use a synthetic local admin only when no token is supplied;
malformed or expired tokens still fail with `401`. Public read routes remain
compatible with the existing dashboard behavior.

`AuditLog` records authentication, ingestion, mutation, deletion, alert-rule,
acknowledgement, role, actor, resource, request ID, and UTC timestamp data.
Credential-shaped keys (`password`, tokens, API keys, authorization values, and
hashed passwords) are recursively removed before persistence. `/api/audit` is
admin-only. The tests cover the role matrix, optional/required auth, invalid
tokens, and nested secret redaction.

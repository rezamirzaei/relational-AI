# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 1.0.x   | ✅ Active |
| < 1.0   | ❌ No     |

## Reporting a vulnerability

If you discover a security vulnerability in Relational Fraud Intelligence, **please do not open a public GitHub issue**.

Instead, report it privately by emailing the maintainers or using GitHub's [private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability) feature on this repository.

Include:

- A description of the vulnerability and its impact.
- Steps to reproduce or a proof of concept.
- The version or commit hash where you found the issue.

We will acknowledge receipt within 48 hours and aim to provide a fix or mitigation plan within 7 days.

## Security design highlights

The platform enforces several security boundaries by default:

### Authentication & authorization

- Operators authenticate via JWT tokens issued by `/api/v1/auth/token`.
- Tokens are signed with `HS256` using `RFI_JWT_SECRET`, which **must** be at least 32 characters and must be rotated outside `local` and `test` environments.
- Bootstrap operator passwords must be at least 12 characters.
- Routes enforce role-based access: `analyst` and `admin` roles gate different capabilities.

### Rate limiting

- Login and general API traffic are rate-limited independently.
- Rate limiting supports in-memory and Redis backends with automatic fallback.

### Audit trail

- Every request receives a unique `X-Request-ID` and is logged to the audit table.
- Audit retention is configurable via `RFI_AUDIT_LOG_RETENTION_DAYS` (default: 90).
- The `rfi-manage prune-audit` command removes expired events.

### Request security

- CORS origins are explicitly configured via `RFI_CORS_ALLOWED_ORIGINS`.
- Security headers are applied by the `SecurityHeadersMiddleware`.
- Cases persist immutable evidence snapshots so later rule or provider changes do not rewrite historical context.

### Provider isolation

- Optional AI integrations (Hugging Face, RelationalAI) sit behind stable application ports.
- If a provider fails at startup, the platform records the fallback and continues with deterministic defaults — it never exposes raw provider errors to operators.

## Configuration checklist for production

| Setting | Requirement |
|---------|-------------|
| `RFI_JWT_SECRET` | ≥ 32 characters, rotated outside local/test |
| `RFI_BOOTSTRAP_ADMIN_PASSWORD` | ≥ 12 characters |
| `RFI_BOOTSTRAP_ANALYST_PASSWORD` | ≥ 12 characters |
| `RFI_APP_ENV` | Set to `production` (blocks default JWT secret) |
| `RFI_CORS_ALLOWED_ORIGINS` | Restrict to your actual frontend origin |
| `RFI_RATE_LIMIT_BACKEND` | `redis` recommended for multi-instance deployments |


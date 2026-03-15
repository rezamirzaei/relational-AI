# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.x     | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
**privately** using one of the following methods:

1. **GitHub Security Advisories** — Open a [private security advisory](https://github.com/your-org/relational-AI/security/advisories/new) on this repository.
2. **Email** — Send a detailed report to `security@your-org.example.com`.

### What to include

- A description of the vulnerability and its potential impact.
- Steps to reproduce or a proof-of-concept.
- Any relevant logs, screenshots, or code snippets.
- Your suggested fix (optional but appreciated).

### Response timeline

| Phase              | Target        |
|--------------------|---------------|
| Acknowledgement    | 48 hours      |
| Initial assessment | 5 business days |
| Fix released       | 30 days       |

### What we ask

- **Do not** open a public issue for security vulnerabilities.
- **Do not** exploit the vulnerability beyond what is necessary to demonstrate it.
- Allow us reasonable time to address the issue before public disclosure.

## Security Practices

This project employs the following security measures:

- **Authentication**: JWT tokens with configurable TTL, issuer, and audience validation.
- **Authorization**: Role-based access control (analyst, admin).
- **Rate limiting**: Per-user and per-IP rate limits with Redis or in-memory backends.
- **Audit trail**: Every authenticated request is logged with actor, action, resource, and IP.
- **Password policy**: Minimum 12-character passwords, bcrypt hashing with salt.
- **Secret validation**: JWT secret must be ≥32 characters; production environments reject the default dev secret.
- **Security headers**: `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, `Referrer-Policy`.
- **Dependency scanning**: `pip-audit` and `npm audit` run in CI.
- **Static analysis**: Ruff with `flake8-bandit` security rules.
- **Pre-commit hooks**: `detect-secrets` prevents accidental credential commits.


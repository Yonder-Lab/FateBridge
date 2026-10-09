# Security Policy

## Supported Versions

FateBridge is pre-1.0; only the latest released minor version receives security
fixes. Please upgrade before reporting.

| Version | Supported |
| ------- | --------- |
| 0.2.x   | ✅        |
| < 0.2   | ❌        |

## Reporting a Vulnerability

Please **do not open a public issue** for security problems.

Report privately via GitHub's
[Report a vulnerability](https://github.com/Yonder-Lab/FateBridge/security/advisories/new)
(Security → Advisories), or email **yx20001210@163.com** with:

- a description of the issue and its impact,
- steps to reproduce (a minimal request payload or CLI invocation is ideal), and
- affected version / commit.

You can expect an initial acknowledgement within **7 days**. Once a fix is
released, we will credit reporters who wish to be named.

## Scope Notes

FateBridge is a backend calculation toolkit. Keep in mind when assessing impact:

- REST supports optional API Key authentication via `FATEBRIDGE_API_KEYS` and
  `API_KEY_HEADER_NAME` (default `X-API-Key`). Empty configuration disables
  authentication; malformed nonempty entries stop startup. This is shared-key
  authentication, not an account, role, or per-tool authorization system.
- `/health`, `/ready`, `/metrics`, `/docs`, `/redoc`, `/openapi.json` and
  `OPTIONS` are exempt from API Key checks; `/api/tools` is protected when keys
  are configured. Restrict operational endpoints at the deployment boundary.
- API Key settings apply only to REST, not the default stdio MCP process or CLI.
  Control access to those processes through the host and operating system.
- REST binds to `0.0.0.0:8010` by default. For local use set
  `API_HOST=127.0.0.1`; for network deployment use a gateway for TLS, access
  controls and request limits. CORS is a browser-origin policy, not authentication.
  Heavy-calculation concurrency is not a rate limit.
- FastMCP (`fatebridge-mcp`) uses stdio by default. If a host changes the
  transport to expose a network endpoint, it must provide transport authentication.
- The project does not bundle Swiss Ephemeris `.se1` data in its Python
  distribution. The optional `python -m fatebridge.fetch_ephe` command downloads
  data separately. Project code, third-party dependencies and downloaded data
  have separate license declarations; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
- Birth information may appear in snapshots and calculation logs. Use fictional
  or redacted examples when reporting problems, and do not include API secrets.

Runtime configuration and precision checks are documented in
[Getting started](docs/getting-started.md).

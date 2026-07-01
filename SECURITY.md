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

- It performs **no authentication or authorization** itself — deployments are
  expected to sit behind their own auth layer.
- The FastAPI (`fatebridge-api`) and FastMCP (`fatebridge-mcp`) servers should
  not be exposed to untrusted networks without a gateway in front.
- Swiss Ephemeris `.se1` data files are **never redistributed** (Astrodienst's,
  dual-licensed AGPL-3.0 / commercial); they are fetched per-checkout via
  `python -m fatebridge.fetch_ephe`. Reports about ephemeris data licensing
  should go to Astrodienst, not here.

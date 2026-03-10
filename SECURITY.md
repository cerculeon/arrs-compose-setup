# Security Policy

## Supported Versions

This project is community maintained. Security fixes are applied on a best-effort basis to the `master` branch.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately.

Preferred process:

1. Open a private GitHub security advisory for this repository, if available.
2. If private advisories are not available, contact the maintainer directly via GitHub.
3. Include details to reproduce the issue and any proof-of-concept.

Please do not disclose vulnerabilities publicly until a fix or mitigation is available.

## Response Expectations

- Initial acknowledgement target: within 7 days
- Triage and impact assessment: best effort
- Fix and disclosure timeline: depends on severity and maintainer availability

## Security Best Practices for Users

- Do not commit secrets (API keys, passwords, tokens)
- Rotate credentials if accidental exposure occurs
- Limit service port exposure to trusted networks
- Use a reverse proxy and authentication for remote access
- Keep Docker images and host OS patched

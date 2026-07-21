# Security policy

## Supported versions

Security fixes are applied to the latest released version.

## Reporting

Please report vulnerabilities through GitHub's private vulnerability reporting feature rather than a public issue. Include the affected version, reproduction steps, impact, and any proposed mitigation.

Do not include proprietary Gerbers, LightBurn license data, network credentials, or personal paths in a report.

## Security boundaries

- ZIP extraction rejects paths outside the temporary workspace.
- Fabrication files are processed locally.
- LightBurn UDP traffic is restricted to loopback.
- Physical Start requires explicit user confirmation and LightBurn `Ready` state.
- The application does not use `FORCELOAD` or silently discard LightBurn projects.


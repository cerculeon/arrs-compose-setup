# Contributing

Thanks for your interest in contributing to this project.

## Getting Started

1. Fork the repository.
2. Create a feature branch from `master`.
3. Make your changes in focused commits.
4. Validate your changes locally.
5. Open a pull request.

## Local Validation

Use the config-only mode first to validate compose and env substitutions:

```bash
./runHTPCStack.sh
./runObserverStack.sh
```

If validation succeeds, bring the stack up if needed:

```bash
./runHTPCStack.sh yes
./runObserverStack.sh yes
```

## Change Scope

Please keep pull requests focused:

- One feature/fix per pull request
- Avoid unrelated formatting churn
- Update docs when behavior or setup changes

## Commit and Pull Request Guidance

- Write clear commit messages describing what and why.
- In your pull request description include:
  - Summary of changes
  - Motivation
  - Validation steps and results
  - Any migration notes

## Suggested Areas to Help

- Portability improvements for host paths
- Compose command/script consistency (`docker compose` vs `docker-compose`)
- Additional healthchecks and startup-order robustness
- CI checks for compose validation
- Better platform coverage (Linux/macOS/Windows docs and scripts)

## Reporting Issues

When opening an issue, please include:

- What you expected
- What happened instead
- Relevant logs
- Host OS and Docker/Compose versions
- Reproduction steps

## Security

Please do not open public issues for sensitive vulnerabilities. See [SECURITY.md](SECURITY.md) for coordinated reporting guidance.

# Wren CI/CD Pipeline

This directory contains GitHub Actions workflows for the Wren monorepo CI/CD pipeline.

## Workflows Overview

### 🔄 Main CI Pipeline (`ci.yml`)
**Triggers:** Push/PR to `main`/`develop` branches

**Features:**
- **Smart change detection** - Only tests affected components
- **Multi-Python support** - Tests wren_src on Python 3.10-3.12
- **Comprehensive testing**:
  - Unit tests with coverage reporting
  - Integration tests (when API keys available)
  - E2E tests across all components
- **Quality checks** - Linting, type checking, security scanning
- **Codecov integration** for coverage reporting

**Jobs:**
1. `changes` - Detects which components changed
2. `test-wren-src` - SDK tests (3.10, 3.11, 3.12)
3. `test-wren-agent` - Agent tests (unit + integration)
4. `test-wren-backend` - Backend tests + E2E
5. `integration-test` - Full workflow test
6. `security-and-quality` - Semgrep + secret scanning
7. `deployment-check` - Deployment readiness

### 📦 Dependency Updates (`dependency-updates.yml`)
**Triggers:** Weekly (Mondays 9 AM UTC) + manual dispatch

**Features:**
- Automated dependency updates via `uv sync --upgrade`
- Tests run after each update
- Auto-creates PRs with change summaries
- Security audit with `pip-audit`
- Component-specific update branches

### 🛡️ Security Analysis (`codeql.yml`)
**Triggers:** Push/PR + weekly (Sundays 6 AM UTC)

**Features:**
- GitHub's CodeQL semantic analysis
- Security vulnerability detection
- OWASP Top 10 coverage
- Results integrate with GitHub Security tab

## Required Secrets

Add these to your repository secrets (`Settings > Secrets and variables > Actions`):

### Optional (Enables Additional Features)
```
CODECOV_TOKEN=<your-codecov-token>     # Coverage reporting dashboard
OPENAI_API_KEY=<sk-...>               # Agent integration tests
PORTKEY_API_KEY=<your-portkey-key>    # SDK AI functionality tests
```

> **Note:** All secrets are optional. CI will run basic tests without them, but some features will be skipped.

## Local Development

### Run tests locally:
```bash
# Individual components
cd wren_src && uv run pytest
cd wren_agent && uv run pytest tests/unit/
cd wren_backend && uv run pytest

# E2E test
cd wren_backend && ./scripts/e2e.sh
```

### Pre-commit checks:
```bash
# Manual quality checks
cd wren_src
uv run ruff check src tests
uv run black --check src tests
uv run mypy src/wren
```

## Quick Reference

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| `ci.yml` | Push/PR | Main testing pipeline |
| `dependency-updates.yml` | Weekly | Automated dependency updates |
| `codeql.yml` | Push/PR/Weekly | Security analysis |

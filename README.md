# Wren

AI-native SDK for code-writing agents. Instead of tool schemas, let agents write Python code.

## Structure

```
wren_src/      # Core SDK - what agents write code against
wren_agent/    # AI agent that generates Wren scripts
wren_backend/  # Platform for deploying/running scripts
```

## Quick Start

```bash
# SDK
cd wren_src && uv sync && uv run pytest

# Agent
cd wren_agent && uv sync && uv run wren-agent "your request"

# Backend
cd wren_backend && uv sync && uv run uvicorn wren_backend.main:app --reload
```

## Environment

```bash
PORTKEY_API_KEY="..."   # Required for SDK (LLM access)
OPENAI_API_KEY="..."    # Required for Agent
```

## License

MIT

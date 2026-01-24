# Wren Agent

AI agent for generating Wren SDK scripts.

## Usage

```bash
# Set your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Or create a .env file with OPENAI_API_KEY=sk-...

# Run the agent
wren-agent "Process emails and classify them as urgent or normal"
```

## Programmatic Usage

```python
from wren_agent import run_agent

result = await run_agent("Send Slack notifications daily at 9 AM")
print(result["script_path"])
```

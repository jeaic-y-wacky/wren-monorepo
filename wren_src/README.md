# Wren - AI-Native SDK

Wren is an AI-native SDK designed specifically for LLMs to write code against. It prioritizes simplicity, zero configuration, and intelligent defaults.

## Core Philosophy

**"All you need is code"** - Wren enables AI agents to write code directly rather than calling tools, resulting in more accurate and flexible automation.

## Quick Start

```python
import wren

# Simple AI decisions
if wren.ai("Is this urgent?", email_text):
    escalate_to_human()

# Structured extraction
from datetime import date
from pydantic import BaseModel

class Booking(BaseModel):
    name: str
    date: date
    guests: int

booking: Booking = wren.ai.extract(email_text)
print(f"Booking for {booking.name} on {booking.date}")

# Knowledge base queries
faq = wren.rag("customer_support")
answer = faq("What's your refund policy?")

# Direct LLM access when you don't need type inference
summary = wren.llm("Summarize the onboarding docs in 3 bullet points.")
print(summary)
```

## Scheduling and Integrations

Integrations must be initialized at module level so metadata is recorded at import time:

```python
import wren

gmail = wren.integrations.gmail.init()
slack = wren.integrations.slack.init()

@wren.on_schedule("0 9 * * *")
def daily_report():
    # Integration calls are lazy and only connect when invoked.
    gmail.send_email(...)
    slack.post_message(...)
```

Note: Gmail/Slack are stub integrations for now; calling their methods raises `NotImplementedError` until real clients are added.

Importing the script registers integrations and schedules without executing function bodies:

```python
import wren
from wren.runtime import import_script

import_script("script.py")
print(wren.get_metadata())
```

## Key Features

- **Zero Configuration** - Works out of the box with smart defaults
- **AI-First Design** - Every API designed for LLM usability
- **Type Inference** - Automatic type detection from context
- **Educational Errors** - Every error teaches how to fix it
- **Context Magic** - Automatic context flow through your code
- **Runtime Metadata** - Import-time registry for integrations + schedules
- **Lazy Integrations** - Connect only when methods are called

## CLI

```bash
wren test script.py
wren validate script.py
wren deploy script.py
```

Set platform credentials for `validate` and `deploy`:

```bash
export WREN_PLATFORM_URL="https://api.wren.ai"
export WREN_PLATFORM_API_KEY="your-platform-key"
```

## Installation

```bash
pip install wren
```

Set your Portkey API key:
```bash
export PORTKEY_API_KEY="your-portkey-api-key"
```

Get your API key from [Portkey](https://app.portkey.ai). Portkey provides unified access to 200+ AI models with built-in fallbacks, caching, and observability.

That's it! No configuration files needed.

## Development Status

This project is in active development as part of a research initiative to improve how AI agents interact with code.

## License

MIT

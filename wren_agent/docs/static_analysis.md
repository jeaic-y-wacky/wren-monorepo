# Static Analysis for Wren Agent Scripts

This document explains how the Wren Agent validates Python scripts before execution.

## The Problem

When the agent generates a Wren SDK script, `wren test` actually **executes** the code to validate it. This means:

1. Dangerous code (e.g., `import os; os.system("rm -rf /")`) runs before any checks
2. Simple typos (e.g., `wren.ai.extrct`) only error at runtime
3. Common mistakes (e.g., initializing integrations inside functions) aren't caught early

## The Solution: Two-Layer Validation

We use a hybrid approach that combines the best of both worlds:

```
┌─────────────────────────────────────────────────────────────┐
│                    write_wren_script()                       │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Semgrep (Security)                                │
│                                                             │
│  • Blocks dangerous imports (os, subprocess, socket, etc.)  │
│  • Blocks eval/exec/compile                                 │
│  • Blocks file write operations                             │
│                                                             │
│  Why Semgrep? Battle-tested by major companies, rich        │
│  pattern matching, no code execution needed.                │
└─────────────────────────┬───────────────────────────────────┘
                          │ If security issues → BLOCK
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: Wren API Validator (Correctness)                  │
│                                                             │
│  • Introspects actual wren.ai methods at runtime            │
│  • Uses fuzzy matching for typo suggestions                 │
│  • Checks Wren-specific patterns (integration location)     │
│                                                             │
│  Why custom? Stays in sync with SDK automatically,          │
│  provides "Did you mean?" suggestions like Python 3.10+.    │
└─────────────────────────┬───────────────────────────────────┘
                          │ If issues → WARN (continue)
                          ▼
                    Write file to disk
```

## Layer 1: Semgrep Security Checks

[Semgrep](https://semgrep.dev/) is an open-source static analysis tool used by companies like Dropbox, Figma, and Snowflake. We use it for security checks because:

- **No code execution**: Pure AST pattern matching
- **Battle-tested**: Thousands of community rules, well-maintained
- **Declarative**: Rules are YAML, easy to audit and modify

### What We Block

| Category | Examples | Severity |
|----------|----------|----------|
| System access | `import os`, `import subprocess` | CRITICAL |
| Code execution | `eval()`, `exec()`, `compile()` | CRITICAL |
| Network access | `import socket`, `import requests` | CRITICAL |
| File writes | `open(path, "w")` | HIGH |
| Dangerous builtins | `globals()`, `setattr()` | HIGH |

### Why These Are Blocked

Even with container sandboxing, we want defense in depth:

- **System imports**: Could execute shell commands, read sensitive files
- **eval/exec**: Arbitrary code execution, defeats all other protections
- **Network**: Could exfiltrate data or contact external services
- **File writes**: Scripts should use Wren integrations for persistence

## Layer 2: Wren API Validator

For Wren-specific validation, we use a custom Python validator that:

1. **Introspects the actual SDK** at import time
2. **Uses fuzzy matching** (like Python 3.10+ error messages)
3. **Stays automatically in sync** with SDK changes

### How It Works

```python
import inspect
from difflib import get_close_matches

# At startup, discover actual wren.ai methods
import wren
valid_methods = {name for name, _ in inspect.getmembers(wren.ai)
                 if not name.startswith('_')}
# Result: {'extract', 'classify', 'sentiment', 'summarize', ...}

# When validating, check if method exists
method = "extrct"  # typo
if method not in valid_methods:
    suggestions = get_close_matches(method, valid_methods, n=1, cutoff=0.6)
    # suggestions = ['extract']
```

This is exactly how Python 3.10+ generates "Did you mean?" suggestions for `AttributeError`.

### What We Check

| Check | Example | Suggestion |
|-------|---------|------------|
| Unknown AI method | `wren.ai.extrct()` | "Did you mean 'extract'?" |
| Unknown integration | `wren.integrations.gmal` | "Did you mean 'gmail'?" |
| Integration in function | `def f(): gmail = wren.integrations.gmail.init()` | "Move to module level" |
| Missing extract type | `wren.ai.extract(text)` | "Add type parameter" |

### Why Not Hardcode Typos?

We initially considered hardcoding common typos:

```yaml
# Bad approach - hardcoded typos
- pattern: wren.ai.extraction(...)  # typo for extract
- pattern: wren.ai.clasify(...)     # typo for classify
```

Problems with this:
- Can only catch typos we've thought of
- Doesn't adapt when SDK adds new methods
- No fuzzy matching for novel typos

The introspection + fuzzy matching approach:
- Catches ANY typo, not just predefined ones
- Automatically works with new SDK methods
- Same technique Python itself uses

## Severity Levels

| Severity | Behavior | Examples |
|----------|----------|----------|
| CRITICAL | Block write | `eval()`, `import os` |
| HIGH | Block write | `open(f, "w")` |
| MEDIUM | Warn, allow write | Typos, wrong patterns |
| LOW | Warn, allow write | Style suggestions |

## Adding New Rules

### Security Rules (Semgrep)

Edit `wren_agent/agent/tools/semgrep_rules.yaml`:

```yaml
rules:
  - id: block-my-dangerous-pattern
    languages: [python]
    severity: CRITICAL
    message: "Description of why this is dangerous"
    pattern: dangerous_function(...)
```

### Wren API Checks (Python)

The Wren validator auto-discovers methods, but you can add pattern checks in `wren_validator.py`:

```python
def _check_integration_location(self, tree: ast.AST) -> list[ValidationIssue]:
    """Check that integrations are initialized at module level."""
    # Custom AST walking logic
```

## Testing

Run the static analyzer tests:

```bash
cd wren_agent
uv run pytest tests/unit/test_static_analyzer.py -v
```

## References

- [Semgrep Documentation](https://semgrep.dev/docs/)
- [Python difflib.get_close_matches](https://docs.python.org/3/library/difflib.html#difflib.get_close_matches)
- [Python 3.10 "Did you mean?" feature](https://docs.python.org/3/whatsnew/3.10.html#better-error-messages)
- [Python inspect module](https://docs.python.org/3/library/inspect.html)

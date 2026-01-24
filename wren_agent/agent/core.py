"""
Wren Agent - Main agent definition.
"""

from __future__ import annotations

from agents import Agent

from .context import AgentContext
from .prompts import SYSTEM_PROMPT, build_system_prompt
from .tools import (
    get_integration_docs,
    list_integrations,
    test_wren_script,
    write_wren_script,
)


def create_agent(
    model: str = "gpt-4o",
    include_all_integration_docs: bool = False,
    specific_integrations: list[str] | None = None,
    include_dynamic_tools: bool = False,
) -> Agent[AgentContext]:
    """Create a Wren Agent configured for writing and testing Wren SDK scripts.

    Args:
        model: The LLM model to use. Defaults to gpt-4o.
               Can be swapped to other OpenAI models or compatible providers.
        include_all_integration_docs: Include all integration docs in system prompt.
        specific_integrations: Include only these integrations' docs in prompt.
        include_dynamic_tools: Include list_integrations/get_integration_docs tools.

    Returns:
        Configured Agent instance ready for use with Runner.run()

    Usage patterns:
        # Pattern 1: All docs upfront (simple, works for ~50 integrations)
        agent = create_agent(include_all_integration_docs=True)

        # Pattern 2: Dynamic loading (scales to 100+ integrations)
        agent = create_agent(include_dynamic_tools=True)

        # Pattern 3: Hybrid (common ones upfront, rest dynamic)
        agent = create_agent(
            specific_integrations=["gmail", "slack"],
            include_dynamic_tools=True
        )

        # Pattern 4: Original behavior (no integration docs)
        agent = create_agent()
    """
    # Build the system prompt based on options
    if include_all_integration_docs or specific_integrations or include_dynamic_tools:
        instructions = build_system_prompt(
            include_all_integration_docs=include_all_integration_docs,
            specific_integrations=specific_integrations,
            include_dynamic_tools=include_dynamic_tools,
        )
    else:
        instructions = SYSTEM_PROMPT

    # Build the tools list
    tools = [
        write_wren_script,
        test_wren_script,
    ]

    # Add dynamic integration tools if requested
    if include_dynamic_tools:
        tools.extend([list_integrations, get_integration_docs])

    return Agent(
        name="WrenAgent",
        instructions=instructions,
        model=model,
        tools=tools,
    )

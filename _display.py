"""Shared terminal renderer for Claude Agent SDK message streams.

Each step script imports `render_message` and feeds it every message yielded by
`query()` or `ClaudeSDKClient.receive_response()`. The renderer prints colored,
labeled lines so the agent loop is visible in the terminal.
"""

import json

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)


RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
MAGENTA = "\033[35m"
RED = "\033[31m"


def _label(color: str, tag: str) -> str:
    return f"{color}{BOLD}[{tag}]{RESET}"


def _truncate(text: str, limit: int = 400) -> str:
    text = text.rstrip()
    if len(text) <= limit:
        return text
    return text[:limit] + f"{DIM}… (+{len(text) - limit} chars){RESET}"


def _render_tool_input(tool_input: dict) -> str:
    return _truncate(json.dumps(tool_input, ensure_ascii=False), limit=200)


def _render_tool_result(content) -> str:
    if isinstance(content, str):
        return _truncate(content)
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
            else:
                parts.append(json.dumps(item, ensure_ascii=False))
        return _truncate("\n".join(parts))
    return _truncate(str(content))


def render_message(message) -> None:
    """Print one SDK message to stdout with ANSI-labeled formatting."""
    if isinstance(message, SystemMessage):
        if message.subtype == "init":
            model = message.data.get("model", "?")
            tools = message.data.get("tools", [])
            print(f"{_label(MAGENTA, 'session')} model={model}  tools={tools}\n")

    elif isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(f"{_label(CYAN, 'assistant')}\n{block.text}\n")
            elif isinstance(block, ToolUseBlock):
                print(
                    f"{_label(YELLOW, 'tool-call')} "
                    f"{BOLD}{block.name}{RESET}({_render_tool_input(block.input)})\n"
                )
            elif isinstance(block, ThinkingBlock):
                print(f"{_label(DIM, 'thinking')} {_truncate(block.thinking, 200)}\n")

    elif isinstance(message, UserMessage):
        # The SDK feeds tool results back as a UserMessage of ToolResultBlocks.
        for block in message.content:
            if isinstance(block, ToolResultBlock):
                color = RED if block.is_error else GREEN
                tag = "tool-error" if block.is_error else "tool-result"
                print(f"{_label(color, tag)}\n{_render_tool_result(block.content)}\n")

    elif isinstance(message, ResultMessage):
        # total_cost_usd is Optional in current SDK releases (float | None).
        cost = message.total_cost_usd
        cost_str = f"${cost:.4f}" if cost is not None else "n/a"
        print(
            f"{_label(MAGENTA, 'done')} "
            f"turns={message.num_turns}  "
            f"cost={cost_str}  "
            f"duration={message.duration_ms / 1000:.1f}s"
        )

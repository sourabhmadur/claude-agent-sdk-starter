"""Step 4 — hooks via HookMatcher + PostToolUse.

What's new:
  - Hooks are callbacks the SDK fires around the agent loop. They can observe
    or veto tool calls, react to user prompts, intercept compaction, etc.
  - `HookMatcher(matcher=..., hooks=[fn])` binds a callback to a regex over
    tool names. `ClaudeAgentOptions(hooks={"PostToolUse": [matcher]})`
    registers it for the PostToolUse event (fires after each tool call
    succeeds and the result is back).
  - Each hook fn receives (input_data, tool_use_id, context) and returns a
    dict. Return {} for "observe only, don't change anything".

Here we audit every Read/Glob/Grep tool call to audit.log so you can see
exactly which files the agent touched and what it found.

Run:
    python step4_hooks.py [path-to-repo]
    cat audit.log   # one JSON line per tool call
"""

import asyncio
import json
import pathlib
import sys
from datetime import datetime
from typing import Any

from dotenv import load_dotenv

from claude_agent_sdk import (
    ClaudeAgentOptions,
    HookMatcher,
    PostToolUseHookInput,
    HookContext,
    query,
)

from _display import render_message

load_dotenv()


AUDIT_FILE = pathlib.Path(__file__).parent / "audit.log"


async def audit_tool_use(
    input_data: PostToolUseHookInput,
    tool_use_id: str | None,
    context: HookContext,
) -> dict[str, Any]:
    """PostToolUse hook: append one JSON line per tool call to audit.log."""
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "tool": input_data["tool_name"],
        "input": input_data["tool_input"],
    }
    with open(AUDIT_FILE, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    # Empty dict = "don't modify anything, just observe".
    return {}


DISALLOWED = [
    "Bash", "Edit", "Write", "NotebookEdit",
    "WebFetch", "WebSearch",
    "Task", "Agent",
    "AskUserQuestion", "EnterPlanMode", "ExitPlanMode",
    "EnterWorktree", "ExitWorktree", "Monitor",
    "PushNotification", "ScheduleWakeup",
    "TaskCreate", "TaskGet", "TaskList",
    "TaskOutput", "TaskStop", "TaskUpdate",
    "Skill", "ToolSearch",
    "CronCreate", "CronDelete", "CronList",
]


async def main() -> None:
    repo = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

    # Start with a fresh audit log each run so you can see what *this* run did.
    AUDIT_FILE.write_text("")

    options = ClaudeAgentOptions(
        cwd=str(repo),
        setting_sources=[],
        allowed_tools=["Read", "Glob", "Grep"],
        disallowed_tools=DISALLOWED,
        model="claude-sonnet-4-6",
        system_prompt=(
            "You are a codebase researcher. Briefly explore the repo to "
            "answer the user's question. Use Read, Glob, and Grep. "
            "Ignore .venv, .git, node_modules, dist, build, __pycache__."
        ),
        # Regex over tool names. Matches Read / Glob / Grep but not, say,
        # a hypothetical "ReadNotebook". The hook fires after each match.
        hooks={
            "PostToolUse": [
                HookMatcher(
                    matcher="Read|Glob|Grep",
                    hooks=[audit_tool_use],
                ),
            ],
        },
    )

    print(f"\033[2mtarget repo: {repo}\033[0m")
    print(f"\033[2maudit log:   {AUDIT_FILE}\033[0m\n")

    prompt = (
        f"In the repo at {repo}, what does each top-level Python file do? "
        "Give a one-line summary per file."
    )

    async for message in query(prompt=prompt, options=options):
        render_message(message)

    print(f"\n\033[2m--- audit.log ({AUDIT_FILE.stat().st_size} bytes) ---\033[0m")
    print(AUDIT_FILE.read_text(), end="")


if __name__ == "__main__":
    asyncio.run(main())

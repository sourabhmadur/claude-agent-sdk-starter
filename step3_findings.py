"""Step 3 — custom Python tool via @tool + create_sdk_mcp_server.

What's new:
  - You can expose your own Python functions to the agent as tools.
  - `@tool(name, description, input_schema)` turns an async function into an
    MCP tool. `create_sdk_mcp_server(...)` bundles tools into an in-process
    MCP server. `ClaudeAgentOptions(mcp_servers={...})` registers it.
  - Custom-tool names follow the pattern  `mcp__<server-key>__<tool-name>`.
    That's the name you put in `allowed_tools`.

The tool we add here is `save_finding(title, body)`: the agent calls it
whenever it notices something noteworthy while exploring a repo, and we
persist the record to findings.jsonl in this directory.

Run:
    python step3_findings.py [path-to-repo]
    cat findings.jsonl   # see what the agent wrote
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
    create_sdk_mcp_server,
    query,
    tool,
)

from _display import render_message

load_dotenv()


FINDINGS_FILE = pathlib.Path(__file__).parent / "findings.jsonl"


# Custom tool. The third arg is the input schema — a dict mapping
# argument name to Python type. The SDK converts this to JSON Schema
# under the hood and the model uses it to decide how to call the tool.
@tool(
    "save_finding",
    "Save a single noteworthy observation about the codebase. "
    "Use a short imperative title and a 1–3 sentence body. "
    "Call this once per distinct finding.",
    {"title": str, "body": str},
)
async def save_finding(args: dict[str, Any]) -> dict[str, Any]:
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "title": args["title"],
        "body": args["body"],
    }
    with open(FINDINGS_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")
    # Tools return MCP content blocks — same shape Claude's built-in tools use.
    return {
        "content": [
            {"type": "text", "text": f"Saved: {args['title']}"}
        ]
    }


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

    # An in-process MCP server. The agent talks to it like any other MCP server,
    # but tool calls become direct Python calls — no IPC, no subprocess.
    findings_server = create_sdk_mcp_server(
        name="findings",
        version="1.0.0",
        tools=[save_finding],
    )

    options = ClaudeAgentOptions(
        cwd=str(repo),
        setting_sources=[],
        mcp_servers={"findings": findings_server},
        allowed_tools=[
            "Read", "Glob", "Grep",
            "mcp__findings__save_finding",  # mcp__<server-key>__<tool-name>
        ],
        disallowed_tools=DISALLOWED,
        model="claude-sonnet-4-6",
        system_prompt=(
            "You are a codebase researcher. Explore the given repo and, "
            "every time you notice something distinct and noteworthy, "
            "call the `save_finding` tool with a short title and body. "
            "Aim for 3–5 findings total. Cover different aspects "
            "(structure, tech choices, anything unusual). "
            "Ignore .venv, .git, node_modules, dist, build, __pycache__."
        ),
    )

    print(f"\033[2mtarget repo: {repo}\033[0m")
    print(f"\033[2mfindings will be appended to: {FINDINGS_FILE}\033[0m\n")

    prompt = (
        f"Explore the repo at {repo} and record 3–5 findings via save_finding. "
        "When you're done, briefly tell me what you saved."
    )

    async for message in query(prompt=prompt, options=options):
        render_message(message)


if __name__ == "__main__":
    asyncio.run(main())

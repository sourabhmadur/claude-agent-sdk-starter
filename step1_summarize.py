"""Step 1 — one-shot repo summary using the Claude Agent SDK's query() API.

Concepts introduced:
  - query()              : async generator that drives the agent loop
  - ClaudeAgentOptions   : configures the agent (cwd, tools, system prompt)
  - allowed_tools        : pre-approval list (NOT a restriction)
  - disallowed_tools     : actual tool restriction
  - setting_sources=[]   : ignore inherited .claude/ config

Run:
    python step1_summarize.py [path-to-repo]
"""

import asyncio
import pathlib
import sys

from dotenv import load_dotenv

from claude_agent_sdk import ClaudeAgentOptions, query

from _display import render_message

load_dotenv()


# Every Claude Code built-in tool except the read-only trio we want.
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

    options = ClaudeAgentOptions(
        cwd=str(repo),
        setting_sources=[],  # ignore any .claude/ config in cwd or $HOME
        allowed_tools=["Read", "Glob", "Grep"],
        disallowed_tools=DISALLOWED,
        model="claude-haiku-4-5",
        system_prompt=(
            "You are a friendly guide who explains unfamiliar codebases "
            "to a developer who has never seen them before. "
            "Ignore .venv, .git, node_modules, dist, build, __pycache__."
        ),
    )

    prompt = (
        f"Give me a tour of the repository at {repo}. Cover:\n"
        "  (1) what it does in one sentence,\n"
        "  (2) main entry points or top-level files,\n"
        "  (3) tech stack / languages,\n"
        "  (4) anything unusual or noteworthy.\n"
        "Keep the whole tour under 200 words."
    )

    print(f"\033[2mtarget repo: {repo}\033[0m\n")

    async for message in query(prompt=prompt, options=options):
        render_message(message)


if __name__ == "__main__":
    asyncio.run(main())

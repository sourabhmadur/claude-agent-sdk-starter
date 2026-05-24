"""Step 5 — subagents via AgentDefinition.

What's new:
  - `AgentDefinition` describes a specialized agent the main agent can spawn
    on demand. Each subagent has its own system prompt, tool allowlist, model,
    and context window — so the main thread stays clean and a focused agent
    handles a focused job.
  - `ClaudeAgentOptions(agents={"code-reviewer": AgentDefinition(...)})`
    registers it. The main agent delegates by calling the `Task` tool with
    `subagent_type="code-reviewer"` — that spawns the subagent, runs it to
    completion, and returns its final answer as the tool result.

Here we define a `code-reviewer` subagent that does one thing: read a file
and return up to 3 concrete code-review comments. The main agent's job is
to pick the most interesting file in the repo and dispatch the review.

Run:
    python step5_subagent.py [path-to-repo]
"""

import asyncio
import pathlib
import sys

from dotenv import load_dotenv

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    query,
)

from _display import render_message

load_dotenv()


# A subagent definition. `tools` is its own allowlist — the main agent's
# allowlist does NOT apply to subagents. Keep this minimal: a reviewer
# only needs to read files.
CODE_REVIEWER = AgentDefinition(
    description=(
        "Reviews a single source file and returns up to 3 concrete, "
        "actionable code-review comments. Use when the main agent has "
        "picked a file worth reviewing."
    ),
    prompt=(
        "You are a senior code reviewer. The main agent will give you a "
        "file path. Read it once with the Read tool, then return up to 3 "
        "specific comments — each with the line number, what's wrong, and "
        "a suggested fix. Be concise. Skip nitpicks. If the file looks "
        "clean, say so in one sentence."
    ),
    tools=["Read"],
    model="claude-sonnet-4-6",
)


DISALLOWED = [
    "Bash", "Edit", "Write", "NotebookEdit",
    "WebFetch", "WebSearch",
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
        setting_sources=[],
        # The main agent can browse the repo AND dispatch to subagents via Task.
        allowed_tools=["Read", "Glob", "Grep", "Task"],
        disallowed_tools=DISALLOWED,
        model="claude-sonnet-4-6",
        agents={"code-reviewer": CODE_REVIEWER},
        system_prompt=(
            "You are a tech lead. Browse the repo yourself using ONLY the "
            "Read, Glob, and Grep tools — do NOT delegate exploration. Pick "
            "ONE source file worth a closer look, then call the Task tool "
            "EXACTLY ONCE with subagent_type='code-reviewer' (never any other "
            "subagent_type — not 'Explore', not 'general-purpose', not "
            "anything else) and pass the file path in the prompt. After the "
            "subagent returns, summarize its findings in 2-3 sentences. "
            "Ignore .venv, .git, node_modules, dist, build, __pycache__."
        ),
    )

    print(f"\033[2mtarget repo: {repo}\033[0m\n")

    prompt = (
        f"Pick the most interesting source file in {repo} and have the "
        "code-reviewer subagent review it. Then summarize what it said."
    )

    async for message in query(prompt=prompt, options=options):
        render_message(message)


if __name__ == "__main__":
    asyncio.run(main())

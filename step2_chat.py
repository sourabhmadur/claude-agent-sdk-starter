"""Step 2 — multi-turn chat using ClaudeSDKClient.

What's new vs step 1:
  - query()  is one-shot: each call is a fresh session, no memory.
  - ClaudeSDKClient is a stateful async context manager: one session per
    `async with` block, and every `client.query(...)` call adds to the same
    conversation. So follow-ups like "what about authentication?" work —
    the model remembers what it just read.

Run:
    python step2_chat.py [path-to-repo]

Type questions at the `you>` prompt. Use 'exit' or Ctrl-D to quit.
"""

import asyncio
import pathlib
import sys

from dotenv import load_dotenv

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from _display import render_message

load_dotenv()


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


async def read_question() -> str | None:
    """Read one line from stdin without blocking the event loop."""
    loop = asyncio.get_event_loop()
    try:
        # Bold green prompt prefix.
        line = await loop.run_in_executor(None, input, "\033[1;32myou>\033[0m ")
    except EOFError:
        return None
    return line.strip()


async def main() -> None:
    repo = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()

    options = ClaudeAgentOptions(
        cwd=str(repo),
        setting_sources=[],
        allowed_tools=["Read", "Glob", "Grep"],
        disallowed_tools=DISALLOWED,
        model="claude-sonnet-4-6",  # Sonnet handles multi-turn tool use better than Haiku
        system_prompt=(
            "You are a helpful guide answering questions about a local "
            "codebase. Be concise. The user may ask follow-up questions "
            "that reference earlier answers — assume shared context. "
            "Ignore .venv, .git, node_modules, dist, build, __pycache__."
        ),
    )

    print(f"\033[2mrepo: {repo}  (type 'exit' or Ctrl-D to quit)\033[0m\n")

    # One ClaudeSDKClient = one persistent session across all .query() calls.
    async with ClaudeSDKClient(options=options) as client:
        while True:
            question = await read_question()
            if question is None or question.lower() in {"exit", "quit"}:
                print("\033[2mbye\033[0m")
                break
            if not question:
                continue

            await client.query(question)
            async for message in client.receive_response():
                render_message(message)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[2minterrupted\033[0m")

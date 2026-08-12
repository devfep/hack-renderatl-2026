"""Run a question end to end with tracing on, for the demo and for debugging.

Usage:
    uv run phoenix serve                    # in one terminal
    uv run python -m atl_transit.demo       # in another, then open localhost:6006
"""

from __future__ import annotations

import asyncio
import sys

from dotenv import load_dotenv

from atl_transit import tracing

QUESTION = "Which Atlanta Communities of Concern get the least weekday bus service?"


async def ask(question: str) -> str:
    """Run one question through the full agent and return its answer.

    Args:
        question: What to ask.

    Returns:
        The agent's final text response.
    """
    # Imported here on purpose: tracing must patch ADK before the agent loads.
    from google.adk.runners import InMemoryRunner  # noqa: PLC0415
    from google.genai import types  # noqa: PLC0415

    from atl_transit.agent import root_agent  # noqa: PLC0415

    runner = InMemoryRunner(agent=root_agent, app_name="atl_transit")
    session = await runner.session_service.create_session(app_name="atl_transit", user_id="demo")
    answers = []
    async for event in runner.run_async(
        user_id="demo",
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=question)]),
    ):
        for part in (event.content.parts or []) if event.content else []:
            if part.function_call:
                print(f"  -> tool: {part.function_call.name}")
            if part.text:
                answers.append(part.text)
    return "\n".join(answers)


def main() -> int:
    """Start tracing, ask one question, print the answer.

    Returns:
        A process exit code.
    """
    load_dotenv()
    tracing.start()
    question = " ".join(sys.argv[1:]) or QUESTION
    print(f"\nQ: {question}\n")
    answer = asyncio.run(ask(question))
    print(f"\nA: {answer}\n")
    print("traces: http://localhost:6006")
    return 0


if __name__ == "__main__":
    sys.exit(main())

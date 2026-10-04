"""Check which Voice tool Gemini chooses for spoken-style requests.

This is a manual, credentialed check, not part of the automated suite. It sends
the real Gemini Voice instructions and tool declarations to a Gemini text model
with each request below and compares the first tool it calls with the expected
route. Nothing is executed: tool calls are only recorded.

    PYTHONPATH=voice /usr/lib/maslow-voice/venv/bin/python voice/dev/route_eval.py [--model MODEL]

The Google AI Studio key is read from the Voice keyring entry "google".
"""

import argparse
import asyncio
import sys
from unittest.mock import AsyncMock

from maslow_voice.config import DEFAULTS
from maslow_voice.keyring import Credentials
from maslow_voice.providers.livekit_gemini import LiveKitGeminiProvider

# (request, expected route). A route is "talk" (no tool), a tool name, or
# tool:detail for the detail that matters (application, action or kind).
CASES = [
    ("What's the capital of Portugal?", "talk"),
    ("Tell me a joke about computers.", "talk"),
    ("How do I make a good cup of coffee?", "talk"),
    ("What do you think about building a to-do app someday?", "talk"),
    ("Go to github.com", "desktop_action:browser"),
    ("Open YouTube", "desktop_action:browser"),
    ("Search for tmux keybindings", "desktop_action:browser"),
    ("Open my files", "desktop_action:files"),
    ("Open a terminal", "desktop_action:terminal"),
    ("Open Codex", "desktop_action:codex"),
    ("Open Claude", "desktop_action:claude"),
    ("Close the browser", "desktop_action:close"),
    ("Close Codex", "desktop_action:close"),
    ("Close the files window", "desktop_action:close"),
    ("Find cheap flights from Newark to Austin next week or the week after", "tell_agent:web_task"),
    ("Compare the prices of the iPhone 18 on Amazon and Best Buy", "tell_agent:web_task"),
    ("Find me a well reviewed Italian restaurant near Times Square that's open tonight", "tell_agent:web_task"),
    ("Look up the three cheapest hotels in Lisbon for the first weekend of November", "tell_agent:web_task"),
    ("Check what time the Apple store in Hoboken closes today and whether it has the new MacBook in stock", "tell_agent:web_task"),
    ("Fill out the contact form on example.com with a question about pricing", "tell_agent:web_task"),
    ("Tell Codex to add a dark mode toggle to the settings page", "tell_agent:instruction"),
    ("Ask Codex to run the tests", "tell_agent:instruction"),
    ("Tell Claude to list the files in this folder", "tell_agent:instruction"),
    ("Tell Codex to check whether example.com is reachable using curl", "tell_agent:instruction"),
    ("How is Codex doing?", "agent_status"),
    ("Is Claude finished yet?", "agent_status"),
    ("Build me a simple calculator app", "submit_intent"),
    ("Make a small web page that tracks my water intake", "submit_intent"),
    ("Approve it", "talk"),
    ("Stop", "talk"),
]


def route(call):
    if call is None:
        return "talk"
    args = dict(call.args or {})
    if call.name == "desktop_action":
        return "desktop_action:" + ("close" if args.get("action") == "close" else args.get("application", ""))
    if call.name == "tell_agent":
        return "tell_agent:" + args.get("kind", "instruction")
    return call.name


async def declarations():
    from livekit import agents
    provider = LiveKitGeminiProvider(config=dict(DEFAULTS), secrets={"google": "unused"}, emit=AsyncMock(), submit=AsyncMock())
    provider._session = provider._create_agent_session(agents, "", "")
    agent = provider._agent
    tools = agents.llm.ToolContext(agent.tools).parse_function_tools("google")
    return agent.instructions, tools


async def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default="gemini-flash-latest", help="Gemini text model used to stand in for the Live model")
    options = parser.parse_args()
    key = await Credentials().get("google")
    if not key:
        sys.exit("No Google AI Studio key is saved in the Voice keyring.")
    from google import genai
    from google.genai import types
    instructions, tools = await declarations()
    client = genai.Client(api_key=key)
    config = types.GenerateContentConfig(
        system_instruction=instructions, tools=[types.Tool(function_declarations=tools)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    passed = 0
    errors = []
    for request, expected in CASES:
        for attempt in range(4):
            try:
                response = await client.aio.models.generate_content(model=options.model, contents=request, config=config)
                calls = response.function_calls or []
                actual = route(calls[0] if calls else None)
                break
            except Exception as error:
                actual = f"error: {type(error).__name__}"
                detail = str(error)[:160]
                # Free-tier keys are rate limited; wait and retry rather than misreport routing.
                if attempt < 3 and any(code in detail for code in ("429", "RESOURCE_EXHAUSTED", "503", "500", "UNAVAILABLE")):
                    await asyncio.sleep(15 * (attempt + 1))
                    continue
                errors.append(f"{request}: {detail}")
                break
        await asyncio.sleep(1)
        ok = actual == expected
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  {expected:26} {actual:26} {request}")
    for line in errors[:3]:
        print("error detail:", line)
    print(f"\n{passed}/{len(CASES)} routed as expected with {options.model}.")
    print("A text model stands in for Gemini Live, so treat this as a routing signal, not a Live acceptance result.")


if __name__ == "__main__":
    asyncio.run(main())

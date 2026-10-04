"""A visible coding-agent terminal that Voice can read and type into.

The agent runs inside tmux on a private server so its window can be closed and
reopened without losing the session. The visible terminal creates the session,
so the agent inherits the desktop environment rather than the service's. The
session is started with the agent as its only program: when the agent exits the
session ends, so typed words can never reach a shell.
"""

import asyncio
import re

from .errors import VoiceError

SOCKET = "maslow-voice"
# Agents start with their own default approval behaviour. Voice never adds
# flags that approve or bypass permission requests on the person's behalf.
AGENTS = {"codex": ("codex",), "claude": ("claude",)}
NAMES = {"codex": "Codex", "claude": "Claude Code"}
# Text the agent shows while it waits for a decision, taken from the installed
# binaries. Typing into one of these screens would pick an option, so words are
# held until the person answers.
PROMPTS = {
    "codex": ("Would you like to run the following command?", "Would you like to make the following edits?",
              "Would you like to grant these permissions?", "Would you like to send input to", "Trust this folder?",
              "Yes, provide the requested info"),
    "claude": ("Yes, I trust this folder", "Yes, I trust these settings", "Is this a project you created"),
}
# Generic questions also appear in ordinary replies ("Do you want to add
# tests?"), so they count only when a numbered first option follows them.
QUESTIONS = {"codex": (), "claude": ("Do you want to",)}
CHOICE = re.compile(r"^\W*1\.\s+Yes")
# One fixed key per answer: the first, one-time option or cancel. "Always" and
# "for this session" options are never sent.
KEYS = {"codex": {"approve": "y", "deny": "Escape"}, "claude": {"approve": "1", "deny": "Escape"}}
MAX_TEXT = 2000
ENTER_DELAY = 0.25  # Codex reads Enter right after fast input as a pasted newline.


def session(agent):
    return "maslow-" + agent


def target(agent):
    return "=" + session(agent) + ":"


def tmux(*args):
    return ("tmux", "-L", SOCKET, *args)


def attach_argv(agent, cwd):
    return [*tmux("new-session", "-A", "-s", session(agent), "-c", str(cwd)), "--", *AGENTS[agent]]


def clean(text):
    if not isinstance(text, str):
        raise VoiceError("INVALID_REQUEST", "Tell the agent what to do.")
    text = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", text).split())
    if not text or len(text) > MAX_TEXT:
        raise VoiceError("INVALID_REQUEST", "Tell the agent what to do in fewer words.")
    return text


async def ready(run, agent, wait=0):
    """True only when the session exists and the agent itself owns its pane."""
    deadline = asyncio.get_running_loop().time() + wait
    while True:
        try:
            state = (await run(*tmux("display-message", "-p", "-t", target(agent), "#{pane_dead}|#{pane_current_command}"))).strip()
        except VoiceError as error:
            if error.code == "APPLICATION_UNAVAILABLE":
                raise
            state = ""
        if state == "0|" + AGENTS[agent][0]:
            return True
        if asyncio.get_running_loop().time() >= deadline:
            return False
        await asyncio.sleep(0.2)


async def screen(run, agent):
    output = await run(*tmux("capture-pane", "-p", "-J", "-t", target(agent)))
    return "\n".join(output.rstrip().splitlines()[-40:])


def pending_prompt(agent, text):
    """The waiting decision on screen, from its question onward, or an empty string."""
    lines = text.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        line = lines[index]
        dialog = any(marker in line for marker in PROMPTS[agent])
        question = any(marker in line for marker in QUESTIONS[agent]) and any(CHOICE.match(later) for later in lines[index + 1:])
        if dialog or question:
            return "\n".join(line.rstrip() for line in lines[index:] if line.strip())[:600]
    return ""


async def type_line(run, agent, text):
    await run(*tmux("send-keys", "-t", target(agent), "-l", "--", text))
    await asyncio.sleep(ENTER_DELAY)
    await run(*tmux("send-keys", "-t", target(agent), "Enter"))


async def press(run, agent, reply):
    await run(*tmux("send-keys", "-t", target(agent), KEYS[agent][reply]))

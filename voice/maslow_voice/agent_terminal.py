"""A visible coding-agent terminal that Voice can read and type into.

The agent runs inside tmux on a private server so its window can be closed and
reopened without losing the session. The visible terminal creates the session,
so the agent inherits the desktop environment rather than the service's. The
session is started with the agent as its only program: when the agent exits the
session ends, so typed words can never reach a shell.
"""

import asyncio
import re
from pathlib import Path

from .errors import VoiceError

SOCKET = "maslow-voice"
CONFIG = Path(__file__).with_name("tmux.conf")
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
              "Yes, provide the requested info", "MCP server to run tool"),
    "claude": ("Yes, I trust this folder", "Yes, I trust these settings", "Is this a project you created"),
}
# Decisions Voice must leave to the window: Codex 0.157 saves "Allow" on an
# MCP tool as a permanent approval, so a spoken answer would grant more than once.
WINDOW_ONLY = {"codex": ("MCP server to run tool",), "claude": ()}
# Generic questions also appear in ordinary replies ("Do you want to add
# tests?"), so they count only when a numbered first option follows them.
QUESTIONS = {"codex": (), "claude": ("Do you want to",)}
CHOICE = re.compile(r"^\W*1\.\s+Yes")
# Shown while the agent works, and while its transcript is scrolled away from
# the input box (where Enter only returns to the latest messages).
BUSY = "esc to interrupt"
SCROLLED = "Back to bottom"
QUEUE = "tab to queue message"  # Codex is starting or busy; Tab queues the words.
# Drawn only once the input box accepts text. Words pasted earlier, while the
# agent is still starting, are silently dropped.
INPUT_READY = {"codex": ("for shortcuts",), "claude": ("❯",)}
# One fixed key per answer: the first, one-time option or cancel. "Always" and
# "for this session" options are never sent.
KEYS = {"codex": {"approve": "y", "deny": "Escape"}, "claude": {"approve": "1", "deny": "Escape"}}
MAX_TEXT = 2000
ENTER_DELAY = 0.25
SUBMIT_CHECKS = 3
INPUT_WAIT = 20  # Codex can take several seconds to start its tools.


def session(agent):
    return "maslow-" + agent


def target(agent):
    return "=" + session(agent) + ":"


def tmux(*args):
    return ("tmux", "-L", SOCKET, "-f", str(CONFIG), *args)


def attach_argv(agent, cwd):
    return [*tmux("new-session", "-A", "-s", session(agent), "-c", str(cwd)), "--", *AGENTS[agent]]


def clean(text):
    if not isinstance(text, str):
        raise VoiceError("INVALID_REQUEST", "Tell the agent what to do.")
    text = " ".join(re.sub(r"[\x00-\x1f\x7f]", " ", text).split())
    if not text or len(text) > MAX_TEXT:
        raise VoiceError("INVALID_REQUEST", "Tell the agent what to do in fewer words.")
    return text


async def exists(run, agent):
    try:
        await run(*tmux("has-session", "-t", "=" + session(agent)))
        return True
    except VoiceError as error:
        if error.code == "APPLICATION_UNAVAILABLE":
            raise
        return False


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


async def input_ready(run, agent, wait=0):
    deadline = asyncio.get_running_loop().time() + wait
    while True:
        text = await screen(run, agent)
        if any(marker in text for marker in INPUT_READY[agent]):
            return True
        if asyncio.get_running_loop().time() >= deadline:
            return False
        await asyncio.sleep(0.25)


def flat(text):
    return " ".join(text.split())


def delivered(text, words):
    """The words reached the conversation, or the agent started working on them."""
    return BUSY in text or flat(words)[-24:] in flat(text)


def waiting_in_input(text, words):
    """True while the end of the words still sits in the input box at the bottom."""
    tail = " ".join(words.split())[-24:]
    bottom = " ".join(" ".join(text.splitlines()[-6:]).split())
    return bool(tail) and tail in bottom and BUSY not in text


async def type_line(run, agent, text):
    """Paste the words as one bracketed paste, then make sure they were submitted."""
    async def key(name):
        await run(*tmux("send-keys", "-t", target(agent), name))

    async def paste():
        # A scrolled transcript turns Enter into "return to latest". Return
        # first, while the input box is still empty.
        if SCROLLED in await screen(run, agent):
            await key("Enter")
            await asyncio.sleep(ENTER_DELAY)
        # Bracketed paste tells the agent this is pasted text, so the
        # following Enter submits instead of becoming a newline.
        await run(*tmux("set-buffer", "-b", SOCKET, "--", text))
        await run(*tmux("paste-buffer", "-p", "-d", "-b", SOCKET, "-t", target(agent)))
        await asyncio.sleep(ENTER_DELAY)
        await key("Enter")
        for _ in range(SUBMIT_CHECKS):
            await asyncio.sleep(ENTER_DELAY * 2)
            current = await screen(run, agent)
            # Never press anything while a decision is on screen.
            if pending_prompt(agent, current):
                return current
            if QUEUE in current:
                await key("Tab")
            elif SCROLLED in current or waiting_in_input(current, text):
                await key("Enter")
            else:
                return current
        return await screen(run, agent)

    if not await input_ready(run, agent, INPUT_WAIT):
        raise VoiceError("AGENT_NOT_READY", "The agent's input box is not ready yet. Try again in a moment.")
    for _ in range(2):
        current = await paste()
        if pending_prompt(agent, current) or delivered(current, text):
            return
    raise VoiceError("NOT_DELIVERED", "The words did not reach the agent. Check its window and try again.")


async def press(run, agent, reply):
    await run(*tmux("send-keys", "-t", target(agent), KEYS[agent][reply]))

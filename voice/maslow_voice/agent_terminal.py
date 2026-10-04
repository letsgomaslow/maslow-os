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
# A seat is one visible agent session. Codex and Claude Code each have one
# interactive seat; every web task gets its own Codex seat and browser so
# separate requests never interrupt each other.
WEB_SEATS = ("web-1", "web-2", "web-3")
# Note seats run Codex inside the Obsidian vault, writing notes from a brief.
NOTE_SEATS = ("note-1", "note-2")
BACKGROUND_SEATS = (*WEB_SEATS, *NOTE_SEATS)
SEATS = (*AGENTS, *BACKGROUND_SEATS)
NAMES = ({"codex": "Codex", "claude": "Claude Code"} | {seat: "Codex web task " + seat[-1] for seat in WEB_SEATS}
         | {seat: "Codex note writer " + seat[-1] for seat in NOTE_SEATS})


def program(seat):
    """The agent program running in a seat."""
    return "codex" if seat in BACKGROUND_SEATS else seat
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
# Codex's folder trust dialog ignores "y" and "1"; Enter accepts its first
# option, "Trust and continue". Escape still goes back.
TRUST = "Trust this folder?"
MAX_TEXT = 2000
ENTER_DELAY = 0.25
DELIVERY_WAIT = 8  # Long requests take Codex a few seconds to echo.
INPUT_WAIT = 20  # Codex can take several seconds to start its tools.
STABLE_READS = 6  # About 1.5 seconds of an unchanged screen.
WIDTH, HEIGHT = 160, 48  # Background web task and note seats.


def session(agent):
    return "maslow-" + agent


def target(agent):
    return "=" + session(agent) + ":"


def tmux(*args):
    return ("tmux", "-L", SOCKET, "-f", str(CONFIG), *args)


def attach_argv(agent, cwd):
    return [*tmux("new-session", "-A", "-s", session(agent), "-c", str(cwd)), "--", *AGENTS[program(agent)]]


def detached_argv(seat, cwd):
    """Start a background seat at a fixed size, independent of any window."""
    return [*tmux("new-session", "-d", "-s", session(seat), "-x", str(WIDTH), "-y", str(HEIGHT), "-c", str(cwd)),
            "--", *AGENTS[program(seat)]]


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
        if state == "0|" + AGENTS[program(agent)][0]:
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
        dialog = any(marker in line for marker in PROMPTS[program(agent)])
        question = any(marker in line for marker in QUESTIONS[program(agent)]) and any(CHOICE.match(later) for later in lines[index + 1:])
        if dialog or question:
            return "\n".join(line.rstrip() for line in lines[index:] if line.strip())[:600]
    return ""


async def input_ready(run, agent, wait=0):
    """The input box is drawn and the screen has settled.

    A fresh Codex draws its input box before it finishes loading the person's
    configuration (its status line still changes), and drops anything pasted
    in that moment. A screen unchanged for STABLE_READS reads is ready.
    """
    deadline = asyncio.get_running_loop().time() + wait
    previous, steady = None, 0
    while True:
        text = await screen(run, agent)
        if any(marker in text for marker in INPUT_READY[program(agent)]):
            steady = steady + 1 if text == previous else 1
            if steady >= STABLE_READS or BUSY in text:
                return True
        else:
            steady = 0
        previous = text
        if asyncio.get_running_loop().time() >= deadline:
            return False
        await asyncio.sleep(0.25)


async def settled_screen(run, agent, wait=0):
    """The screen once the agent shows its input box or a decision.

    A freshly started agent can show a question, such as Codex's folder trust
    dialog, a few seconds after its pane exists. Checking earlier would miss
    it and then wait for an input box that never appears.
    """
    deadline = asyncio.get_running_loop().time() + wait
    while True:
        text = await screen(run, agent)
        if pending_prompt(agent, text) or any(marker in text for marker in INPUT_READY[program(agent)]) or BUSY in text:
            return text
        if asyncio.get_running_loop().time() >= deadline:
            return text
        await asyncio.sleep(0.25)


def flat(text):
    return " ".join(text.split())


def split_input(text):
    """The conversation above the input box, and the input box itself.

    The input box is the last block starting with the agent's prompt marker
    (Codex "›", Claude "❯"); submitted messages are echoed above it.
    """
    lines = text.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].lstrip().startswith(("›", "❯")):
            return "\n".join(lines[:index]), "\n".join(lines[index:])
    return text, ""


def waiting_in_input(text, words):
    """True while the end of the words still sits in the input box."""
    return BUSY not in text and flat(words)[-24:] in flat(split_input(text)[1])


def delivered(text, words):
    """The words reached the conversation, or the agent started working on them."""
    conversation, _ = split_input(text)
    return BUSY in text or flat(words)[-24:] in flat(conversation)


async def type_line(run, agent, text):
    """Paste the words once as a bracketed paste, then confirm they were submitted.

    The words are never pasted twice: a second paste could submit the request
    twice. Without evidence of delivery the caller is told, not reassured.
    """
    async def key(name):
        await run(*tmux("send-keys", "-t", target(agent), name))

    if not await input_ready(run, agent, INPUT_WAIT):
        raise VoiceError("AGENT_NOT_READY", "The agent's input box is not ready yet. Try again in a moment.")
    # A scrolled transcript turns Enter into "return to latest". Return first,
    # while the input box is still empty.
    if SCROLLED in await screen(run, agent):
        await key("Enter")
        await asyncio.sleep(ENTER_DELAY)
    # Bracketed paste tells the agent this is pasted text, so the following
    # Enter submits instead of becoming a newline.
    await run(*tmux("set-buffer", "-b", SOCKET, "--", text))
    await run(*tmux("paste-buffer", "-p", "-d", "-b", SOCKET, "-t", target(agent)))
    await asyncio.sleep(ENTER_DELAY)
    await key("Enter")
    nudges = 0
    deadline = asyncio.get_running_loop().time() + DELIVERY_WAIT
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(ENTER_DELAY * 2)
        current = await screen(run, agent)
        # Never press anything while a decision is on screen.
        if pending_prompt(agent, current) or delivered(current, text):
            return
        if nudges < 2 and QUEUE in current:
            await key("Tab")
            nudges += 1
        elif nudges < 2 and (SCROLLED in current or waiting_in_input(current, text)):
            await key("Enter")
            nudges += 1
    raise VoiceError("NOT_DELIVERED", "The words may not have reached the agent. Check its window before trying again.")


def answer_key(agent, reply, prompt=""):
    if reply == "approve" and program(agent) == "codex" and TRUST in prompt:
        return "Enter"
    return KEYS[program(agent)][reply]


async def press(run, agent, reply, prompt=""):
    await run(*tmux("send-keys", "-t", target(agent), answer_key(agent, reply, prompt)))

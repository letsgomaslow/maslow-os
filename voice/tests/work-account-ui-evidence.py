"""Owned disposable Sway/Quickshell fixture only; no daemon/account/audio."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--container", required=True)
parser.add_argument("--evidence", type=Path, required=True)
args = parser.parse_args()
base = ["docker", "exec", "--user", "1000:1000", "--env", "XDG_RUNTIME_DIR=/evidence/account-isolated", "--env", "WAYLAND_DISPLAY=wayland-1", args.container]


def execute(*command):
    return subprocess.check_output(base + list(command), text=True).strip()


def ipc(method, *values):
    return execute("qs", "-p", "/evidence/accounts-config", "ipc", "call", "voice-fixture", method,
                   *[str(value).lower() if isinstance(value, bool) else str(value) for value in values])


def status():
    return json.loads(ipc("composerStatus"))


def requests():
    return json.loads(ipc("requests"))


def click(x, y):
    execute("/tmp/qa-click", str(x), str(y), "480", "800")
    time.sleep(0.1)


def capture(name):
    # Account delegates and wrapped text finish layout after the RPC signal.
    # Reposition after that polish rather than capturing a transient viewport.
    time.sleep(0.4)
    ipc("workScrollEnd")
    time.sleep(0.2)
    execute("grim", "/evidence/" + name + ".png")


assert json.loads(ipc("geometry"))["width"] == 480, "Use the isolated 480x800 fixture output"
ipc("assistantReadiness", True, True)
ipc("page", "tasks")
ipc("preference", "execution_connection", "free-cloud")
ipc("composer", "Review my selected calendar", "/fixture/work", "", "summary.md", True)
ipc("composerResponse", False, "Fixture previous request rejected.")
ipc("refreshAccounts")
ipc("accountsFixture", "unavailable")
assert not status()["selectedAccounts"]
ipc("workScrollEnd")
capture("account-narrow-unavailable-proof")
ipc("refreshAccounts")
refresh_id = status()["accountRequestId"]
ipc("accountsFixture", "options")
assert status()["selectedAccounts"] == [], "Listing does not grant access"
ipc("accountSelect", "fixture_personal", True)
ipc("workScrollEnd")
capture("account-narrow-consent-proof")
before = len(requests())
click(145, 714)
assert len(requests()) == before, "Send is blocked until the independent Groq checkbox is checked"
click(49, 602)
assert status()["accountConsent"] is True
click(145, 714)
submitted = requests()[-1]
assert submitted["action"] == "task_submit"
assert submitted["capabilities"]["accounts"] == ["fixture_personal"]
assert submitted["capabilities"]["send_to_groq_confirmed"] is True
assert submitted["capabilities"]["note"] == "summary.md"
request_id = submitted["request_id"]
ipc("composerTransportError")
assert status()["draft"] == "Review my selected calendar"
ipc("workScrollEnd")
click(145, 714)
assert requests()[-1]["request_id"] == request_id, "Lost acknowledgment retries retain identity"
ipc("composerResponse", True, "")
assert status()["requestId"] == "" and status()["draft"] == ""
ipc("composer", "Review my selected calendar", "/fixture/work", "", "summary.md", True)
ipc("workScrollEnd")
click(145, 714)
assert requests()[-1]["request_id"] != request_id, "Accepted identical new requests have a fresh identity"
ipc("composerResponse", False, "Fixture request rejected.")
ipc("assistantReadiness", True, True)  # model a fresh healthy daemon snapshot
ipc("refreshAccounts")
ipc("accountsFixture", "changed")
assert status()["selectedAccounts"] == [] and status()["accountConsent"] is False
ipc("workScrollEnd")
capture("account-narrow-stale-selection-proof")
geometry = json.loads(ipc("geometry"))
assert geometry["work"]["contentWidth"] <= geometry["card"]["width"], "No horizontal form overflow/pan"
assert all(request["action"] in ("task_submit", "assistant_accounts") for request in requests()), "No speech/microphone start"
screenshots = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in args.evidence.glob("account-narrow-*-proof.png")}
result = {"nativePointerConsentAndSubmit": True, "programmaticFixtureScrollForRendering": True,
          "syntheticAccountResponsesOnly": True, "installedConnectVerified": False, "liveAccountVerified": False,
          "status": status(), "geometry": geometry, "requests": requests(), "screenshots": screenshots}
(args.evidence / "account-native-interaction.json").write_text(json.dumps(result, indent=2) + "\n")
print("Narrow native account consent/submit/retry/new-request identity and stale-selection checks passed.")

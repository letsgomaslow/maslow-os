"""Fixed package entry; Python isolation is established before this executes."""
import importlib.util
import runpy
import sys

ROOT = "/usr/lib/maslow-voice"
SITE = ROOT + "/venv/lib/python3.14/site-packages"


def main():
    if (sys.version_info[:2] != (3, 14) or not sys.flags.isolated or not sys.flags.no_site
            or not sys.flags.dont_write_bytecode or sys.pycache_prefix != "/dev/null"
            or sys.executable != ROOT + "/venv/bin/python" or __file__ != ROOT + "/bootstrap.py"
            or len(sys.argv) < 2 or sys.argv[1] not in {"daemon", "control"}
            or (sys.argv[1] == "daemon" and len(sys.argv) != 2)):
        raise SystemExit("Voice needs its fixed isolated package launcher.")
    mode = sys.argv[1]
    # Do not execute site/.pth hooks; only the reviewed fixed package and its
    # packaged dependencies are added to Python's isolated standard-library path.
    sys.path[:0] = [ROOT, SITE]
    if any(name == "maslow_voice" or name.startswith("maslow_voice.") for name in sys.modules):
        raise SystemExit("Voice package was loaded before its fixed entry.")
    parent = importlib.util.find_spec("maslow_voice")
    if (parent is None or parent.origin != ROOT + "/maslow_voice/__init__.py"
            or list(parent.submodule_search_locations or []) != [ROOT + "/maslow_voice"]):
        raise SystemExit("Voice package origin could not be verified.")
    module = "maslow_voice." + mode
    spec = importlib.util.find_spec(module)
    if spec is None or spec.origin != ROOT + "/maslow_voice/" + mode + ".py":
        raise SystemExit("Voice package entry could not be verified.")
    sys.argv = [spec.origin, *sys.argv[2:]]
    runpy.run_module(module, run_name="__main__", alter_sys=True)


if __name__ == "__main__":
    main()

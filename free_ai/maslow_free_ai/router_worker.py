"""The router dies with its owning task service, including parent crashes."""

import ctypes
import os
from pathlib import Path
import signal
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit(1)
    parent = int(sys.argv[1])
    if ctypes.CDLL(None).prctl(1, signal.SIGTERM, 0, 0, 0) != 0 or os.getppid() != parent:
        raise SystemExit(1)
    package = Path(__file__).resolve().parent.parent
    binary = str(package / "node/bin/node")
    os.execve(binary, [binary, str(package / "router/server/dist/maslow-main.js")], os.environ)


if __name__ == "__main__":
    main()

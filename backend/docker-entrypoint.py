"""Container boot entrypoint (H3) — migrate, then exec the real command.

`alembic upgrade head` is idempotent, so this is safe on every start in
every topology (compose api/worker, Railway single container). Fails fast
with clear logs — no deploy ever serves the API against an unmigrated DB.

A Python (not shell) entrypoint is deliberate: it is immune to Windows
CRLF checkouts breaking `sh` scripts.
"""

import os
import subprocess
import sys


def main(argv: list[str]) -> None:
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main(sys.argv[1:])

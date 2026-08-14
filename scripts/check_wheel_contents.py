"""Check that built wheels contain the self-contained package boundaries."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path


def check_wheel(path: Path, required: tuple[str, ...]) -> None:
    if not path.is_file():
        raise SystemExit(f"wheel not found: {path}")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
    missing = [
        entry for entry in required if not any(name.endswith(entry) for name in names)
    ]
    if missing:
        raise SystemExit(f"{path.name} is missing: {', '.join(missing)}")


def main() -> int:
    sdk_wheels = sorted(Path("sdk/dist").glob("*.whl"))
    server_wheels = sorted(Path("server/dist").glob("*.whl"))
    if not sdk_wheels or not server_wheels:
        raise SystemExit("build SDK and server wheels before checking their contents")
    check_wheel(sdk_wheels[-1], ("agenttrace/__init__.py",))
    check_wheel(
        server_wheels[-1],
        (
            "app/main.py",
            "app/internal/vendor_core/config.py",
            "app/internal/vendor_core/pricing.py",
            "app/internal/vendor_core/tracing.py",
        ),
    )
    print("wheel contents: self-contained SDK and vendored server core present")
    return 0


if __name__ == "__main__":
    sys.exit(main())

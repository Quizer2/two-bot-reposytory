"""Helper script that builds distributable UI bundles using PyInstaller."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

APP_ENTRYPOINT = Path("ui/updated_main_window.py")


def ensure_pyinstaller() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise SystemExit(
            "PyInstaller is required. Install optional dependencies (`pip install -r requirements.txt`)"
        ) from exc


def build_bundle(output: Path, onefile: bool = False) -> None:
    ensure_pyinstaller()
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        output.stem,
        "--distpath",
        str(output.parent),
        "--workpath",
        str(output.parent / "build"),
        "--specpath",
        str(output.parent / "spec"),
    ]
    if onefile:
        command.append("--onefile")
    command.append(str(APP_ENTRYPOINT))

    subprocess.check_call(command)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build UI distribution bundles")
    parser.add_argument("output", type=Path, help="Output binary or directory (name determines artefact name)")
    parser.add_argument(
        "--onefile",
        action="store_true",
        help="Produce a single-file executable",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous build artefacts before starting",
    )
    return parser.parse_args(argv or sys.argv[1:])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.clean:
        build_dir = args.output.parent / "build"
        spec_dir = args.output.parent / "spec"
        if build_dir.exists():
            shutil.rmtree(build_dir)
        if spec_dir.exists():
            shutil.rmtree(spec_dir)
        if args.output.exists():
            if args.output.is_dir():
                shutil.rmtree(args.output)
            else:
                args.output.unlink()
    build_bundle(args.output, args.onefile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

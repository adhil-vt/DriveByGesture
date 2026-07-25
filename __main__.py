"""
GestureDrive — entry point.

Run with:
    python -m gesturedrive
or (if installed as a package):
    gesturedrive
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running from the project root without installing.
sys.path.insert(0, str(Path(__file__).parent))

from app import Application


def main() -> None:
    """Parse CLI arguments and start the application."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="gesturedrive",
        description="Control racing games with hand gestures.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="PATH",
        help="Path to a user configuration TOML file.",
    )
    args = parser.parse_args()

    Application(config_path=args.config).run()


if __name__ == "__main__":
    main()

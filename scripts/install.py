#!/usr/bin/env python3
"""Link the order skill into a host's skill folder, so `git pull` in this clone updates it."""

import argparse
import sys
from pathlib import Path


SOURCE = Path(__file__).resolve().parents[1] / "skills" / "order"
HOST_DIRS = {
    "codex": ".agents/skills",
    "claude": ".claude/skills",
    "grok": ".grok/skills",
}


def install(skills_dir):
    """Create <skills_dir>/order as a link to this clone. Never replace anything else."""
    destination = skills_dir.expanduser().absolute() / "order"
    if destination.is_symlink() and destination.resolve() == SOURCE:
        return destination, False
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"Already exists: {destination}. Move it aside, then run this again.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.symlink_to(SOURCE, target_is_directory=True)
    return destination, True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", choices=list(HOST_DIRS))
    parser.add_argument("--skills-dir", type=Path, help="Parent folder for order/ (default: the host's user skill folder)")
    args = parser.parse_args()
    skills_dir = args.skills_dir if args.skills_dir is not None else Path.home() / HOST_DIRS[args.host]
    try:
        destination, created = install(skills_dir)
    except OSError as error:
        print(f"install error: {error}", file=sys.stderr)
        return 1
    state = "Linked" if created else "Already linked"
    print(f"{state} {args.host}: {destination} -> {SOURCE}")
    print("Update with `git pull` in this clone. Start a new host session if order is not listed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Git-based code update for VLC Player.

Forces the local repo to match origin/main and restarts services.
Intended to be run by a systemd timer every N hours, or manually.
"""

import os
import subprocess
from pathlib import Path

from config import BASE_DIR


def ensure_script_permissions(repo_dir: Path) -> None:
    """
    Re-apply executable bit to scripts after git reset (Git may not preserve it).
    """
    for dir_name, pattern in [("src", "*.py"), ("scripts", "*.sh")]:
        d = repo_dir / dir_name
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file() and f.suffix == (".py" if pattern == "*.py" else ".sh"):
                try:
                    os.chmod(f, os.stat(f).st_mode | 0o111)
                    print(f"+ chmod +x {f.relative_to(repo_dir)}")
                except OSError as e:
                    print(f"Warning: could not chmod +x {f}: {e}")
    bootstrap = repo_dir / "bootstrap.sh"
    if bootstrap.is_file():
        try:
            os.chmod(bootstrap, os.stat(bootstrap).st_mode | 0o111)
            print("+ chmod +x bootstrap.sh")
        except OSError as e:
            print(f"Warning: could not chmod +x bootstrap.sh: {e}")


def run(cmd, check: bool = True) -> int:
    """Run a shell command with basic logging."""
    print(f"+ {' '.join(cmd)}")
    result = subprocess.run(cmd, text=True)
    if check and result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode


def update() -> None:
    """Force-sync local repo to origin/main and restart services."""
    repo_dir: Path = BASE_DIR

    print("=== Forced git-based code update ===")
    print(f"Repo dir: {repo_dir}")

    git_dir = repo_dir / ".git"
    if not git_dir.exists():
        raise SystemExit(f"Not a git repository: {repo_dir} (no .git directory)")

    # Fetch latest changes and hard reset to origin/main (forced update)
    run(["git", "-C", str(repo_dir), "fetch", "origin"])
    run(["git", "-C", str(repo_dir), "reset", "--hard", "origin/main"])

    # Re-apply executable bit to scripts (Git may not preserve it on checkout)
    ensure_script_permissions(repo_dir)

    # Restart maintenance timer so next run uses new code (media_sync, etc.)
    # vlc-player is not restarted to avoid playback interruption; it will pick up changes on reboot
    run(["sudo", "systemctl", "restart", "vlc-maintenance.timer"])

    print("=== Code update complete ===")


if __name__ == "__main__":
    update()
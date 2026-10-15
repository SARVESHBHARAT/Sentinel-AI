#!/usr/bin/env python3
"""SQLite-safe backup using the online backup API (works while the app runs under WAL)."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up the Sentinel SQLite database safely.")
    parser.add_argument("--db", default="data/sentinel.db")
    parser.add_argument("--out-dir", default="backups")
    parser.add_argument("--keep", type=int, default=7)
    args = parser.parse_args()
    source = Path(args.db)
    if not source.exists():
        print(f"No database at {source}; nothing to back up.")
        return 1
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = out_dir / f"sentinel-{stamp}.db"
    with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
        src.backup(dst)
    backups = sorted(out_dir.glob("sentinel-*.db"))
    for old in backups[: max(0, len(backups) - args.keep)]:
        old.unlink()
    print(f"Backup written to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import os
from pathlib import Path

from scanner import ScanOptions, scan_roots, to_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a secret-safe architecture inventory from local project directories.")
    parser.add_argument("roots", nargs="*", help="Directories containing project repositories")
    parser.add_argument("-o", "--output", default="architecture-inventory.json")
    parser.add_argument("--max-files", type=int, default=6000)
    args = parser.parse_args()
    roots = args.roots or [os.environ.get("PROJECTS_ROOT", "~/Projects")]
    data = scan_roots([Path(root) for root in roots], ScanOptions(max_files_per_project=args.max_files))
    Path(args.output).write_text(to_json(data) + "\n", encoding="utf-8")
    print(f"Wrote {args.output} with {len(data['projects'])} project(s)")


if __name__ == "__main__":
    main()

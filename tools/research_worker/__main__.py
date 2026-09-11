from __future__ import annotations

import argparse
import logging
import sys

from .client import ResearchApiClient
from .executor import OpenCodeExecutor
from .settings import load_settings
from .worker import ResearchWorker


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pull structured research jobs and execute them through the local OpenCode toolkit.")
    parser.add_argument("--once", action="store_true", help="Claim/process one batch and exit.")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args(argv)

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        settings = load_settings()
        worker = ResearchWorker(settings, ResearchApiClient(settings), OpenCodeExecutor(settings))
        if args.once:
            worker.run_once()
            return 0
        worker.run_forever()
        return 0
    except (ValueError, KeyboardInterrupt) as error:
        if isinstance(error, KeyboardInterrupt):
            return 130
        print(f"research-worker: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

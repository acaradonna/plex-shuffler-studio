"""CLI entrypoint for the Plex Shuffler Studio web UI."""

from __future__ import annotations

import argparse
import logging

from plex_shuffler.web_server import run_web_server


def main() -> int:
    parser = argparse.ArgumentParser(description="Plex Shuffler Studio web UI")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8181, help="Port to bind")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    run_web_server(args.config, args.host, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

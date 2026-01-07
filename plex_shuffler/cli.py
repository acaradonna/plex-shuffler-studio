"""Command line entrypoint for generating Plex playlists."""

from __future__ import annotations

import argparse
import logging
import random
import time

from plex_shuffler.builder import build_playlist_items
from plex_shuffler.config import ConfigError, load_config, validate_config
from plex_shuffler.plex_client import PlexClient
from plex_shuffler.playlist import sync_playlist
from plex_shuffler.utils import now_utc

LOGGER = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate shuffled Plex playlists")
    parser.add_argument("--config", required=True, help="Path to config.json")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    subparsers = parser.add_subparsers(dest="command", required=True)

    run_cmd = subparsers.add_parser("run", help="Build and sync playlists")
    run_cmd.add_argument("--dry-run", action="store_true", help="Do not write playlists to Plex")
    run_cmd.add_argument("--print", dest="print_count", type=int, default=0, help="Print first N items")
    run_cmd.add_argument("--playlist", action="append", default=[], help="Only run named playlist(s)")
    run_cmd.add_argument("--loop", action="store_true", help="Run continuously based on schedule")
    run_cmd.add_argument("--once", action="store_true", help="Run once even if schedule is set")
    run_cmd.add_argument("--interval-minutes", type=int, default=0, help="Override schedule interval")

    list_cmd = subparsers.add_parser("libraries", help="List Plex library sections")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        config = load_config(args.config)
        validate_config(config)
    except (ConfigError, OSError, ValueError) as exc:
        LOGGER.error("Config error: %s", exc)
        return 1

    plex_cfg = config["plex"]
    client = PlexClient(
        base_url=plex_cfg["url"],
        token=plex_cfg["token"],
        timeout=int(plex_cfg.get("timeout_seconds", 30) or 30),
    )

    if args.command == "libraries":
        sections = client.get_sections()
        for section in sections:
            print(f"{section.title} ({section.type}) - key={section.key}")
        return 0

    if args.command == "run":
        interval = args.interval_minutes or int(config.get("schedule", {}).get("interval_minutes", 0) or 0)
        jitter = int(config.get("schedule", {}).get("jitter_seconds", 0) or 0)

        def run_once() -> None:
            now = now_utc()
            playlist_filters = {name.strip().lower() for name in args.playlist if name}
            for playlist_cfg in config["playlists"]:
                name = playlist_cfg.get("name")
                if playlist_filters and name.strip().lower() not in playlist_filters:
                    continue
                items, stats = build_playlist_items(client, playlist_cfg, now)
                LOGGER.info(
                    "Built playlist %s: %s shows, %s episodes, %s movies, %s total",
                    name,
                    stats.shows,
                    stats.episodes,
                    stats.movies,
                    stats.total_items,
                )
                if args.print_count > 0:
                    _print_items(items[: args.print_count])
                if not args.dry_run:
                    output_cfg = playlist_cfg.get("output", {})
                    sync_playlist(
                        client,
                        name=name,
                        items=items,
                        mode=output_cfg.get("mode", "replace"),
                        chunk_size=int(output_cfg.get("chunk_size", 200) or 200),
                    )

        if args.once or (not args.loop and interval <= 0):
            run_once()
            return 0

        while True:
            run_once()
            if interval <= 0:
                LOGGER.info("Schedule interval is 0; exiting loop")
                break
            sleep_seconds = interval * 60
            if jitter > 0:
                sleep_seconds += random.randint(0, jitter)
            LOGGER.info("Sleeping for %s seconds", sleep_seconds)
            time.sleep(sleep_seconds)
        return 0

    return 0


def _print_items(items: list) -> None:
    for item in items:
        if item.type == "episode":
            season = item.season_index or 0
            episode = item.episode_index or 0
            print(f"{item.show_title} S{season:02d}E{episode:02d} - {item.title}")
        elif item.type == "movie":
            print(f"Movie - {item.title}")
        else:
            print(item.title)

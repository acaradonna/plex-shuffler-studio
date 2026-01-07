"""Shuffle and interleave strategies for media groups."""

from __future__ import annotations

import random
from typing import Iterable

from plex_shuffler.models import MediaGroup, MediaItem


def shuffle_groups(
    groups: list[MediaGroup],
    rng: random.Random,
    strategy: str = "rounds",
    chunk_size: int = 1,
) -> list[MediaItem]:
    if not groups:
        return []

    strategy = (strategy or "rounds").lower()
    if strategy == "round_robin":
        return _round_robin(groups, rng, chunk_size)
    if strategy == "random":
        return _random_pick(groups, rng)
    return _rounds(groups, rng, chunk_size)


def interleave_movies(
    episodes: list[MediaItem],
    movies: list[MediaItem],
    every_episodes: int,
) -> list[MediaItem]:
    if not movies or not every_episodes or every_episodes <= 0:
        return episodes

    output: list[MediaItem] = []
    movie_iter = iter(movies)
    since_movie = 0

    for episode in episodes:
        output.append(episode)
        since_movie += 1
        if since_movie >= every_episodes:
            try:
                output.append(next(movie_iter))
                since_movie = 0
            except StopIteration:
                since_movie = 0
    return output


def flatten_groups(groups: Iterable[MediaGroup]) -> list[MediaItem]:
    items: list[MediaItem] = []
    for group in groups:
        items.extend(group.items)
    return items


def _rounds(groups: list[MediaGroup], rng: random.Random, chunk_size: int) -> list[MediaItem]:
    remaining = [MediaGroup(group.name, list(group.items), group.source) for group in groups]
    output: list[MediaItem] = []
    while True:
        active = [group for group in remaining if group.items]
        if not active:
            break
        rng.shuffle(active)
        for group in active:
            for _ in range(max(1, chunk_size)):
                if not group.items:
                    break
                output.append(group.items.pop(0))
    return output


def _round_robin(groups: list[MediaGroup], rng: random.Random, chunk_size: int) -> list[MediaItem]:
    remaining = [MediaGroup(group.name, list(group.items), group.source) for group in groups]
    rng.shuffle(remaining)
    output: list[MediaItem] = []
    while True:
        active = [group for group in remaining if group.items]
        if not active:
            break
        for group in active:
            for _ in range(max(1, chunk_size)):
                if not group.items:
                    break
                output.append(group.items.pop(0))
    return output


def _random_pick(groups: list[MediaGroup], rng: random.Random) -> list[MediaItem]:
    remaining = [MediaGroup(group.name, list(group.items), group.source) for group in groups]
    output: list[MediaItem] = []
    while True:
        active = [group for group in remaining if group.items]
        if not active:
            break
        group = rng.choice(active)
        output.append(group.items.pop(0))
    return output

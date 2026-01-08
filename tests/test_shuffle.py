import random

from plex_shuffler.models import MediaGroup, MediaItem
from plex_shuffler.shuffle import interleave_movies, shuffle_groups


def _episode(show: str, index: int) -> MediaItem:
    return MediaItem(rating_key=f"{show}-{index}", title=f"{show} ep {index}", type="episode", show_title=show)


def _movie(title: str) -> MediaItem:
    return MediaItem(rating_key=f"m-{title}", title=title, type="movie")


def test_shuffle_groups_round_robin_preserves_per_group_order() -> None:
    groups = [
        MediaGroup("A", [_episode("A", 1), _episode("A", 2), _episode("A", 3)], "tv"),
        MediaGroup("B", [_episode("B", 1), _episode("B", 2)], "tv"),
        MediaGroup("C", [_episode("C", 1)], "tv"),
    ]

    rng = random.Random(123)
    out = shuffle_groups(groups, rng=rng, strategy="round_robin", chunk_size=1)

    # Within each show, episode order must remain sequential.
    by_show: dict[str, list[int]] = {"A": [], "B": [], "C": []}
    for item in out:
        by_show[item.show_title].append(int(item.rating_key.split("-")[-1]))

    assert by_show["A"] == [1, 2, 3]
    assert by_show["B"] == [1, 2]
    assert by_show["C"] == [1]
    assert len(out) == 6


def test_shuffle_groups_rounds_chunk_size() -> None:
    groups = [
        MediaGroup("A", [_episode("A", 1), _episode("A", 2), _episode("A", 3), _episode("A", 4)], "tv"),
        MediaGroup("B", [_episode("B", 1), _episode("B", 2), _episode("B", 3), _episode("B", 4)], "tv"),
    ]

    rng = random.Random(0)
    out = shuffle_groups(groups, rng=rng, strategy="rounds", chunk_size=2)

    # Each group emits up to chunk_size items per round, but shuffles group order each round.
    # This assertion checks chunking (no more than 2 consecutive from same show).
    last = None
    run = 0
    for item in out:
        if item.show_title == last:
            run += 1
        else:
            last = item.show_title
            run = 1
        assert run <= 2

    assert len(out) == 8


def test_shuffle_groups_random_preserves_per_group_order() -> None:
    groups = [
        MediaGroup("A", [_episode("A", 1), _episode("A", 2)], "tv"),
        MediaGroup("B", [_episode("B", 1), _episode("B", 2)], "tv"),
        MediaGroup("C", [_episode("C", 1), _episode("C", 2)], "tv"),
    ]

    rng = random.Random(99)
    out = shuffle_groups(groups, rng=rng, strategy="random", chunk_size=1)

    # It can pick groups in any order, but each group is still FIFO.
    by_show: dict[str, list[int]] = {"A": [], "B": [], "C": []}
    for item in out:
        by_show[item.show_title].append(int(item.rating_key.split("-")[-1]))

    assert by_show["A"] == [1, 2]
    assert by_show["B"] == [1, 2]
    assert by_show["C"] == [1, 2]
    assert len(out) == 6


def test_interleave_movies_every_n() -> None:
    episodes = [_episode("S", i) for i in range(1, 7)]
    movies = [_movie("M1"), _movie("M2")]

    out = interleave_movies(episodes, movies, every_episodes=3)

    assert [item.type for item in out] == [
        "episode",
        "episode",
        "episode",
        "movie",
        "episode",
        "episode",
        "episode",
        "movie",
    ]
    assert [item.title for item in out if item.type == "movie"] == ["M1", "M2"]


def test_interleave_movies_noop_when_every_invalid() -> None:
    episodes = [_episode("S", 1), _episode("S", 2)]
    movies = [_movie("M1")]

    assert interleave_movies(episodes, movies, every_episodes=0) == episodes
    assert interleave_movies(episodes, movies, every_episodes=-1) == episodes

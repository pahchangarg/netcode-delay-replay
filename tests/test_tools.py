from __future__ import annotations

from pathlib import Path

import pytest
from slimconfig import build_output

from contract import DelayInput, FrameStatus, RenderInput, RewindInput, ShotStatus, SpectatorInput
from plugin import render_positions, rewind_shot, spectator_view


def snap(tick: int, arrived: int | None, x: int, y: int) -> dict:
    return {"tick_ms": tick, "arrived_ms": arrived, "x": x, "y": y}


# Every 50 ms; the 100 ms snapshot is lost and the 200 ms one arrives 60 ms late.
SNAPSHOTS = [snap(0, 30, 0, 0), snap(50, 85, 100, 0), snap(100, None, 200, 50), snap(150, 190, 300, 100), snap(200, 260, 301, 100)]
# The target moves one unit per ms along x.
HISTORY = [{"tick_ms": tick, "x": tick, "y": 0} for tick in range(0, 401, 100)]
SHOT = {"history": HISTORY, "received_ms": 400, "latency_ms": 80, "delay_ms": 100, "max_rewind_ms": 250,
        "aim_x": 225, "aim_y": 0, "radius": 10}
EVENTS = [
    {"time_ms": 1000, "team": "Red", "player": "ana", "points": 1},
    {"time_ms": 4000, "team": "Blue", "player": "ben", "points": 1},
    {"time_ms": 6000, "team": "Red", "player": "cy", "points": 2},
    {"time_ms": 9000, "team": "Blue", "player": "dee", "points": 1},
    {"time_ms": 9500, "team": "Green", "player": "eve", "points": 1},
    {"time_ms": 12000, "team": "Green", "player": "fay", "points": 3},
]


def frames(delay: int, times: list[int]) -> list[tuple]:
    request = build_output({"snapshots": SNAPSHOTS, "delay_ms": delay, "times_ms": times}, RenderInput)
    return [(f.render_ms, f.status, f.x, f.y) for f in render_positions(request, Path(".")).frames]


def test_draws_a_delay_behind_from_what_has_arrived() -> None:
    I, H, W = FrameStatus.INTERPOLATED, FrameStatus.HELD, FrameStatus.WAITING
    assert frames(100, [20, 130, 150, 175, 240, 275, 330]) == [
        (-80, W, None, None),  # nothing has arrived
        (30, I, 60, 0),  # 3/5 of the way from 0 to 100
        (50, I, 100, 0),  # exactly on a snapshot
        (75, H, 100, 0),  # the 150 ms snapshot arrives only at 190: hold the newest
        (140, I, 280, 90),  # the 100 ms snapshot was lost: interpolate 50 -> 150
        (175, I, 301, 100),  # 300.5 rounds half up
        (230, H, 301, 100),  # past the newest snapshot
    ]


def test_rounds_negative_halves_up() -> None:
    request = build_output({"snapshots": [snap(0, 0, -1, -3), snap(10, 10, 0, -2)], "delay_ms": 10, "times_ms": [15, 12]}, RenderInput)
    made = render_positions(request, Path("."))
    assert [(f.x, f.y) for f in made.frames] == [(0, -2), (-1, -3)]  # -0.5 -> 0 and -2.5 -> -2; -0.8 -> -1, -2.8 -> -3


def shot(**changes) -> tuple:
    made = rewind_shot(build_output({**SHOT, **changes}, RewindInput), Path("."))
    return made.rewind_ms, made.status, made.target_x, made.target_y, made.distance_sq


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, (220, ShotStatus.HIT, 220, 0, 25)),  # aimed where the shooter saw the target
        ({"aim_x": 400}, (220, ShotStatus.MISS, 220, 0, 32400)),  # aimed at the live position: a miss
        ({"aim_x": 230}, (220, ShotStatus.HIT, 220, 0, 100)),  # exactly on the radius
        ({"aim_x": 231}, (220, ShotStatus.MISS, 220, 0, 121)),
        ({"max_rewind_ms": 179}, (220, ShotStatus.TOO_OLD, None, None, None)),
        ({"max_rewind_ms": 180}, (220, ShotStatus.HIT, 220, 0, 25)),  # exactly at the limit
        ({"received_ms": 100}, (-80, ShotStatus.NO_HISTORY, None, None, None)),
        ({"received_ms": 700, "latency_ms": 0, "delay_ms": 0}, (700, ShotStatus.NO_HISTORY, None, None, None)),
        ({"received_ms": 100, "max_rewind_ms": 10}, (-80, ShotStatus.TOO_OLD, None, None, None)),  # too_old first
    ],
)
def test_rewinds_shots(changes: dict, expected: tuple) -> None:
    assert shot(**changes) == expected


def view(delay: int, wall: int, events: list[dict] = EVENTS) -> tuple:
    made = spectator_view(build_output({"events": events, "broadcast_delay_ms": delay, "wall_ms": wall}, SpectatorInput), Path("."))
    return made.shown_until_ms, [(s.team, s.points) for s in made.scores], made.last_time_ms, made.last_player, made.hidden


def test_spectators_see_five_seconds_behind() -> None:
    # 6000 ms is exactly the cutoff, so cy's event shows; 9000 and 9500 have happened but are hidden; 12000 is future.
    assert view(5000, 11000) == (6000, [("Red", 3), ("Blue", 1), ("Green", 0)], 6000, "cy", 2)
    assert view(5000, 3000) == (-2000, [("Blue", 0), ("Green", 0), ("Red", 0)], None, None, 1)
    assert view(0, 9500) == (9500, [("Red", 3), ("Blue", 2), ("Green", 1)], 9500, "eve", 0)
    assert view(5000, 14000) == (9000, [("Red", 3), ("Blue", 2), ("Green", 0)], 9000, "dee", 2)


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        ({"snapshots": []}, "at least one"),
        ({"snapshots": [snap(50, 60, 0, 0), snap(50, 70, 1, 1)]}, "increasing"),
        ({"snapshots": [snap(50, 40, 0, 0)]}, "arrived_ms"),
        ({"snapshots": [snap(0, 0, 2_000_000, 0)]}, "x and y"),
        ({"delay_ms": -1}, "delay_ms"),
        ({"times_ms": []}, "times_ms"),
        ({"times_ms": [-5]}, "times_ms"),
    ],
)
def test_render_refuses_bad_requests(bad: dict, message: str) -> None:
    request = build_output({"snapshots": SNAPSHOTS, "delay_ms": 100, "times_ms": [100], **bad}, RenderInput)
    with pytest.raises(ValueError, match=message):
        render_positions(request, Path("."))


def test_rewind_and_spectator_refuse_bad_requests() -> None:
    with pytest.raises(ValueError, match="radius"):
        shot(radius=0)
    with pytest.raises(ValueError, match="latency_ms"):
        shot(latency_ms=6000)
    with pytest.raises(ValueError, match="time order"):
        view(5000, 11000, [EVENTS[1], EVENTS[0]])
    with pytest.raises(ValueError, match="points"):
        view(5000, 11000, [{**EVENTS[0], "points": 0}])
    with pytest.raises(ValueError, match="blank"):
        view(5000, 11000, [{**EVENTS[0], "team": " "}])


def test_delay_input_builds() -> None:
    request = build_output({"snapshots": SNAPSHOTS, "times_ms": [200], "step_ms": 50, "max_delay_ms": 300}, DelayInput)
    assert request.step_ms == 50

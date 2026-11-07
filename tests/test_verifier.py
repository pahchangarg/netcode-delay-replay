from __future__ import annotations

from pathlib import Path

import pytest
from slimconfig import build_output, plain_output
from test_tools import EVENTS, HISTORY, SHOT, SNAPSHOTS, snap

import verifier
from contract import TASKS, TOOLS, RenderInput, RewindInput, SpectatorInput, Task, Tool
from plugin import render_positions, rewind_shot, spectator_view


# The verifier gets contract instances, as NanoAgent's sandbox builds them from JSON.
def verify_input(tool: str, value: dict) -> dict:
    return verifier.verify_input(tool, build_output(value, TOOLS[Tool(tool)][0]))


def verify_task(task: str, arguments: dict, output: dict, workspace: Path) -> dict:
    given, made = TASKS[Task(task)]
    return verifier.verify_task(task, build_output(arguments, given), build_output(output, made), None, str(workspace))


RENDER = {"snapshots": SNAPSHOTS, "delay_ms": 100, "times_ms": [20, 130, 150, 175, 240, 275, 330]}
VIEW = {"events": EVENTS, "broadcast_delay_ms": 5000, "wall_ms": 11000}


def test_approves_the_tools_own_outputs(tmp_path: Path) -> None:
    made = plain_output(render_positions(build_output(RENDER, RenderInput), tmp_path))
    assert verify_task("render-positions", RENDER, made, tmp_path)["valid"] is True
    for changes in ({}, {"aim_x": 400}, {"max_rewind_ms": 100}, {"received_ms": 100}):
        request = {**SHOT, **changes}
        made = plain_output(rewind_shot(build_output(request, RewindInput), tmp_path))
        assert verify_task("rewind-shot", request, made, tmp_path)["valid"] is True
    for wall in (3000, 11000, 14000):
        request = {**VIEW, "wall_ms": wall}
        made = plain_output(spectator_view(build_output(request, SpectatorInput), tmp_path))
        assert verify_task("spectator-view", request, made, tmp_path)["valid"] is True


def test_refuses_a_frame_that_is_off_or_ignores_arrival(tmp_path: Path) -> None:
    made = plain_output(render_positions(build_output(RENDER, RenderInput), tmp_path))
    rounded_down = {"frames": [*made["frames"][:5], {**made["frames"][5], "x": 300}, made["frames"][6]]}
    assert "275 ms" in verify_task("render-positions", RENDER, rounded_down, tmp_path)["message"]
    # Using the 150 ms snapshot before it arrived (at 190) would interpolate instead of hold.
    peeked = {"frames": [*made["frames"][:3], {**made["frames"][3], "status": "interpolated", "x": 150, "y": 25}, *made["frames"][4:]]}
    assert verify_task("render-positions", RENDER, peeked, tmp_path)["valid"] is False
    # Using the lost 100 ms snapshot would put 140 ms at (280, 90) only by luck; claim the snapshot-to-snapshot value.
    lost = {"frames": [*made["frames"][:4], {**made["frames"][4], "x": 280, "y": 95}, *made["frames"][5:]]}
    assert verify_task("render-positions", RENDER, lost, tmp_path)["valid"] is False
    assert "frames for" in verify_task("render-positions", RENDER, {"frames": made["frames"][:-1]}, tmp_path)["message"]


def test_refuses_a_wrong_shot_or_view(tmp_path: Path) -> None:
    made = plain_output(rewind_shot(build_output(SHOT, RewindInput), tmp_path))
    live = {**made, "rewind_ms": 400, "target_x": 400, "distance_sq": 175**2, "status": "miss"}
    assert "rewind to 220" in verify_task("rewind-shot", SHOT, live, tmp_path)["message"]
    edge = {**SHOT, "aim_x": 230}
    made = plain_output(rewind_shot(build_output(edge, RewindInput), tmp_path))
    assert verify_task("rewind-shot", edge, {**made, "status": "miss"}, tmp_path)["valid"] is False
    view = plain_output(spectator_view(build_output(VIEW, SpectatorInput), tmp_path))
    # Showing dee's 9000 ms kill 5 seconds early leaks live information.
    leaked = {**view, "scores": [{"team": "Red", "points": 3}, {"team": "Blue", "points": 2}, {"team": "Green", "points": 0}]}
    assert "scores should be" in verify_task("spectator-view", VIEW, leaked, tmp_path)["message"]
    assert "not shown yet" in verify_task("spectator-view", VIEW, {**view, "hidden": 3}, tmp_path)["message"]
    assert "last shown" in verify_task("spectator-view", VIEW, {**view, "last_player": "dee", "last_time_ms": 9000}, tmp_path)["message"]


JUDGE = {
    "history": HISTORY,
    "shots": [
        {"shot_id": "A", "received_ms": 400, "latency_ms": 80, "aim_x": 225, "aim_y": 0},  # rewinds to 220: hit
        {"shot_id": "B", "received_ms": 410, "latency_ms": 20, "aim_x": 290, "aim_y": 0},  # 290: hit
        {"shot_id": "C", "received_ms": 420, "latency_ms": 150, "aim_x": 175, "aim_y": 5},  # 170, exactly the limit: hit
        {"shot_id": "D", "received_ms": 430, "latency_ms": 60, "aim_x": 400, "aim_y": 0},  # 270, aimed live: miss
        {"shot_id": "E", "received_ms": 440, "latency_ms": 300, "aim_x": 40, "aim_y": 0},  # too old, though it lines up
    ],
    "delay_ms": 100,
    "max_rewind_ms": 250,
    "radius": 10,
}


def test_approves_the_right_judgement(tmp_path: Path) -> None:
    # C was received last of the hits but happened first in game time.
    assert verify_task("judge-shots", JUDGE, {"hits": ["A", "B", "C"], "first_hit": "C"}, tmp_path)["valid"] is True
    no_hits = {**JUDGE, "shots": JUDGE["shots"][3:]}
    assert verify_task("judge-shots", no_hits, {"hits": [], "first_hit": None}, tmp_path)["valid"] is True


@pytest.mark.parametrize(
    ("output", "message"),
    [
        ({"hits": ["A", "B", "C"], "first_hit": "A"}, "first hit in game time is C"),
        ({"hits": ["A", "B", "C", "E"], "first_hit": "C"}, "hits should be"),
        ({"hits": ["A", "B"], "first_hit": "A"}, "hits should be"),
        ({"hits": ["C", "A", "B"], "first_hit": "C"}, "hits should be"),
        ({"hits": ["A", "B", "C", "D"], "first_hit": "C"}, "hits should be"),
        ({"hits": [], "first_hit": None}, "hits should be"),
        ({"hits": ["A", "B", "C"], "first_hit": None}, "first hit in game time is C"),
    ],
)
def test_refuses_a_wrong_judgement(tmp_path: Path, output: dict, message: str) -> None:
    verdict = verify_task("judge-shots", JUDGE, output, tmp_path)
    assert verdict["valid"] is False and message in verdict["message"]


def test_refuses_judging_a_malformed_log(tmp_path: Path) -> None:
    twice = {**JUDGE, "shots": [JUDGE["shots"][0], JUDGE["shots"][0]]}
    assert "unique" in verify_task("judge-shots", twice, {"hits": ["A"], "first_hit": "A"}, tmp_path)["message"]
    slow = {**JUDGE, "shots": [{**JUDGE["shots"][0], "latency_ms": 9000}]}
    assert "A: latency_ms" in verify_task("judge-shots", slow, {"hits": [], "first_hit": None}, tmp_path)["message"]


DELAY = {"snapshots": SNAPSHOTS, "times_ms": [200, 250, 300, 350], "step_ms": 50, "max_delay_ms": 300}


def test_approves_the_smallest_safe_delay(tmp_path: Path) -> None:
    # 0, 50 and 100 run out of snapshots; 150 interpolates every frame.
    assert verify_task("min-safe-delay", DELAY, {"delay_ms": 150}, tmp_path)["valid"] is True
    short = {**DELAY, "max_delay_ms": 100}
    assert verify_task("min-safe-delay", short, {"delay_ms": None}, tmp_path)["valid"] is True


@pytest.mark.parametrize(
    ("delay", "message"),
    [
        (100, "at 100 ms the frame at 350 ms is held"),
        (200, "150 ms is smaller and also safe"),
        (250, "at 250 ms the frame at 200 ms is waiting"),  # longer is not always safer
        (120, "not a candidate"),
        (None, "must not be null"),
    ],
)
def test_refuses_a_wrong_delay(tmp_path: Path, delay: int | None, message: str) -> None:
    verdict = verify_task("min-safe-delay", DELAY, {"delay_ms": delay}, tmp_path)
    assert verdict["valid"] is False and message in verdict["message"]


def test_checks_what_the_types_cannot_say() -> None:
    assert verify_input("render_positions", RENDER)["valid"]
    assert not verify_input("render_positions", {**RENDER, "snapshots": []})["valid"]
    assert not verify_input("render_positions", {**RENDER, "snapshots": [snap(9, 8, 0, 0)]})["valid"]
    assert not verify_input("render_positions", {**RENDER, "snapshots": [snap(5, 5, 0, 0), snap(5, 6, 0, 0)]})["valid"]
    assert not verify_input("render_positions", {**RENDER, "times_ms": [-1]})["valid"]
    assert not verify_input("render_positions", {**RENDER, "delay_ms": 10_001})["valid"]
    assert verify_input("rewind_shot", SHOT)["valid"]
    assert not verify_input("rewind_shot", {**SHOT, "radius": 0})["valid"]
    assert not verify_input("rewind_shot", {**SHOT, "history": []})["valid"]
    assert verify_input("spectator_view", VIEW)["valid"]
    assert not verify_input("spectator_view", {**VIEW, "events": [EVENTS[2], EVENTS[0]]})["valid"]
    assert not verify_input("spectator_view", {**VIEW, "broadcast_delay_ms": -5})["valid"]

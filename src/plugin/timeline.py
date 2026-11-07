"""The netcode math the tools share: input checks, and positions interpolated in integers, rounded half up."""

from __future__ import annotations

import itertools

from contract import FrameStatus, Sample, Snapshot

LIMIT = 1_000_000
MAX_TIMES = 500


def check_range(name: str, value: int, low: int, high: int) -> None:
    if not low <= value <= high:
        raise ValueError(f"{name} must be {low} to {high}, not {value}")


def check_ticks(points: list[Snapshot] | list[Sample], what: str) -> None:
    if not points:
        raise ValueError(f"{what} must hold at least one entry")
    ticks = [point.tick_ms for point in points]
    if ticks[0] < 0 or any(later <= earlier for earlier, later in itertools.pairwise(ticks)):
        raise ValueError(f"{what} must be in increasing tick_ms order from 0, each tick once")
    for point in points:
        if abs(point.x) > LIMIT or abs(point.y) > LIMIT:
            raise ValueError(f"tick {point.tick_ms}: x and y must be -{LIMIT} to {LIMIT}")


def check_snapshots(snapshots: list[Snapshot]) -> None:
    check_ticks(snapshots, "snapshots")
    for snapshot in snapshots:
        if snapshot.arrived_ms is not None and snapshot.arrived_ms < snapshot.tick_ms:
            raise ValueError(f"tick {snapshot.tick_ms}: arrived_ms must be at or after tick_ms")


def check_times(times: list[int]) -> None:
    if not 1 <= len(times) <= MAX_TIMES or any(time < 0 for time in times):
        raise ValueError(f"times_ms must hold 1 to {MAX_TIMES} times, each 0 or more")


def round_half_up(numerator: int, denominator: int) -> int:
    """numerator / denominator (denominator > 0) rounded to the nearest integer, halves up."""
    return (2 * numerator + denominator) // (2 * denominator)


def position_at(points: list[Snapshot] | list[Sample], at: int) -> tuple[FrameStatus, int | None, int | None]:
    """Where ``points`` (in tick order) put the player at server time ``at``."""
    before = after = None
    for point in points:
        if point.tick_ms <= at:
            before = point
        elif after is None:
            after = point
    if before is None:
        return FrameStatus.WAITING, None, None
    if before.tick_ms == at:
        return FrameStatus.INTERPOLATED, before.x, before.y
    if after is None:
        return FrameStatus.HELD, before.x, before.y
    span, gone = after.tick_ms - before.tick_ms, at - before.tick_ms
    x = round_half_up(before.x * span + (after.x - before.x) * gone, span)
    y = round_half_up(before.y * span + (after.y - before.y) * gone, span)
    return FrameStatus.INTERPOLATED, x, y


def arrived_by(snapshots: list[Snapshot], time: int) -> list[Snapshot]:
    """The snapshots the client holds at ``time``: lost ones never arrive."""
    return [snapshot for snapshot in snapshots if snapshot.arrived_ms is not None and snapshot.arrived_ms <= time]

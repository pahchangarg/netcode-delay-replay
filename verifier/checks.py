"""Checks shared by the verifiers: the rules worked out apart from the tools' code, with exact fractions."""

import itertools
import math
from fractions import Fraction

from contract import FrameStatus, ShotStatus

LIMIT = 1_000_000
MAX_TIMES = 500
HALF = Fraction(1, 2)


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def first_problem(*problems):
    return next((problem for problem in problems if problem), None)


def range_problem(name, value, low, high):
    return None if low <= value <= high else f"{name} must be {low} to {high}, not {value}"


def ticks_problem(points, what):
    if not points:
        return f"{what} must hold at least one entry"
    for index, point in enumerate(points):
        if point.tick_ms < 0 or (index and point.tick_ms <= points[index - 1].tick_ms):
            return f"{what} must be in increasing tick_ms order from 0, each tick once"
        if not (-LIMIT <= point.x <= LIMIT and -LIMIT <= point.y <= LIMIT):
            return f"tick {point.tick_ms}: x and y must be -{LIMIT} to {LIMIT}"
    return None


def snapshots_problem(snapshots):
    problem = ticks_problem(snapshots, "snapshots")
    if problem:
        return problem
    for snapshot in snapshots:
        if snapshot.arrived_ms is not None and snapshot.arrived_ms < snapshot.tick_ms:
            return f"tick {snapshot.tick_ms}: arrived_ms must be at or after tick_ms"
    return None


def times_problem(times):
    if not 1 <= len(times) <= MAX_TIMES or min(times) < 0:
        return f"times_ms must hold 1 to {MAX_TIMES} times, each 0 or more"
    return None


def shot_problem(latency, delay, max_rewind, aim_x, aim_y, radius):
    return first_problem(
        range_problem("latency_ms", latency, 0, 5_000),
        range_problem("delay_ms", delay, 0, 10_000),
        range_problem("max_rewind_ms", max_rewind, 0, 10_000),
        range_problem("aim_x", aim_x, -LIMIT, LIMIT),
        range_problem("aim_y", aim_y, -LIMIT, LIMIT),
        range_problem("radius", radius, 1, 10_000),
    )


def rounded(value):
    """The nearest integer to a Fraction, halves up."""
    return math.floor(value + HALF)


def place(points, at):
    """(status, x, y) for server time ``at``, from points in tick order: the pair around ``at``, weighted exactly."""
    if not points or at < points[0].tick_ms:
        return FrameStatus.WAITING, None, None
    last = points[-1]
    if at >= last.tick_ms:
        return (FrameStatus.INTERPOLATED if at == last.tick_ms else FrameStatus.HELD), last.x, last.y
    for start, end in itertools.pairwise(points):
        if start.tick_ms <= at < end.tick_ms:
            share = Fraction(at - start.tick_ms, end.tick_ms - start.tick_ms)
            return (
                FrameStatus.INTERPOLATED,
                rounded(start.x + share * (end.x - start.x)),
                rounded(start.y + share * (end.y - start.y)),
            )
    return FrameStatus.WAITING, None, None


def frames(snapshots, delay, times):
    """[(time, render, status, x, y)] per time: only snapshots that have arrived by then count."""
    out = []
    for time in times:
        held = [snapshot for snapshot in snapshots if snapshot.arrived_ms is not None and snapshot.arrived_ms <= time]
        out.append((time, time - delay, *place(held, time - delay)))
    return out


def shot(history, received, latency, delay, max_rewind, aim_x, aim_y, radius):
    """(rewind, status, target_x, target_y, distance_sq) for one shot under lag compensation."""
    rewind = received - latency - delay
    if latency + delay > max_rewind:
        return rewind, ShotStatus.TOO_OLD, None, None, None
    status, x, y = place(history, rewind)
    if status != FrameStatus.INTERPOLATED:
        return rewind, ShotStatus.NO_HISTORY, None, None, None
    distance = (aim_x - x) * (aim_x - x) + (aim_y - y) * (aim_y - y)
    return rewind, (ShotStatus.HIT if distance <= radius * radius else ShotStatus.MISS), x, y, distance

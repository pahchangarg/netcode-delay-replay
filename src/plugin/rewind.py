"""rewind_shot: lag compensation. The server moves the target back to what the shooter saw, then tests the hit."""

from __future__ import annotations

from pathlib import Path

from contract import FrameStatus, RewindInput, RewindOutput, ShotStatus
from plugin.timeline import LIMIT, check_range, check_ticks, position_at


def rewind_shot(request: RewindInput, workspace: Path) -> RewindOutput:
    check_ticks(request.history, "history")
    check_range("received_ms", request.received_ms, 0, 10**12)
    check_range("latency_ms", request.latency_ms, 0, 5_000)
    check_range("delay_ms", request.delay_ms, 0, 10_000)
    check_range("max_rewind_ms", request.max_rewind_ms, 0, 10_000)
    check_range("aim_x", request.aim_x, -LIMIT, LIMIT)
    check_range("aim_y", request.aim_y, -LIMIT, LIMIT)
    check_range("radius", request.radius, 1, 10_000)
    back = request.latency_ms + request.delay_ms
    rewind = request.received_ms - back
    if back > request.max_rewind_ms:
        return RewindOutput(rewind_ms=rewind, status=ShotStatus.TOO_OLD, target_x=None, target_y=None, distance_sq=None)
    status, x, y = position_at(request.history, rewind)
    if status is not FrameStatus.INTERPOLATED:
        return RewindOutput(rewind_ms=rewind, status=ShotStatus.NO_HISTORY, target_x=None, target_y=None, distance_sq=None)
    distance = (request.aim_x - x) ** 2 + (request.aim_y - y) ** 2
    hit = ShotStatus.HIT if distance <= request.radius**2 else ShotStatus.MISS
    return RewindOutput(rewind_ms=rewind, status=hit, target_x=x, target_y=y, distance_sq=distance)

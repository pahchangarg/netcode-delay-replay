"""render_positions: what the client draws, a delay behind, from the snapshots that have arrived."""

from __future__ import annotations

from pathlib import Path

from contract import Frame, RenderInput, RenderOutput
from plugin.timeline import arrived_by, check_range, check_snapshots, check_times, position_at


def render_positions(request: RenderInput, workspace: Path) -> RenderOutput:
    check_snapshots(request.snapshots)
    check_range("delay_ms", request.delay_ms, 0, 10_000)
    check_times(request.times_ms)
    frames = []
    for time in request.times_ms:
        render = time - request.delay_ms
        status, x, y = position_at(arrived_by(request.snapshots, time), render)
        frames.append(Frame(time_ms=time, render_ms=render, status=status, x=x, y=y))
    return RenderOutput(frames=frames)

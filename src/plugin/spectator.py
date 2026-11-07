"""spectator_view: the delayed broadcast. Viewers see only what happened broadcast_delay_ms ago."""

from __future__ import annotations

from pathlib import Path

from contract import SpectatorInput, SpectatorOutput, TeamScore
from plugin.timeline import check_range


def spectator_view(request: SpectatorInput, workspace: Path) -> SpectatorOutput:
    check_range("broadcast_delay_ms", request.broadcast_delay_ms, 0, 600_000)
    check_range("wall_ms", request.wall_ms, 0, 10**12)
    previous = 0
    for number, event in enumerate(request.events, 1):
        if event.time_ms < previous:
            raise ValueError(f"event {number}: events must be in time order, from 0")
        if not event.team.strip() or not event.player.strip():
            raise ValueError(f"event {number}: team and player must not be blank")
        check_range(f"event {number}: points", event.points, 1, 100)
        previous = event.time_ms
    shown_until = request.wall_ms - request.broadcast_delay_ms
    points = {event.team: 0 for event in request.events}
    last = None
    hidden = 0
    for event in request.events:
        if event.time_ms <= shown_until:
            points[event.team] += event.points
            last = event
        elif event.time_ms <= request.wall_ms:
            hidden += 1
    ranked = sorted(points.items(), key=lambda item: (-item[1], item[0]))
    return SpectatorOutput(
        shown_until_ms=shown_until,
        scores=[TeamScore(team=team, points=total) for team, total in ranked],
        last_time_ms=None if last is None else last.time_ms,
        last_player=None if last is None else last.player,
        hidden=hidden,
    )

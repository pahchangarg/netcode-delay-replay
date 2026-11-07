"""Each tool's and task's typed input and output (see nanoagent.plugin.v0001.contract): declarations only."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    RENDER_POSITIONS = "render_positions"
    REWIND_SHOT = "rewind_shot"
    SPECTATOR_VIEW = "spectator_view"


class Task(Enum):
    RENDER_POSITIONS = "render-positions"
    REWIND_SHOT = "rewind-shot"
    SPECTATOR_VIEW = "spectator-view"
    JUDGE_SHOTS = "judge-shots"
    MIN_SAFE_DELAY = "min-safe-delay"


class FrameStatus(Enum):
    INTERPOLATED = "interpolated"
    HELD = "held"
    WAITING = "waiting"


class ShotStatus(Enum):
    HIT = "hit"
    MISS = "miss"
    TOO_OLD = "too_old"
    NO_HISTORY = "no_history"


SNAPSHOTS = "The server's snapshots of one player, in increasing tick_ms order, each tick once"
HISTORY = "The server's record of the target player, in increasing tick_ms order, each tick once"
X = "Game units, an integer from -1000000 to 1000000"
DELAY = "The client's render (interpolation) delay in ms, 0 to 10000: it draws the world this long in the past"
RADIUS = "The target's hit radius in game units, 1 to 10000"
MAX_REWIND = "The longest the server rewinds, in ms, 0 to 10000; a shot needing more is too_old"


@dataclass
class Snapshot(Output):
    tick_ms: Annotated[int, "The server time this snapshot describes, in ms, 0 or more"]
    arrived_ms: Annotated[int | None, "When it reached the client, in ms, at or after tick_ms; null if it was lost"]
    x: Annotated[int, X]
    y: Annotated[int, X]


@dataclass
class Sample(Output):
    tick_ms: Annotated[int, "The server time, in ms, 0 or more"]
    x: Annotated[int, X]
    y: Annotated[int, X]


@dataclass
class Frame(Output):
    time_ms: Annotated[int, "The client's clock when the frame is drawn"]
    render_ms: Annotated[int, "time_ms minus the delay: the server time the frame shows"]
    status: Annotated[
        FrameStatus,
        "interpolated between the arrived snapshots around render_ms (or exactly on one); held at the newest arrived"
        " snapshot when none newer than render_ms has arrived; waiting when no arrived snapshot is at or before render_ms",
    ]
    x: Annotated[int | None, "The drawn position, rounded half up to a whole unit; null when waiting"]
    y: Annotated[int | None, "The drawn position, rounded half up to a whole unit; null when waiting"]


@dataclass
class RenderInput(Output):
    snapshots: Annotated[list[Snapshot], SNAPSHOTS]
    delay_ms: Annotated[int, DELAY]
    times_ms: Annotated[list[int], "The client clock times to draw a frame at, in ms, 0 or more, 1 to 500 of them"]


@dataclass
class RenderOutput(Output):
    frames: Annotated[list[Frame], "One frame per time, in the times' order"]


@dataclass
class RewindInput(Output):
    history: Annotated[list[Sample], HISTORY]
    received_ms: Annotated[int, "When the server received the shot, in ms"]
    latency_ms: Annotated[int, "The shooter's one-way latency in ms, 0 to 5000"]
    delay_ms: Annotated[int, DELAY]
    max_rewind_ms: Annotated[int, MAX_REWIND]
    aim_x: Annotated[int, "Where the shooter aimed, game units"]
    aim_y: Annotated[int, "Where the shooter aimed, game units"]
    radius: Annotated[int, RADIUS]


@dataclass
class RewindOutput(Output):
    rewind_ms: Annotated[int, "received_ms minus latency_ms minus delay_ms: the server time the shooter was seeing"]
    status: Annotated[
        ShotStatus,
        "too_old when latency_ms + delay_ms exceeds max_rewind_ms; else no_history when rewind_ms is outside the"
        " history; else hit when the squared distance from the aim to the target is at most radius squared; else miss",
    ]
    target_x: Annotated[int | None, "The target at rewind_ms, interpolated and rounded half up; null if too_old or no_history"]
    target_y: Annotated[int | None, "The target at rewind_ms, interpolated and rounded half up; null if too_old or no_history"]
    distance_sq: Annotated[int | None, "The squared distance from the aim to (target_x, target_y); null if too_old or no_history"]


@dataclass
class Event(Output):
    time_ms: Annotated[int, "When it happened, server time in ms, 0 or more"]
    team: Annotated[str, "The scoring team"]
    player: Annotated[str, "The scoring player"]
    points: Annotated[int, "Points scored, 1 to 100"]


@dataclass
class TeamScore(Output):
    team: Annotated[str, "The team"]
    points: Annotated[int, "Its points that spectators can see"]


@dataclass
class SpectatorInput(Output):
    events: Annotated[list[Event], "The match's scoring events in time order"]
    broadcast_delay_ms: Annotated[int, "How far behind the live match the spectator feed runs, in ms, 0 to 600000, e.g. 5000"]
    wall_ms: Annotated[int, "The live match time when the spectator looks, in ms, 0 or more"]


@dataclass
class SpectatorOutput(Output):
    shown_until_ms: Annotated[int, "wall_ms minus broadcast_delay_ms: events at or before it are shown; negative before the feed starts"]
    scores: Annotated[
        list[TeamScore],
        "Every team in the events with its shown points, most points first, then by team name",
    ]
    last_time_ms: Annotated[int | None, "The time of the last shown event, or null if none is shown"]
    last_player: Annotated[str | None, "The player of the last shown event (the later in the list on a tie), or null"]
    hidden: Annotated[int, "Events that have happened by wall_ms but are not shown yet"]


@dataclass
class Shot(Output):
    shot_id: Annotated[str, "The shot's id, unique in the log"]
    received_ms: Annotated[int, "When the server received the shot, in ms"]
    latency_ms: Annotated[int, "The shooter's one-way latency in ms, 0 to 5000"]
    aim_x: Annotated[int, "Where the shooter aimed, game units"]
    aim_y: Annotated[int, "Where the shooter aimed, game units"]


@dataclass
class JudgeInput(Output):
    history: Annotated[list[Sample], HISTORY]
    shots: Annotated[list[Shot], "The shots at the target, in the order the server received them, 1 to 100"]
    delay_ms: Annotated[int, "Every shooter's render delay in ms, 0 to 10000"]
    max_rewind_ms: Annotated[int, MAX_REWIND]
    radius: Annotated[int, RADIUS]


@dataclass
class JudgeOutput(Output):
    hits: Annotated[list[str], "The shot_ids that hit after lag compensation, in the shots' order"]
    first_hit: Annotated[
        str | None,
        "The hit with the earliest rewind_ms (the earlier in the shots' order on a tie), or null if none hit",
    ]


@dataclass
class DelayInput(Output):
    snapshots: Annotated[list[Snapshot], SNAPSHOTS]
    times_ms: Annotated[list[int], "The client clock times to draw a frame at, in ms, 0 or more, 1 to 500 of them"]
    step_ms: Annotated[int, "The candidate delays are 0, step_ms, 2 * step_ms, ...; 1 to 1000"]
    max_delay_ms: Annotated[int, "The largest candidate delay, in ms, 0 to 10000"]


@dataclass
class DelayOutput(Output):
    delay_ms: Annotated[
        int | None,
        "The smallest candidate delay at which every frame is interpolated (none held or waiting), or null if none is",
    ]


TOOLS = {
    Tool.RENDER_POSITIONS: (RenderInput, RenderOutput),
    Tool.REWIND_SHOT: (RewindInput, RewindOutput),
    Tool.SPECTATOR_VIEW: (SpectatorInput, SpectatorOutput),
}
TASKS = {
    Task.RENDER_POSITIONS: (RenderInput, RenderOutput),
    Task.REWIND_SHOT: (RewindInput, RewindOutput),
    Task.SPECTATOR_VIEW: (SpectatorInput, SpectatorOutput),
    Task.JUDGE_SHOTS: (JudgeInput, JudgeOutput),
    Task.MIN_SAFE_DELAY: (DelayInput, DelayOutput),
}

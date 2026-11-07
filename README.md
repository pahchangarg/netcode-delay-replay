# Netcode Delay Replay

A `nanoagent.plugin/v0001` plugin, made from the structure of NanoAgent's
reference plugin, [arxiv-source](https://github.com/zeyuyang8/arxiv-source).
Online games never draw a player's live position. The client buffers server
snapshots and draws the world a little in the past, interpolating between
them; the server rewinds time to judge a shot against what the shooter saw
(lag compensation); and spectator feeds run seconds behind so viewers cannot
pass live information to players. This plugin works out each of these exactly,
from the inputs given, so every answer can be checked.

## Tools

| Tool | Does | Code |
|---|---|---|
| `render_positions` | Draws a frame at each client time, `delay_ms` in the past, from the snapshots that have arrived by then: interpolated, held at the newest, or waiting | `src/plugin/render.py` |
| `rewind_shot` | Rewinds the target to `received_ms - latency_ms - delay_ms` and tests the hit against the radius; too_old past `max_rewind_ms`, no_history outside the record | `src/plugin/rewind.py` |
| `spectator_view` | Shows the events at or before `wall_ms - broadcast_delay_ms`: team scores, the last shown event, and how many events are still hidden | `src/plugin/spectator.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `render-positions` | Shows where the client draws a player at each time | `tool`, with `render_positions` |
| `rewind-shot` | Decides one shot with lag compensation | `tool`, with `rewind_shot` |
| `spectator-view` | Shows what the delayed spectator feed reveals | `tool`, with `spectator_view` |
| `judge-shots` | Decides which shots in a log hit, and which hit first in game time | `agent`, with `rewind_shot` |
| `min-safe-delay` | Finds the smallest render delay at which no frame is held or waiting | `agent`, with `render_positions` |

The rules:

- Times are whole milliseconds and positions whole game units. A position
  between two snapshots is interpolated linearly and rounded half up to a
  whole unit.
- A frame uses only the snapshots that have arrived by its client time; a lost
  snapshot (`arrived_ms: null`) never arrives. It is `interpolated` when
  arrived snapshots lie at or before and after the render time (or one lies
  exactly on it), `held` at the newest when none newer has arrived, and
  `waiting` when none is at or before it.
- A shot hits when the squared distance from the aim to the rewound target is
  at most the radius squared. `too_old` is checked before `no_history`.
- `first_hit` is the hit with the smallest rewind time, which can differ from
  the first shot the server received.
- In `min-safe-delay` a longer delay is not always safer: it can reach back
  before the first snapshot.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs (none)
├── src/plugin/      # the MCP server: __main__.py, its IMPLEMENTATIONS, and one module per tool
├── tests/           # the tools' tests and the verifier's
├── ui/              # outputs are drawn from their JSON Schema
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package
```

The tools interpolate in integer arithmetic (`src/plugin/timeline.py`).
`verifier/` works every answer out again with its own code
(`verifier/checks.py`): it finds the pair of snapshots around a time by
scanning consecutive pairs, weights them with exact `fractions`, and rounds
with `math.floor(value + 1/2)`. Tool outputs must match exactly. For
`judge-shots` it checks the list of hits and the first hit in game time; for
`min-safe-delay` it tries every candidate delay and checks that the answer is
safe and that no smaller candidate is.

## Develop and run

```bash
uv sync --extra dev
uv run pytest
```

The plugin needs no network and no environment variables.

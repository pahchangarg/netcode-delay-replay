"""render_positions and the render-positions task: every frame must be the one the rules give."""

from .checks import first_problem, frames, range_problem, result, snapshots_problem, times_problem


def input_problem(value):
    return first_problem(
        snapshots_problem(value.snapshots),
        range_problem("delay_ms", value.delay_ms, 0, 10_000),
        times_problem(value.times_ms),
    )


def verify_input(value):
    problem = input_problem(value)
    return result(problem is None, problem or "a valid render request")


def verify_output(given, made, workspace):
    problem = input_problem(given)
    if problem:
        return result(False, f"the request is not valid: {problem}")
    expected = frames(given.snapshots, given.delay_ms, given.times_ms)
    got = [(frame.time_ms, frame.render_ms, frame.status, frame.x, frame.y) for frame in made.frames]
    if len(got) != len(expected):
        return result(False, f"{len(got)} frames for {len(expected)} times")
    for want, have in zip(expected, got):
        if want != have:
            time, render, status, x, y = want
            return result(False, f"the frame at {time} ms should show {render} ms as {status.value} at ({x}, {y})")
    held = sum(1 for frame in expected if frame[2].value != "interpolated")
    return result(True, f"{len(expected)} frames, {held} held or waiting", frames=len(expected), held=held)

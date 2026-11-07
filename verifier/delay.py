"""The min-safe-delay task: the smallest candidate delay at which no frame is held or waiting."""

from .checks import first_problem, frames, range_problem, result, snapshots_problem, times_problem


def input_problem(value):
    return first_problem(
        snapshots_problem(value.snapshots),
        times_problem(value.times_ms),
        range_problem("step_ms", value.step_ms, 1, 1_000),
        range_problem("max_delay_ms", value.max_delay_ms, 0, 10_000),
    )


def first_unsafe(value, delay):
    """The first frame that is not interpolated at this delay, or None when all are."""
    return next((frame for frame in frames(value.snapshots, delay, value.times_ms) if frame[2].value != "interpolated"), None)


def verify_task(arguments, output, reference, workspace):
    problem = input_problem(arguments)
    if problem:
        return result(False, f"the request is not valid: {problem}")
    candidates = list(range(0, arguments.max_delay_ms + 1, arguments.step_ms))
    safe = next((delay for delay in candidates if first_unsafe(arguments, delay) is None), None)
    given = output.delay_ms
    if given is None:
        if safe is None:
            return result(True, "no candidate delay is safe, and the output says so")
        return result(False, f"delay {safe} ms is safe, so delay_ms must not be null", expected=safe)
    if given not in candidates:
        return result(False, f"{given} ms is not a candidate: a multiple of {arguments.step_ms} up to {arguments.max_delay_ms}")
    bad = first_unsafe(arguments, given)
    if bad is not None:
        return result(False, f"at {given} ms the frame at {bad[0]} ms is {bad[2].value}", expected=safe)
    if given != safe:
        return result(False, f"{safe} ms is smaller and also safe", expected=safe)
    return result(True, f"{safe} ms is the smallest safe delay", delay_ms=safe)

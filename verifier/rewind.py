"""rewind_shot and the rewind-shot task: the rewound target and the hit test must follow the rules."""

from .checks import first_problem, range_problem, result, shot, shot_problem, ticks_problem


def input_problem(value):
    return first_problem(
        ticks_problem(value.history, "history"),
        range_problem("received_ms", value.received_ms, 0, 10**12),
        shot_problem(value.latency_ms, value.delay_ms, value.max_rewind_ms, value.aim_x, value.aim_y, value.radius),
    )


def verify_input(value):
    problem = input_problem(value)
    return result(problem is None, problem or "a valid shot")


def verify_output(given, made, workspace):
    problem = input_problem(given)
    if problem:
        return result(False, f"the request is not valid: {problem}")
    expected = shot(given.history, given.received_ms, given.latency_ms, given.delay_ms, given.max_rewind_ms,
                    given.aim_x, given.aim_y, given.radius)
    got = (made.rewind_ms, made.status, made.target_x, made.target_y, made.distance_sq)
    if got != expected:
        rewind, status, x, y, distance = expected
        return result(False, f"the shot should rewind to {rewind} ms and be {status.value} "
                             f"(target ({x}, {y}), distance_sq {distance})")
    return result(True, f"rewound to {expected[0]} ms: {expected[1].value}", status=expected[1].value)

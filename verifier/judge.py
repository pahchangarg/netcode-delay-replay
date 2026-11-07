"""The judge-shots task: which shots hit after lag compensation, and which hit first in game time."""

from .checks import first_problem, range_problem, result, shot, shot_problem, ticks_problem


def input_problem(value):
    problem = first_problem(
        ticks_problem(value.history, "history"),
        range_problem("shots", len(value.shots), 1, 100),
    )
    if problem:
        return problem
    ids = [entry.shot_id for entry in value.shots]
    if len(set(ids)) != len(ids) or any(not shot_id.strip() for shot_id in ids):
        return "shot_ids must be unique and not blank"
    for entry in value.shots:
        problem = first_problem(
            range_problem(f"{entry.shot_id}: received_ms", entry.received_ms, 0, 10**12),
            shot_problem(entry.latency_ms, value.delay_ms, value.max_rewind_ms, entry.aim_x, entry.aim_y, value.radius),
        )
        if problem:
            return problem if problem.startswith(entry.shot_id) else f"{entry.shot_id}: {problem}"
    return None


def verify_task(arguments, output, reference, workspace):
    problem = input_problem(arguments)
    if problem:
        return result(False, f"the request is not valid: {problem}")
    hits = []
    for entry in arguments.shots:
        rewind, status, _x, _y, _d = shot(arguments.history, entry.received_ms, entry.latency_ms, arguments.delay_ms,
                                           arguments.max_rewind_ms, entry.aim_x, entry.aim_y, arguments.radius)
        if status.value == "hit":
            hits.append((rewind, entry.shot_id))
    want = [shot_id for _rewind, shot_id in hits]
    if output.hits != want:
        missed = [shot_id for shot_id in want if shot_id not in output.hits]
        extra = [shot_id for shot_id in output.hits if shot_id not in want]
        return result(False, f"hits should be {want}", missing=missed, extra=extra)
    first = min(hits, key=lambda pair: pair[0])[1] if hits else None
    if output.first_hit != first:
        return result(False, f"the first hit in game time is {first}, not {output.first_hit}")
    return result(True, f"{len(want)} of {len(arguments.shots)} shots hit; first in game time: {first}", hits=len(want))

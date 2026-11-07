"""spectator_view and the spectator-view task: only events old enough for the broadcast may show."""

from .checks import first_problem, range_problem, result


def input_problem(value):
    problem = first_problem(
        range_problem("broadcast_delay_ms", value.broadcast_delay_ms, 0, 600_000),
        range_problem("wall_ms", value.wall_ms, 0, 10**12),
    )
    if problem:
        return problem
    for number, event in enumerate(value.events, 1):
        if event.time_ms < (value.events[number - 2].time_ms if number > 1 else 0):
            return f"event {number}: events must be in time order, from 0"
        if not event.team.strip() or not event.player.strip():
            return f"event {number}: team and player must not be blank"
        problem = range_problem(f"event {number}: points", event.points, 1, 100)
        if problem:
            return problem
    return None


def expected_view(value):
    cutoff = value.wall_ms - value.broadcast_delay_ms
    shown = [event for event in value.events if event.time_ms <= cutoff]
    teams = sorted({event.team for event in value.events})
    totals = [(team, sum(event.points for event in shown if event.team == team)) for team in teams]
    # sorted() is stable, so equal totals stay in team-name order.
    scores = sorted(totals, key=lambda pair: -pair[1])
    last = shown[-1] if shown else None
    hidden = len([event for event in value.events if cutoff < event.time_ms <= value.wall_ms])
    return cutoff, scores, (last.time_ms if last else None), (last.player if last else None), hidden


def verify_input(value):
    problem = input_problem(value)
    return result(problem is None, problem or "a valid spectator request")


def verify_output(given, made, workspace):
    problem = input_problem(given)
    if problem:
        return result(False, f"the request is not valid: {problem}")
    cutoff, scores, last_time, last_player, hidden = expected_view(given)
    if made.shown_until_ms != cutoff:
        return result(False, f"shown_until_ms should be {cutoff}")
    if [(score.team, score.points) for score in made.scores] != scores:
        return result(False, f"the scores should be {scores}")
    if (made.last_time_ms, made.last_player) != (last_time, last_player):
        return result(False, f"the last shown event should be {last_player} at {last_time} ms")
    if made.hidden != hidden:
        return result(False, f"{hidden} events have happened but are not shown yet, not {made.hidden}")
    return result(True, f"spectators see up to {cutoff} ms; events still hidden: {hidden}", hidden=hidden)

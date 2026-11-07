"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import delay, judge, render, rewind, spectator

TOOLS = {Tool.RENDER_POSITIONS: render, Tool.REWIND_SHOT: rewind, Tool.SPECTATOR_VIEW: spectator}


def _tool_output(module):
    """A tool task's check: its output judged as its one tool's verify_output judges it."""
    return lambda arguments, output, reference, workspace: module.verify_output(arguments, output, workspace)


# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {
    Task.RENDER_POSITIONS: _tool_output(render),
    Task.REWIND_SHOT: _tool_output(rewind),
    Task.SPECTATOR_VIEW: _tool_output(spectator),
    Task.JUDGE_SHOTS: judge.verify_task,
    Task.MIN_SAFE_DELAY: delay.verify_task,
}


def verify_input(tool, value):
    return TOOLS[Tool(tool)].verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)].verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)

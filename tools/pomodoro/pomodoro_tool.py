from langchain.tools import tool

from tools.pomodoro.pomodoro_timer_manager import PomodoroTimerManager


@tool
def start_pomodoro_timer(duration_minutes: int = 90) -> str:
    """
    Start a Pomodoro timer with a specified duration.

    This tool accepts a duration in minutes for the timer.
    The default duration is 90 minutes if no specific time is provided.

    Examples:
        - 25 for a 25-minute timer
        - 15 for a 15-minute break
        - Any value from 1 to 120 minutes is accepted

    Args:
        duration_minutes: Duration in minutes (default: 90)

    Returns:
        Confirmation message with the timer duration
    """
    if PomodoroTimerManager().is_running:
        remaining = PomodoroTimerManager().get_remaining_minutes()
        return f"A timer is already running with {remaining} minutes remaining. Stop it first if you want to start a new one."

    duration_minutes = max(1, min(120, duration_minutes))

    PomodoroTimerManager().start_timer(duration_minutes)

    end_time = PomodoroTimerManager().get_end_time_formatted()

    if end_time:
        return f"Pomodoro timer started for {duration_minutes} minutes. It will finish at {end_time}."

    return f"Pomodoro timer started for {duration_minutes} minutes."


@tool
def stop_pomodoro_timer() -> str:
    """
    Stop the currently running Pomodoro timer.

    This tool stops any active Pomodoro timer.

    Returns:
        Confirmation message about stopping the timer
    """
    if not PomodoroTimerManager().is_running:
        return "No active Pomodoro timer to stop."

    PomodoroTimerManager().stop_timer()
    return "Pomodoro timer stopped."


@tool
def get_pomodoro_status() -> str:
    """
    Get the status of the current Pomodoro timer.

    This tool provides information about any running timer, including
    remaining time and expected completion time.

    Returns:
        Status message about the current timer
    """
    if not PomodoroTimerManager().is_running:
        return "No Pomodoro timer is currently running."

    minutes_remaining = PomodoroTimerManager().get_remaining_minutes()
    end_time = PomodoroTimerManager().get_end_time_formatted()

    if minutes_remaining <= 1:
        if end_time:
            return f"Pomodoro timer is almost done! It will finish at {end_time}."
        return "Pomodoro timer is almost done!"

    if end_time:
        return f"Pomodoro timer has {minutes_remaining} minutes remaining. It will finish at {end_time}."

    return f"Pomodoro timer has {minutes_remaining} minutes remaining."

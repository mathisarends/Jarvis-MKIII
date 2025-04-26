import json
import re
from typing import Dict, Any, Optional

from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

from tools.pomodoro.pomodoro_timer_manager import PomodoroTimerManager

DEFAULT_POMODORO_MINUTES = 90


def _create_llm() -> ChatGoogleGenerativeAI:
    """Create and configure the LLM for interpreting requests."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.2,
        disable_streaming=True,
    )


def _get_system_prompt() -> SystemMessage:
    """Create the system prompt for the LLM."""
    return SystemMessage(
        content=f"""
    Analyze the user's request and determine which Pomodoro timer action to take.
    Return only a JSON object with the following structure:
    
    For starting a timer:
    {{"action": "start", "duration_minutes": <number>}}
    
    For stopping a timer:
    {{"action": "stop"}}
    
    For checking timer status:
    {{"action": "status"}}
    
    Extract the duration from the user's message if they're asking to start a timer.
    If no specific duration is mentioned, ALWAYS use {DEFAULT_POMODORO_MINUTES} minutes as the default duration.
    This is very important: the standard Pomodoro duration in this system is {DEFAULT_POMODORO_MINUTES} minutes, NOT 25 minutes.
    Even if the user asks for a "pomodoro" without specifying time, use {DEFAULT_POMODORO_MINUTES} minutes.
    """
    )


def _parse_llm_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON from LLM response."""
    json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
    if not json_match:
        return None

    try:
        return json.loads(json_match.group(0))
    except json.JSONDecodeError:
        return None


def _handle_start_action(
    action_json: Dict[str, Any], manager: PomodoroTimerManager
) -> str:
    """Handle the start timer action."""
    if manager.is_running:
        remaining = manager.get_remaining_minutes()
        return f"A timer is already running with {remaining} minutes remaining. Stop it first if you want to start a new one."

    duration = action_json.get("duration_minutes", DEFAULT_POMODORO_MINUTES)

    if duration == 25 and "duration_minutes" not in action_json:
        duration = DEFAULT_POMODORO_MINUTES

    # Limits einhalten
    duration = max(1, min(120, duration))

    manager.start_timer(duration)

    end_time = manager.get_end_time_formatted()
    if end_time:
        return f"Pomodoro timer started for {duration} minutes. It will finish at {end_time}."
    return f"Pomodoro timer started for {duration} minutes."


def _handle_stop_action(manager: PomodoroTimerManager) -> str:
    """Handle the stop timer action."""
    if not manager.is_running:
        return "No active Pomodoro timer to stop."

    manager.stop_timer()
    return "Pomodoro timer stopped."


def _handle_status_action(manager: PomodoroTimerManager) -> str:
    """Handle the status check action."""
    if not manager.is_running:
        return "No Pomodoro timer is currently running."

    minutes_remaining = manager.get_remaining_minutes()
    end_time = manager.get_end_time_formatted()

    if minutes_remaining <= 1:
        if end_time:
            return f"Pomodoro timer is almost done! It will finish at {end_time}."
        return "Pomodoro timer is almost done!"

    if end_time:
        return f"Pomodoro timer has {minutes_remaining} minutes remaining. It will finish at {end_time}."
    return f"Pomodoro timer has {minutes_remaining} minutes remaining."


@tool
def pomodoro_tool(input_text: str) -> str:
    """
    A unified tool to manage Pomodoro timers based on natural language input.

    This tool interprets user requests to start, stop, or check pomodoro timers.
    It uses an LLM internally to determine what the user wants to do.

    The default Pomodoro duration is 90 minutes unless otherwise specified.

    Examples:
      - "Start a 25-minute timer"
      - "Start a pomodoro" (will start a 90-minute timer)
      - "How much time is left in my current session?"
      - "Stop my timer"
      - "Give me a 15 minute break timer"

    Args:
        input_text: The user's request in natural language

    Returns:
        A response message about the timer action taken
    """
    try:
        llm = _create_llm()
        system_message = _get_system_prompt()
        user_message = HumanMessage(content=input_text)
        response = llm.invoke([system_message, user_message])

        action_json = _parse_llm_response(response.content)
        if not action_json:
            return "I couldn't understand what you want to do with the timer. Please try again."

        action = action_json.get("action", "").lower()
        if not action:
            return "I couldn't determine what timer action you want to perform. Please try again."

        manager = PomodoroTimerManager()

        # Handle actions with early returns
        if action == "start":
            return _handle_start_action(action_json, manager)

        if action == "stop":
            return _handle_stop_action(manager)

        if action == "status":
            return _handle_status_action(manager)

        return f"Unknown action: {action}. Please use start, stop, or status."

    except Exception as e:
        return f"An error occurred: {str(e)}. Please try again with a clearer request."

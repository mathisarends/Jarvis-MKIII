import datetime
from langchain.tools import tool

@tool
def get_current_time() -> str:
    """
    Returns the current date and time in a human-readable format.
    """
    now = datetime.datetime.now()
    return now.strftime("Date: %Y-%m-%d Time: %H:%M:%S")
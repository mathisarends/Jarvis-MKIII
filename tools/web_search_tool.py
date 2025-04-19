from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults


@tool
def web_search_tool(query: str) -> str:
    """
    Search the web for up-to-date information on a given topic.

    Args:
        query: The search query.
    """
    tavily_tool = TavilySearchResults(max_results=2, search_depth="basic")
    return tavily_tool.invoke(query)

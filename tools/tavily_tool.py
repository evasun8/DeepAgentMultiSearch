# ======================== Import Core Dependencies ========================
# Typing: Enhances code hints and static analysis
from typing import Literal
# LangChain tool decorator: Converts functions into Agent-callable tools
from langchain_core.tools import tool
# Tavily official client: Implements core web search functionality
from tavily import TavilyClient

# System/Third-party dependencies
import os  # Handles system paths and environment variables
from dotenv import load_dotenv  # Loads environment variables from a .env file

# Custom module: Tool call monitoring/telemetry
from api.monitor import monitor


load_dotenv()

tavily_clinet = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

@tool
def internet_search(
    query: str,
    topic: Literal["news", "finance", "general"] = "general",
    max_results: int = 5,
    include_raw_content: bool = False,
) -> str:

    """
    Perform a web search based on the user's query.
    
    Note: Primarily searches for public web information. Do not use this tool 
    if the query specifically requires internal database or RAG data.
    
    :param query: The user's search query.
    :param topic: The category of the search.
    :param max_results: Maximum number of search results to return.
    :param include_raw_content: Whether to include raw source content (False for concise, True for detailed).
    :return: Search results from Tavily.
    """
    
    # Monitor tool call
    monitor.report_tool(
        tool_name="internet_search",
        args={  
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "include_raw_content": include_raw_content,
        },      
    )

    return tavily_clinet.search(
        query=query,
        topic=topic,
        max_results=max_results,
        include_raw_content=include_raw_content
    )
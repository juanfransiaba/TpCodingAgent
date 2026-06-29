import os

from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()


def web_search(query: str) -> str:
    """Searches information on the web using Tavily."""
    try:
        tavily_key = os.getenv("TAVILY_API_KEY")

        if not tavily_key:
            return "Error: TAVILY_API_KEY is not configured."

        client = TavilyClient(api_key=tavily_key)
        results = client.search(query=query, max_results=3)

        output = f"Results for '{query}':\n"

        for result in results.get("results", []):
            title = result.get("title", "No title")
            url = result.get("url", "No url")
            content = result.get("content", "")

            output += f"\n- {title}\n  {url}\n  {content[:300]}...\n"

        return output

    except Exception as error:
        return f"Error in web_search: {error}"

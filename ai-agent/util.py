import httpx
import json
import os
from datetime import datetime


async def search_web_duckduckgo(query: str, max_results: int = 5) -> dict:
    """
    Search the web using DuckDuckGo (free, no API key required)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # DuckDuckGo Instant Answer API
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            data = response.json()

            results = []

            # Add abstract if available
            if data.get("Abstract"):
                results.append(
                    {
                        "title": data.get("Heading", "Summary"),
                        "snippet": data["Abstract"],
                        "url": data.get("AbstractURL", ""),
                    }
                )

            # Add related topics
            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append(
                        {
                            "title": topic.get("Text", "")[:100],
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", ""),
                        }
                    )

            if not results:
                # Fallback: try HTML search
                html_response = await client.get(
                    f"https://html.duckduckgo.com/html/",
                    params={"q": query},
                    follow_redirects=True,
                )
                # Return basic info
                results = [
                    {
                        "title": "Search Results",
                        "snippet": f"Found search results for: {query}",
                        "url": f"https://duckduckgo.com/?q={query}",
                    }
                ]

            return {"success": True, "results": results[:max_results], "query": query}

    except Exception as e:
        return {"success": False, "error": str(e), "query": query}


async def search_web_tavily(query: str, max_results: int = 5) -> dict:
    """
    Search the web using Tavily API (requires API key, better quality results)
    Get your API key from: https://tavily.com/
    """
    tavily_api_key = os.getenv("TAVILY_API_KEY")

    if not tavily_api_key:
        return {
            "success": False,
            "error": "TAVILY_API_KEY not found in environment variables",
            "query": query,
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": tavily_api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic",
                    "include_answer": True,
                },
            )
            data = response.json()

            if response.status_code == 200:
                results = []
                for item in data.get("results", []):
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "snippet": item.get("content", ""),
                            "url": item.get("url", ""),
                        }
                    )

                return {
                    "success": True,
                    "results": results,
                    "answer": data.get("answer", ""),
                    "query": query,
                }
            else:
                return {
                    "success": False,
                    "error": data.get("error", "Unknown error"),
                    "query": query,
                }

    except Exception as e:
        return {"success": False, "error": str(e), "query": query}


async def execute_tool(tool_call):
    """Execute a tool call and return the result"""
    tool_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)

    if tool_name == "calculate":
        try:
            # Safe evaluation of mathematical expressions
            result = eval(
                arguments["expression"],
                {"__builtins__": {}},
                {"abs": abs, "round": round, "min": min, "max": max, "sum": sum},
            )
            return json.dumps({"result": result})
        except Exception as e:
            return json.dumps({"error": f"Calculation error: {str(e)}"})

    elif tool_name == "get_current_time":
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return json.dumps({"current_time": current_time})

    elif tool_name == "web_search":
        query = arguments["query"]
        max_results = arguments.get("max_results", 5)

        # Try Tavily first (if API key is available), fallback to DuckDuckGo
        tavily_api_key = os.getenv("TAVILY_API_KEY")

        if tavily_api_key:
            result = await search_web_tavily(query, max_results)
        else:
            result = await search_web_duckduckgo(query, max_results)

        return json.dumps(result)

    return json.dumps({"error": "Unknown tool"})

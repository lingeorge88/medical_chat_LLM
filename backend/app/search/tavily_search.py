from tavily import TavilyClient
from app.search.interface import WebSearchProvider, WebResult
from app import config
from typing import List


class TavilySearch(WebSearchProvider):
    def __init__(self):
        self._client = TavilyClient(api_key=config.TAVILY_API_KEY)

    def search(self, query: str, max_results: int = 5) -> List[WebResult]:
        response = self._client.search(query, max_results=max_results)
        results = []
        for r in response.get("results", []):
            results.append(WebResult(
                title=r["title"],
                url=r["url"],
                content=r["content"][:500],
            ))
        return results

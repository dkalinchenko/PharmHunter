"""Tavily Search API service for company discovery."""

import time
from typing import List, Dict, Optional
from tavily import TavilyClient


class TavilyService:
    """Service wrapper for Tavily search API."""
    
    def __init__(self, api_key: str):
        """
        Initialize Tavily service.
        
        Args:
            api_key: Tavily API key
        """
        self.api_key = api_key
        self._client: Optional[TavilyClient] = None
    
    @property
    def client(self) -> TavilyClient:
        """Lazy-initialize Tavily client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("Tavily API key is required")
            self._client = TavilyClient(api_key=self.api_key)
        return self._client
    
    def search(
        self,
        query: str,
        max_results: int = 10,
        search_depth: str = "advanced",
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search for companies using Tavily.
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            search_depth: "basic" or "advanced" search depth
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            
        Returns:
            List of search results with url, title, content
        """
        print(f"[Tavily] Searching: {query[:60]}... (max_results={max_results})")
        try:
            # Build search parameters
            search_params = {
                "query": query,
                "max_results": max_results,
                "search_depth": search_depth,
            }
            
            if include_domains:
                search_params["include_domains"] = include_domains
            if exclude_domains:
                search_params["exclude_domains"] = exclude_domains
            
            # Execute search
            print(f"[Tavily] Calling API...")
            response = self.client.search(**search_params)
            
            # Extract results
            results = []
            for result in response.get("results", []):
                results.append({
                    "url": result.get("url", ""),
                    "title": result.get("title", ""),
                    "content": result.get("content", ""),
                    "score": result.get("score", 0)
                })
            
            print(f"[Tavily] Got {len(results)} results")
            return results
            
        except Exception as e:
            # Log error and return empty results
            print(f"[Tavily] ERROR: {e}")
            import traceback
            print(traceback.format_exc())
            return []
    
    def search_with_retry(
        self,
        query: str,
        max_results: int = 10,
        max_retries: int = 2,
        delay: float = 1.0
    ) -> List[Dict]:
        """
        Search with automatic retry on failure.
        
        Args:
            query: Search query string
            max_results: Maximum number of results
            max_retries: Maximum retry attempts
            delay: Delay between retries in seconds
            
        Returns:
            List of search results
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                results = self.search(query, max_results)
                if results:
                    return results
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
        
        if last_error:
            print(f"Tavily search failed after {max_retries + 1} attempts: {last_error}")
        
        return []
    
    def search_companies(
        self,
        therapeutic_focus: str,
        phase: str,
        geography: str = "Global",
        exclusions: str = "",
        max_results: int = 10
    ) -> List[Dict]:
        """
        Specialized search for biopharma companies.
        
        Args:
            therapeutic_focus: Therapeutic area focus
            phase: Clinical trial phase
            geography: Geographic focus
            exclusions: Companies to exclude
            max_results: Maximum results
            
        Returns:
            List of search results
        """
        # Build optimized queries for biopharma discovery
        queries = [
            f"{therapeutic_focus} biopharma company {phase} clinical trial imaging endpoints",
            f"{therapeutic_focus} biotech {phase} RECIST PET MRI trial",
            f"biopharma {therapeutic_focus} Series B funding {phase} imaging",
            f"{therapeutic_focus} first patient dosed {phase} imaging trial",
        ]
        
        # Preferred domains for clinical trial info
        include_domains = [
            "clinicaltrials.gov",
            "biospace.com",
            "fiercebiotech.com",
            "businesswire.com",
            "prnewswire.com",
            "sec.gov"
        ]
        
        # Collect results from multiple queries
        all_results = []
        seen_urls = set()
        
        for query in queries:
            results = self.search(
                query=query,
                max_results=max_results // 2,  # Split across queries
                search_depth="advanced"
            )
            
            for result in results:
                url = result.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(result)
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return all_results[:max_results]

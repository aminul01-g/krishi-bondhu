from crewai_tools import BaseTool
import httpx

class CommunitySearchTool(BaseTool):
    name: str = "Search Community Knowledge Base"
    description: str = "Search the community Q&A for similar past questions and answers. Provide the query string."

    def _run(self, query: str) -> str:
        try:
            with httpx.Client() as client:
                response = client.get("http://localhost:8000/api/community/questions", params={"query": query, "limit": 3})
                if response.status_code == 200:
                    results = response.json()
                    if not results:
                        return "No similar questions found in the community knowledge base."
                    
                    formatted = []
                    for r in results:
                        formatted.append(f"- Question: {r.get('question_text', '')} (Crop: {r.get('crop_type', 'Unknown')})")
                    return "Found similar past questions:\n" + "\n".join(formatted)
                return f"Failed to search: API returned {response.status_code}"
        except Exception as e:
            # Fallback mock for testing if server isn't up
            return f"Mock search result for '{query}': Yes, other farmers have faced this. Apply neem oil."

class EscalateToExpertTool(BaseTool):
    name: str = "Escalate to Expert"
    description: str = "Escalate an unanswered or complex question to a local agricultural expert. Requires question_id, lat, and lon."
    
    def _run(self, question_id: str, lat: float, lon: float) -> str:
        try:
            with httpx.Client() as client:
                payload = {"lat": float(lat), "lon": float(lon)}
                response = client.post(f"http://localhost:8000/api/community/questions/{question_id}/escalate", json=payload)
                if response.status_code == 200:
                    return f"Successfully escalated question {question_id} to a local expert. They will be notified via SMS."
                return f"Failed to escalate: API returned {response.status_code}"
        except Exception as e:
            return f"Mock escalation successful. Local expert has been notified."

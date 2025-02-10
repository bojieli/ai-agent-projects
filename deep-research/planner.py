from openai import OpenAI, OpenAIError
import json
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Dict, List
from search import GoogleSearchClient
from utils.api_error_handler import handle_openai_error, APIError

class ResearchPlanner:
    def __init__(self, config):
        self.client = OpenAI(api_key=config.openai_key)
        self.search_client = GoogleSearchClient(config.google_key, config.search_engine_id)
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def generate_plan(self, query: str) -> Dict:
        """Generate research plan and initial search queries"""
        try:
            # Generate initial plan
            prompt = self._create_planning_prompt(query)
            plan = self._get_plan_from_llm(prompt)
            
            # Perform initial searches to validate queries
            search_results = self._test_search_queries(plan['primary_search_queries'])
            
            # Update plan with validated queries
            plan['search_results'] = search_results
            return plan
            
        except Exception as e:
            raise ValueError(f"Failed to generate research plan: {str(e)}")
            
    def _get_plan_from_llm(self, prompt: str) -> Dict:
        """Get plan from LLM with proper error handling"""
        try:
            response = self.client.chat.completions.create(
                model="o3-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            
            try:
                plan = json.loads(response.choices[0].message.content)
                return self._validate_plan(plan)
            except json.JSONDecodeError as e:
                raise APIError(
                    f"Invalid JSON response from LLM: {str(e)}\n"
                    f"Response content: {response.choices[0].message.content}"
                )
                
        except OpenAIError as e:
            raise handle_openai_error(e)
            
    def _test_search_queries(self, queries: List[str]) -> Dict[str, List[Dict]]:
        """Test search queries and return initial results"""
        results = {}
        for query in queries:
            results[query] = self.search_client.search(query, start_index=1)
        return results
        
    def _create_planning_prompt(self, query: str) -> str:
        return f"""Create a detailed research execution plan for: {query}
        Output a JSON object with the following structure:
        {{
            "primary_search_queries": ["query1", "query2"...],
            "required_sections": [
                {{"title": "section_title", "key_points": ["point1", "point2"...]}}
            ],
            "analysis_steps": [
                {{"step": "step_description", "priority": 1-5}}
            ],
            "expected_sources": ["academic_papers", "news_articles", "expert_blogs"...]
        }}"""

    def _validate_plan(self, plan: Dict) -> Dict:
        """Validate the structure of the research plan"""
        required_keys = ["primary_search_queries", "required_sections", "analysis_steps"]
        if not all(key in plan for key in required_keys):
            raise ValueError("Invalid plan structure")
            
        if not plan["primary_search_queries"]:
            raise ValueError("No search queries generated")
            
        return plan 
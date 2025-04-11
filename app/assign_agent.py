import pandas as pd
import json
import re
from get_response import OpenAIClient
from chroma_agent import ChromaAgent
from summarization_agent import SummarizationAgent
from prompts import assignment_agent_prompt

class AssignAgent:
    def __init__(self, openai_client=None, chroma_agent=None, summarization_agent=None):
        """
        Initialize the assignment agent.
        
        Args:
            openai_client (OpenAIClient, optional): Client for OpenAI API
            chroma_agent (ChromaAgent, optional): Agent for ChromaDB operations
            summarization_agent (SummarizationAgent, optional): Agent for summarizing issues
        """
        self.openai_client = openai_client if openai_client else OpenAIClient()
        self.chroma_agent = chroma_agent if chroma_agent else ChromaAgent()
        self.summarization_agent = summarization_agent if summarization_agent else SummarizationAgent(self.openai_client)
        self.prompt_template = assignment_agent_prompt()
        
    def process_and_assign(self, query_text, chat_history=None, n_results=3):
        """
        Process an issue, find similar historical issues, assign a team, and estimate resolution time.
        If no similar issues found, use LLM for team assignment.
        
        Args:
            query_text (str): The query text describing the issue
            chat_history (list, optional): Previous conversation history
            n_results (int): Number of similar results to consider
            
        Returns:
            dict: Contains assigned team, estimated resolution time, and other info
        """
        # First, summarize the issue to get a better query for ChromaDB
        print(f"Getting summary for issue: '{query_text}'")
        summary_result = self.summarization_agent.summarize_issue(query_text)
        
        # Use the summary for querying similar issues
        search_query = summary_result["summary"]
        print(f"Using summary for search: '{search_query}'")
        
        # Get similar issues from ChromaDB
        similar_issues = self.chroma_agent.query(search_query, n_results)
        
        # Debug - print all similar issues and their similarity scores
        print(f"Found {len(similar_issues)} similar issues")
        for i, issue in enumerate(similar_issues):
            print(f"Issue #{i+1}: '{issue['issue']}' - Score: {issue['similarity_score']}")
        
        # Check if we have any good matches (similarity score >= 0.3)
        has_good_matches = any(result['similarity_score'] >= 0.3 for result in similar_issues)
        print(f"Has good matches with score >= 0.3: {has_good_matches}")
        
        if not similar_issues or not has_good_matches:  # If no good matches found
            print("No similar cases found with sufficient similarity. Sending to LLM for assignment...")
            
            # Format previous conversation for context if available
            previous_context = ""
            if chat_history and len(chat_history) > 0:
                previous_context = "Previous conversation:\n"
                for msg in chat_history:
                    role = msg["role"]
                    content = msg["content"]
                    previous_context += f"{role}: {content}\n"
                previous_context += "\n"
            
            # Format the prompt using the template
            user_prompt = self.prompt_template.user_prompt.format(
                previous_context=previous_context,
                query_text=query_text
            )
            system_prompt = self.prompt_template.system_prompt
            
            # Get response from LLM
            llm_response = self.openai_client.get_response(user_prompt, system_prompt, chat_history)
            
            # Parse the JSON from the LLM response
            parsed_data = self._parse_llm_response(llm_response)
            
            if parsed_data:
                return {
                    "source": "LLM",
                    "assigned_team": parsed_data.get("assigned_team"),
                    "estimated_resolution_hours": parsed_data.get("estimated_resolution_hours"),
                    "reason": parsed_data.get("reason"),
                    "similar_cases_found": False,
                    "query_text": query_text,
                    "summary": summary_result["summary"],
                    "raw_response": llm_response
                }
            else:
                # Return unparsed response if parsing fails
                return {
                    "source": "LLM",
                    "response": llm_response,
                    "similar_cases_found": False,
                    "query_text": query_text,
                    "summary": summary_result["summary"],
                    "parsing_failed": True
                }
        
        print("Using historical data for assignment")
        # Process similar issues found
        team_votes = {}
        resolution_times = []
        
        for issue in similar_issues:
            team = issue['metadata']['assigned_team']
            team_votes[team] = team_votes.get(team, 0) + issue['similarity_score']
            
            # Calculate resolution time in hours for this issue
            try:
                open_time = pd.to_datetime(issue['metadata']['ticket_open_date'])
                resolve_time = pd.to_datetime(issue['metadata']['resolution_date'])
                resolution_hours = (resolve_time - open_time).total_seconds() / 3600
                resolution_times.append((resolution_hours, issue['similarity_score']))
            except Exception as e:
                print(f"Error calculating resolution time: {str(e)}")
                # If there's an error, use a default resolution time
                resolution_times.append((24, issue['similarity_score']))  # 24 hours as fallback
        
        # Assign team based on weighted voting
        assigned_team = max(team_votes.items(), key=lambda x: x[1])[0]
        print(f"Team votes: {team_votes}")
        print(f"Assigned team: {assigned_team}")
        
        # Calculate estimated resolution time (weighted average based on similarity scores)
        total_weight = sum(score for _, score in resolution_times)
        estimated_hours = sum(hours * score for hours, score in resolution_times) / total_weight
        
        # Calculate confidence score
        confidence_score = max(team_votes.values()) / sum(team_votes.values())
        
        return {
            "source": "historical_data",
            "assigned_team": assigned_team,
            "estimated_resolution_hours": round(estimated_hours, 2),
            "confidence_score": round(confidence_score, 2),
            "similar_cases": len(similar_issues),
            "similar_issues": similar_issues,
            "query_text": query_text,
            "summary": summary_result["summary"]
        }
    
    def _parse_llm_response(self, response):
        """
        Parse the JSON response from the LLM.
        
        Args:
            response (str): The response from the LLM
            
        Returns:
            dict: Parsed JSON data or None if parsing fails
        """
        try:
            # Try to find JSON in the response using regex
            json_match = re.search(r'```json\s*(\{.*?\})\s*', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            
            # If no match with ```json format, try to find any JSON object
            json_match = re.search(r'\{(?:[^{}]|"[^"]*")*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                return json.loads(json_str)
            
            # If no JSON object found, return None
            print("No JSON format found in LLM response")
            return None
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response JSON: {str(e)}")
            return None 
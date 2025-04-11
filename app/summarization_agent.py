import json
from get_response import OpenAIClient
from prompts import summarization_agent_prompt

class SummarizationAgent:
    def __init__(self, openai_client=None):
        """
        Initialize the summarization agent.
        
        Args:
            openai_client (OpenAIClient, optional): Client for OpenAI API
        """
        self.openai_client = openai_client if openai_client else OpenAIClient()
        self.prompt_template = summarization_agent_prompt()
        
    def summarize_issue(self, query_text, chat_history=None):
        """
        Summarize the issue using the LLM.
        
        Args:
            query_text (str): The text to summarize
            chat_history (list, optional): Previous conversation history
            
        Returns:
            dict: Dictionary containing the summary, sentiment, priority and solution
        """
        try:
            # Format the prompt
            user_prompt = self.prompt_template.user_prompt.format(conversation=query_text)
            system_prompt = self.prompt_template.system_prompt
            
            # Get response from LLM
            response = self.openai_client.get_response(user_prompt, system_prompt, chat_history)
            
            # Try to parse JSON response
            try:
                # Clean the response if it has markdown code blocks
                if response.startswith("```") and response.endswith("```"):
                    response = response.strip("`").strip()
                
                if response.startswith("json") or response.startswith("JSON"):
                    response = response.replace("json", "", 1).replace("JSON", "", 1).strip()
                
                result = json.loads(response)
                return {
                    "summary": result.get("summary", ""),
                    "sentiment": result.get("sentiment", ""),
                    "priority": result.get("priority", ""),
                    "solution": result.get("solution", ""),
                    "raw_response": response
                }
            except json.JSONDecodeError:
                # If not valid JSON, return the raw response
                return {
                    "summary": "Error parsing summary",
                    "sentiment": "Unknown",
                    "priority": "Medium",
                    "solution": "Could not generate solution.",
                    "raw_response": response
                }
        
        except Exception as e:
            return {
                "summary": f"Error: {str(e)}",
                "sentiment": "Unknown",
                "priority": "Medium",
                "solution": "Could not generate solution due to error.",
                "raw_response": f"Error: {str(e)}"
            } 
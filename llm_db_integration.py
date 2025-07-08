#!/usr/bin/env python3
"""
LLM Database Integration

This module integrates the LLM database access layer with the Groq LLM API
to provide enhanced recommendations based on actual database queries.
"""

import json
import os
from typing import Dict, List, Any, Optional
from groq import Groq
from dotenv import load_dotenv
from llm_db_access import LLMDatabaseAccess

# Load environment variables
load_dotenv()

# Initialize Groq client
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set")

groq_client = Groq(api_key=GROQ_API_KEY)

class LLMDatabaseIntegration:
    """
    Integrates the LLM with database access to provide enhanced recommendations.
    """
    
    def __init__(self, db_path: str = 'uber_eats.db'):
        """Initialize the LLM database integration."""
        self.db_access = LLMDatabaseAccess(db_path)
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"
    
    def generate_db_query(self, user_query: str, user_context: Dict[str, Any]) -> str:
        """
        Generate a database query based on the user's natural language query.
        """
        # Create a prompt that helps the LLM formulate a database query
        schema_info = json.dumps(self.db_access.get_schema_info(), indent=2)
        
        prompt = f"""
        # Database Query Generation
        
        ## Context
        You are helping to generate a database query for a restaurant recommendation system.
        The user is looking for food recommendations based on their query.
        
        ## Database Schema
        {schema_info}
        
        ## User Information
        User ID: {user_context.get('user_id', 'Unknown')}
        Previous Orders: {user_context.get('order_count', 0)} orders
        Favorite Cuisines: {user_context.get('favorite_cuisines', [])}
        
        ## User Query
        "{user_query}"
        
        ## Your Task
        Analyze the user query and generate a database query command that will retrieve relevant information.
        Choose from one of these query types:
        1. restaurant_search - Search for restaurants by name, cuisine, or location
        2. menu_search - Search for specific menu items
        3. popular_cuisines - Get the most popular cuisines
        4. price_range - Find items within a specific price range
        5. user_favorite_cuisines - Get the user's favorite cuisines
        6. user_favorite_items - Get the user's favorite menu items
        
        ## Response Format
        Respond with a single JSON object containing:
        1. query_type: One of the query types listed above
        2. search_term: The search term to use (if applicable)
        3. min_price and max_price: For price range queries
        4. explanation: A brief explanation of why you chose this query
        
        Format your response as a valid JSON object only, with no additional text.
        """
        
        try:
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a database query generator for a restaurant recommendation system."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                response_format={"type": "json_object"}
            )
            
            query_instruction = response.choices[0].message.content.strip()
            return query_instruction
            
        except Exception as e:
            print(f"Error generating database query: {str(e)}")
            return json.dumps({"query_type": "schema_info", "explanation": "Failed to generate query"})
    
    def execute_db_query(self, query_instruction: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute a database query based on the LLM-generated query instruction.
        """
        try:
            # Parse the query instruction
            query_data = json.loads(query_instruction)
            query_type = query_data.get('query_type', '')
            
            # Execute the appropriate query based on the type
            if query_type == 'restaurant_search' and 'search_term' in query_data:
                return self.db_access.search_restaurants(query_data['search_term'])
            
            elif query_type == 'menu_search' and 'search_term' in query_data:
                return self.db_access.search_menu_items(query_data['search_term'])
            
            elif query_type == 'popular_cuisines':
                return self.db_access.get_popular_cuisines()
            
            elif query_type == 'price_range' and 'min_price' in query_data and 'max_price' in query_data:
                return self.db_access.get_price_range_items(
                    float(query_data['min_price']), 
                    float(query_data['max_price'])
                )
            
            elif query_type == 'user_favorite_cuisines' and user_id:
                return self.db_access.get_user_favorite_cuisines(user_id)
            
            elif query_type == 'user_favorite_items' and user_id:
                return self.db_access.get_user_favorite_items(user_id)
            
            else:
                return self.db_access.get_schema_info()
                
        except json.JSONDecodeError:
            return {"error": "Invalid query instruction format"}
        except Exception as e:
            return {"error": str(e)}
    
    def generate_recommendations(self, user_query: str, user_context: Dict[str, Any]) -> str:
        """
        Generate food recommendations based on database queries and LLM analysis.
        """
        # Step 1: Generate a database query based on the user's query
        query_instruction = self.generate_db_query(user_query, user_context)
        
        # Step 2: Execute the database query
        db_results = self.execute_db_query(query_instruction, user_context.get('user_id'))
        
        # Step 3: Generate recommendations based on the database results
        prompt = f"""
        # Restaurant Recommendation Generation
        
        ## Context
        You are providing personalized restaurant and food recommendations based on the user's query and database results.
        
        ## User Information
        User ID: {user_context.get('user_id', 'Unknown')}
        Previous Orders: {user_context.get('order_count', 0)} orders
        Favorite Cuisines: {user_context.get('favorite_cuisines', [])}
        
        ## User Query
        "{user_query}"
        
        ## Database Results
        {json.dumps(db_results, indent=2)}
        
        ## Your Task
        Generate personalized restaurant or food recommendations based on the database results and user context.
        Make your recommendations specific, mentioning actual restaurant names and menu items from the database results.
        If the database results don't contain enough information, suggest general recommendations based on the user's favorites.
        
        ## Response Format
        Provide a conversational response that includes:
        1. 2-3 specific recommendations with restaurant names and menu items when available
        2. Brief explanations for why you're recommending each option
        3. A follow-up question to refine the recommendations further
        
        Keep your response concise and focused on the recommendations.
        """
        
        try:
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a restaurant recommendation expert providing personalized food suggestions."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
            )
            
            recommendations = response.choices[0].message.content.strip()
            return recommendations
            
        except Exception as e:
            print(f"Error generating recommendations: {str(e)}")
            return "I'm sorry, I couldn't generate recommendations at this time. Please try again later."


# Example usage
if __name__ == "__main__":
    integration = LLMDatabaseIntegration()
    
    # Example user context
    user_context = {
        "user_id": "sample_user_123",
        "order_count": 5,
        "favorite_cuisines": ["Italian", "Japanese"]
    }
    
    # Example query
    user_query = "I'm in the mood for something spicy under $15"
    
    # Generate recommendations
    recommendations = integration.generate_recommendations(user_query, user_context)
    print(recommendations)

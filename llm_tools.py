#!/usr/bin/env python3
"""
LLM Function Calling (Tools) for Database Access

This module implements function calling (tools) for the LLM to interact with the food database
in a structured and secure way.
"""

import os
import json
import sqlite3
from typing import Dict, List, Any, Optional, Union
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq client
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY environment variable not set")

groq_client = Groq(api_key=GROQ_API_KEY)

class DatabaseTools:
    """
    Provides database access functions that can be called by the LLM as tools.
    """
    
    def __init__(self, db_path: str = 'uber_eats.db'):
        """Initialize the database tools."""
        self.db_path = db_path
    
    def connect(self):
        """Connect to the database and return connection and cursor."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        return conn, cursor
    
    def close(self, conn):
        """Close the database connection."""
        if conn:
            conn.close()
    
    def search_restaurants(self, search_term: str, cuisine_type: Optional[str] = None, 
                          limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for restaurants by name, cuisine, or borough.
        
        Args:
            search_term: The search term to look for in restaurant names
            cuisine_type: Optional filter for specific cuisine type
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            List of restaurant dictionaries
        """
        conn, cursor = self.connect()
        try:
            query = """
            SELECT restaurant_id, name, cuisine, borough 
            FROM restaurants 
            WHERE name LIKE ?
            """
            params = [f"%{search_term}%"]
            
            if cuisine_type:
                query += " AND cuisine LIKE ?"
                params.append(f"%{cuisine_type}%")
                
            query += f" LIMIT {min(limit, 20)}"  # Cap at 20 for safety
            
            cursor.execute(query, params)
            
            # Convert rows to dictionaries
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            return {"error": str(e)}
        finally:
            self.close(conn)
    
    def get_restaurant_menu(self, restaurant_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get menu items for a specific restaurant.
        
        Args:
            restaurant_id: The ID of the restaurant
            limit: Maximum number of menu items to return (default: 10)
            
        Returns:
            List of menu item dictionaries
        """
        conn, cursor = self.connect()
        try:
            query = """
            SELECT item_id, name, section, description, price
            FROM menu_items
            WHERE restaurant_id = ?
            LIMIT ?
            """
            
            cursor.execute(query, (restaurant_id, min(limit, 50)))  # Cap at 50 for safety
            
            # Convert rows to dictionaries
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            return {"error": str(e)}
        finally:
            self.close(conn)
    
    def search_menu_items(self, search_term: str, max_price: Optional[float] = None,
                         section: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for menu items across all restaurants.
        
        Args:
            search_term: The search term to look for in menu item names or descriptions
            max_price: Optional maximum price filter
            section: Optional menu section filter (e.g., "Appetizers", "Entrees")
            limit: Maximum number of results to return (default: 10)
            
        Returns:
            List of menu item dictionaries with restaurant information
        """
        conn, cursor = self.connect()
        try:
            query = """
            SELECT mi.item_id, mi.name, mi.description, mi.price, mi.section, 
                   r.name as restaurant_name, r.restaurant_id
            FROM menu_items mi
            JOIN restaurants r ON mi.restaurant_id = r.restaurant_id
            WHERE (mi.name LIKE ? OR mi.description LIKE ?)
            """
            params = [f"%{search_term}%", f"%{search_term}%"]
            
            if max_price is not None:
                query += " AND mi.price <= ?"
                params.append(max_price)
                
            if section:
                query += " AND mi.section LIKE ?"
                params.append(f"%{section}%")
                
            query += f" LIMIT {min(limit, 30)}"  # Cap at 30 for safety
            
            cursor.execute(query, params)
            
            # Convert rows to dictionaries
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            return {"error": str(e)}
        finally:
            self.close(conn)
    
    def get_popular_cuisines(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most popular cuisines based on restaurant count.
        
        Args:
            limit: Maximum number of cuisines to return (default: 10)
            
        Returns:
            List of cuisine dictionaries with counts
        """
        conn, cursor = self.connect()
        try:
            query = """
            SELECT cuisine, COUNT(*) as count
            FROM restaurants
            WHERE cuisine IS NOT NULL AND cuisine != ''
            GROUP BY cuisine
            ORDER BY count DESC
            LIMIT ?
            """
            
            cursor.execute(query, (min(limit, 20),))  # Cap at 20 for safety
            
            # Convert rows to dictionaries
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            return {"error": str(e)}
        finally:
            self.close(conn)
    
    def get_user_order_history(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get a user's order history.
        
        Args:
            user_id: The ID of the user
            limit: Maximum number of orders to return (default: 5)
            
        Returns:
            List of order dictionaries with restaurant information
        """
        conn, cursor = self.connect()
        try:
            query = """
            SELECT o.order_id, o.items, o.created_at,
                   r.name as restaurant_name, r.cuisine
            FROM orders o
            JOIN restaurants r ON o.restaurant_id = r.restaurant_id
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC
            LIMIT ?
            """
            
            cursor.execute(query, (user_id, min(limit, 20)))  # Cap at 20 for safety
            
            # Convert rows to dictionaries
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                row_dict = dict(zip(columns, row))
                
                # Parse items JSON if it's stored as a string
                if isinstance(row_dict.get('items'), str):
                    try:
                        row_dict['items'] = json.loads(row_dict['items'])
                    except json.JSONDecodeError:
                        pass
                
                results.append(row_dict)
            
            return results
        except Exception as e:
            return {"error": str(e)}
        finally:
            self.close(conn)
    
    def get_user_favorite_cuisines(self, user_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get a user's favorite cuisines based on order history.
        
        Args:
            user_id: The ID of the user
            limit: Maximum number of cuisines to return (default: 3)
            
        Returns:
            List of cuisine dictionaries with counts
        """
        conn, cursor = self.connect()
        try:
            query = """
            SELECT r.cuisine, COUNT(*) as count
            FROM orders o
            JOIN restaurants r ON o.restaurant_id = r.restaurant_id
            WHERE o.user_id = ? AND r.cuisine IS NOT NULL AND r.cuisine != ''
            GROUP BY r.cuisine
            ORDER BY count DESC
            LIMIT ?
            """
            
            cursor.execute(query, (user_id, min(limit, 10)))  # Cap at 10 for safety
            
            # Convert rows to dictionaries
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            return {"error": str(e)}
        finally:
            self.close(conn)
    
    def get_similar_restaurants(self, restaurant_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get restaurants similar to the specified restaurant (same cuisine).
        
        Args:
            restaurant_id: The ID of the reference restaurant
            limit: Maximum number of similar restaurants to return (default: 3)
            
        Returns:
            List of similar restaurant dictionaries
        """
        conn, cursor = self.connect()
        try:
            # First get the cuisine of the reference restaurant
            cursor.execute(
                "SELECT cuisine FROM restaurants WHERE restaurant_id = ?", 
                (restaurant_id,)
            )
            result = cursor.fetchone()
            
            if not result:
                return []
                
            cuisine = result['cuisine']
            
            # Find similar restaurants with the same cuisine
            query = """
            SELECT restaurant_id, name, cuisine, borough
            FROM restaurants
            WHERE cuisine = ? AND restaurant_id != ?
            LIMIT ?
            """
            
            cursor.execute(query, (cuisine, restaurant_id, min(limit, 10)))
            
            # Convert rows to dictionaries
            columns = [col[0] for col in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            
            return results
        except Exception as e:
            return {"error": str(e)}
        finally:
            self.close(conn)


class LLMToolsIntegration:
    """
    Integrates the LLM with database tools using function calling.
    """
    
    def __init__(self, db_path: str = 'uber_eats.db'):
        """Initialize the LLM tools integration."""
        self.db_tools = DatabaseTools(db_path)
        self.model = "meta-llama/llama-4-scout-17b-16e-instruct"
        
        # Define the tools (functions) that the LLM can call
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "search_restaurants",
                    "description": "Search for restaurants by name, cuisine, or location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "The search term to look for in restaurant names"
                            },
                            "cuisine_type": {
                                "type": "string",
                                "description": "Optional filter for specific cuisine type"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 5)"
                            }
                        },
                        "required": ["search_term"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_restaurant_menu",
                    "description": "Get menu items for a specific restaurant",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "restaurant_id": {
                                "type": "string",
                                "description": "The ID of the restaurant"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of menu items to return (default: 10)"
                            }
                        },
                        "required": ["restaurant_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_menu_items",
                    "description": "Search for menu items across all restaurants",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "The search term to look for in menu item names or descriptions"
                            },
                            "max_price": {
                                "type": "number",
                                "description": "Optional maximum price filter"
                            },
                            "section": {
                                "type": "string",
                                "description": "Optional menu section filter (e.g., 'Appetizers', 'Entrees')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 10)"
                            }
                        },
                        "required": ["search_term"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_popular_cuisines",
                    "description": "Get the most popular cuisines based on restaurant count",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of cuisines to return (default: 10)"
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_user_order_history",
                    "description": "Get a user's order history",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "The ID of the user"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of orders to return (default: 5)"
                            }
                        },
                        "required": ["user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_user_favorite_cuisines",
                    "description": "Get a user's favorite cuisines based on order history",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "user_id": {
                                "type": "string",
                                "description": "The ID of the user"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of cuisines to return (default: 3)"
                            }
                        },
                        "required": ["user_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_similar_restaurants",
                    "description": "Get restaurants similar to the specified restaurant (same cuisine)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "restaurant_id": {
                                "type": "string",
                                "description": "The ID of the reference restaurant"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of similar restaurants to return (default: 3)"
                            }
                        },
                        "required": ["restaurant_id"]
                    }
                }
            }
        ]
    
    def execute_tool_call(self, tool_call):
        """
        Execute a tool call from the LLM.
        
        Args:
            tool_call: The tool call object from the LLM
            
        Returns:
            The result of the tool call
        """
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        
        # Execute the appropriate function based on the name
        if function_name == "search_restaurants":
            return self.db_tools.search_restaurants(**function_args)
        elif function_name == "get_restaurant_menu":
            return self.db_tools.get_restaurant_menu(**function_args)
        elif function_name == "search_menu_items":
            return self.db_tools.search_menu_items(**function_args)
        elif function_name == "get_popular_cuisines":
            return self.db_tools.get_popular_cuisines(**function_args)
        elif function_name == "get_user_order_history":
            return self.db_tools.get_user_order_history(**function_args)
        elif function_name == "get_user_favorite_cuisines":
            return self.db_tools.get_user_favorite_cuisines(**function_args)
        elif function_name == "get_similar_restaurants":
            return self.db_tools.get_similar_restaurants(**function_args)
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    def generate_recommendations(self, user_query: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate food recommendations based on user query and context.
        Uses function calling to interact with the database.
        
        Args:
            user_query: The user's natural language query
            user_context: Dictionary containing user context (user_id, etc.)
            
        Returns:
            Recommendation data in JSON format
        """
        # Create the initial prompt
        system_prompt = """
        You are a restaurant recommendation expert providing personalized food suggestions.
        Use the available tools to query the database for restaurants and menu items.
        Make your recommendations specific, mentioning actual restaurant names and menu items.
        """
        
        user_prompt = f"""
        I need restaurant or food recommendations based on the following request:
        
        "{user_query}"
        
        User information:
        - User ID: {user_context.get('user_id', 'Unknown')}
        - Previous orders: {user_context.get('order_count', 0)}
        
        Please use the available tools to find relevant information in the database,
        then provide 2-3 specific recommendations with restaurant names and menu items.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        # First LLM call to get tool calls
        try:
            response = groq_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            # Check if the LLM wants to call tools
            if assistant_message.tool_calls:
                # Execute each tool call and collect results
                tool_results = []
                for tool_call in assistant_message.tool_calls:
                    result = self.execute_tool_call(tool_call)
                    tool_results.append({
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "result": json.dumps(result)
                    })
                
                # Add the assistant's message and tool results to the conversation
                messages.append(assistant_message)
                for result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": result["tool_call_id"],
                        "name": result["name"],
                        "content": result["result"]
                    })
                
                # Create a prompt for structured JSON output
                json_prompt = f"""
                Based on the database information you've gathered, please provide restaurant recommendations 
                in the following JSON format:
                
                ```json
                {{
                  "text": "A conversational response with your recommendations (this will be shown to the user)",
                  "recommendations": [
                    {{
                      "restaurant_name": "Name of restaurant 1",
                      "cuisine": "Cuisine type",
                      "recommended_items": ["Item 1", "Item 2"],
                      "reason": "Brief reason for this recommendation"
                    }},
                    {{...more recommendations...}}
                  ],
                  "follow_up_question": "A question to refine recommendations further"
                }}
                
                Include 2-3 specific recommendations in the recommendations array.
                Make sure your response is valid JSON.
                """
                
                # Add the JSON format request
                messages.append({"role": "user", "content": json_prompt})
                
                # Second LLM call to generate structured JSON recommendations
                final_response = groq_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"}
                )
                
                # Parse the JSON response
                try:
                    recommendations_json = final_response.choices[0].message.content.strip()
                    recommendations_data = json.loads(recommendations_json)
                    return recommendations_data
                except json.JSONDecodeError as e:
                    print(f"Error parsing JSON response: {str(e)}")
                    # Fallback response if JSON parsing fails
                    return {
                        "text": final_response.choices[0].message.content.strip(),
                        "recommendations": [],
                        "follow_up_question": "Would you like more specific recommendations?"
                    }
            else:
                # If no tool calls were made, create a basic response
                return {
                    "text": assistant_message.content,
                    "recommendations": [],
                    "follow_up_question": "Can you provide more details about what you're looking for?"
                }
                
        except Exception as e:
            print(f"Error generating recommendations: {str(e)}")
            return {
                "text": "I'm sorry, I couldn't generate recommendations at this time. Please try again later.",
                "recommendations": [],
                "follow_up_question": "Would you like to try a different type of cuisine?"
            }


# Example usage
if __name__ == "__main__":
    integration = LLMToolsIntegration()
    
    # Example user context
    user_context = {
        "user_id": "sample_user_123",
        "order_count": 5
    }
    
    # Example query
    user_query = "I'm in the mood for something spicy under $15"
    
    # Generate recommendations
    recommendations = integration.generate_recommendations(user_query, user_context)
    print(recommendations)

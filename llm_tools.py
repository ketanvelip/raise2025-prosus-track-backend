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
    
    def get_restaurant_ingredients(self, restaurant_id: str) -> List[Dict[str, Any]]:
        """
        Get ingredients available at a specific restaurant.
        
        Args:
            restaurant_id: The ID of the restaurant
            
        Returns:
            List of ingredient dictionaries
        """
        conn, cursor = self.connect()
        try:
            query = """
            SELECT i.ingredient_id, i.name, i.category
            FROM ingredients i
            JOIN restaurant_ingredients ri ON i.ingredient_id = ri.ingredient_id
            WHERE ri.restaurant_id = ?
            ORDER BY i.category, i.name
            """
            
            cursor.execute(query, (restaurant_id,))
            
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
    
    def search_by_ingredients(self, ingredients: List[str], match_all: bool = False, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for restaurants that have specific ingredients available.
        
        Args:
            ingredients: List of ingredient names to search for
            match_all: If True, restaurants must have ALL ingredients; if False, ANY ingredient
            limit: Maximum number of results to return (default: 5)
            
        Returns:
            List of restaurant dictionaries with ingredient match counts
        """
        if not ingredients:
            return []
        
        conn, cursor = self.connect()
        try:
            # Convert ingredient names to placeholders for the query
            placeholders = ', '.join(['?'] * len(ingredients))
            
            # Different query based on match_all or match_any
            if match_all:
                # Must match all ingredients (count must equal the number of ingredients)
                query = f"""
                SELECT r.restaurant_id, r.name, r.cuisine, r.borough, COUNT(DISTINCT i.ingredient_id) as match_count
                FROM restaurants r
                JOIN restaurant_ingredients ri ON r.restaurant_id = ri.restaurant_id
                JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
                WHERE i.name IN ({placeholders})
                GROUP BY r.restaurant_id
                HAVING match_count = ?
                ORDER BY match_count DESC
                LIMIT ?
                """
                params = ingredients + [len(ingredients), min(limit, 20)]
            else:
                # Match any of the ingredients
                query = f"""
                SELECT r.restaurant_id, r.name, r.cuisine, r.borough, COUNT(DISTINCT i.ingredient_id) as match_count
                FROM restaurants r
                JOIN restaurant_ingredients ri ON r.restaurant_id = ri.restaurant_id
                JOIN ingredients i ON ri.ingredient_id = i.ingredient_id
                WHERE i.name IN ({placeholders})
                GROUP BY r.restaurant_id
                ORDER BY match_count DESC
                LIMIT ?
                """
                params = ingredients + [min(limit, 20)]
            
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
    
    def get_popular_ingredients(self, category: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most popular ingredients based on restaurant usage.
        
        Args:
            category: Optional filter for ingredient category
            limit: Maximum number of ingredients to return (default: 10)
            
        Returns:
            List of ingredient dictionaries with counts
        """
        conn, cursor = self.connect()
        try:
            query = """
            SELECT i.ingredient_id, i.name, i.category, COUNT(ri.restaurant_id) as restaurant_count
            FROM ingredients i
            JOIN restaurant_ingredients ri ON i.ingredient_id = ri.ingredient_id
            """
            
            params = []
            if category:
                query += " WHERE i.category = ? "
                params.append(category)
                
            query += """
            GROUP BY i.ingredient_id
            ORDER BY restaurant_count DESC
            LIMIT ?
            """
            
            params.append(min(limit, 30))  # Cap at 30 for safety
            
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
            
    def get_ingredients_by_category(self, restaurant_id: str) -> Dict[str, List[str]]:
        """
        Get ingredients available at a specific restaurant, organized by category.
        This is useful for custom food recommendations.
        
        Args:
            restaurant_id: The ID of the restaurant
            
        Returns:
            Dictionary with categories as keys and lists of ingredient names as values
        """
        conn, cursor = self.connect()
        try:
            query = """
            SELECT i.name, i.category
            FROM ingredients i
            JOIN restaurant_ingredients ri ON i.ingredient_id = ri.ingredient_id
            WHERE ri.restaurant_id = ?
            ORDER BY i.category, i.name
            """
            
            cursor.execute(query, (restaurant_id,))
            
            # Organize ingredients by category
            categorized = {
                "protein": [],
                "vegetable": [],
                "grain": [],
                "dairy": [],
                "spice_herb": [],
                "fruit": [],
                "other": []
            }
            
            for row in cursor.fetchall():
                name, category = row
                if category in categorized:
                    categorized[category].append(name)
                else:
                    categorized["other"].append(name)
            
            # Remove empty categories
            return {k: v for k, v in categorized.items() if v}
            
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
        self.model = "meta-llama/llama-4-maverick-17b-128e-instruct"
        
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
                    "name": "search_by_ingredients",
                    "description": "Search for restaurants that have specific ingredients available",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "ingredients": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of ingredient names to search for"
                            },
                            "match_all": {
                                "type": "boolean",
                                "description": "If true, restaurants must have ALL ingredients; if false, ANY ingredient (default: false)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 5)"
                            }
                        },
                        "required": ["ingredients"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_restaurant_ingredients",
                    "description": "Get ingredients available at a specific restaurant",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "restaurant_id": {
                                "type": "string",
                                "description": "The ID of the restaurant"
                            }
                        },
                        "required": ["restaurant_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_popular_ingredients",
                    "description": "Get the most popular ingredients based on restaurant usage",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Optional filter for ingredient category (protein, vegetable, grain, dairy, spice_herb, fruit, other)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of ingredients to return (default: 10)"
                            }
                        }
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
        # New ingredient-related functions
        elif function_name == "search_by_ingredients":
            return self.db_tools.search_by_ingredients(**function_args)
        elif function_name == "get_restaurant_ingredients":
            return self.db_tools.get_restaurant_ingredients(**function_args)
        elif function_name == "get_popular_ingredients":
            return self.db_tools.get_popular_ingredients(**function_args)
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
        IMPORTANT: You must ONLY recommend actual restaurants that exist in the database.
        DO NOT invent or create fictional restaurant names - use ONLY the exact restaurant
        names returned by the database queries.
        Make your recommendations specific, mentioning actual restaurant names and menu items
        that were returned in the database query results.
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
                tool_choice="auto",
                temperature=0.2
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
                
                EXTREMELY IMPORTANT:
                1. You must ONLY use restaurant names that actually exist in the database results
                2. The "restaurant_name" field must contain the EXACT name of a restaurant from your database query results
                3. DO NOT invent or create fictional restaurant names - use ONLY names that were returned by your tool calls
                4. If you're not sure if a restaurant exists in the database, call the search_restaurants tool to verify
                5. Include 2-3 specific recommendations in the recommendations array
                
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


    def generate_custom_food(self, restaurant_id: str, preferences: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate food recommendations including both on-menu items and custom off-menu dishes
        that can be prepared with the restaurant's available ingredients.
        
        Args:
            restaurant_id: The ID of the restaurant
            preferences: Optional dictionary of user preferences (dietary restrictions, etc.)
            
        Returns:
            Dictionary with on-menu and off-menu food recommendations
        """
        # Get restaurant details
        conn, cursor = self.db_tools.connect()
        try:
            query = "SELECT restaurant_id, name, cuisine FROM restaurants WHERE restaurant_id = ?"
            cursor.execute(query, (restaurant_id,))
            result = cursor.fetchone()
            
            if result:
                restaurant = {
                    "restaurant_id": result[0],
                    "name": result[1],
                    "cuisine": result[2]
                }
            else:
                return {
                    "error": "Restaurant not found",
                    "menu_items": [],
                    "custom_foods": []
                }
        except Exception as e:
            return {
                "error": f"Failed to get restaurant details: {str(e)}",
                "menu_items": [],
                "custom_foods": []
            }
        finally:
            self.db_tools.close(conn)
            
        restaurant_name = restaurant.get("name", "Unknown Restaurant")
        cuisine = restaurant.get("cuisine", "Unknown Cuisine")
        
        # Get menu items for the restaurant
        menu_items = self.db_tools.get_restaurant_menu(restaurant_id, limit=20)
        if isinstance(menu_items, dict) and "error" in menu_items:
            menu_items = []
        
        # Get ingredients by category
        ingredients_by_category = self.db_tools.get_ingredients_by_category(restaurant_id)
        if isinstance(ingredients_by_category, dict) and "error" in ingredients_by_category:
            return {
                "error": "Failed to get ingredients",
                "menu_items": [],
                "custom_foods": []
            }
        
        # Create the prompt
        system_prompt = """
        You are a culinary expert specializing in food recommendations and creative dish ideas.
        Your task is to provide both on-menu recommendations and suggest unique off-menu dishes 
        that can be prepared with the restaurant's available ingredients.
        """
        
        user_prompt = f"""
        I need food recommendations for a restaurant called "{restaurant_name}" 
        which specializes in {cuisine} cuisine.
        
        The restaurant has the following menu items:
        {json.dumps([{"name": item.get("name"), "description": item.get("description"), "section": item.get("section"), "price": item.get("price")} for item in menu_items], indent=2)}
        
        The restaurant also has the following ingredients available, organized by category:
        {json.dumps(ingredients_by_category, indent=2)}
        
        User preferences: {json.dumps(preferences) if preferences else 'No specific preferences'}
        
        Please provide:
        
        1. THREE (3) recommended items from the existing menu. For each item, include:
           - The exact name from the menu
           - A brief reason why you're recommending it
           - Any suggested modifications or pairings
        
        2. TWO (2) creative off-menu dishes that could be prepared with the available ingredients. For each dish, include:
           - A creative name
           - A brief description
           - Main ingredients required
           - Simple preparation instructions
           - Estimated cooking time
        
        Format your response as a JSON object with 'menu_items' and 'custom_foods' arrays.
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = groq_client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.7  # Higher temperature for more creativity
            )
            
            # Parse the JSON response
            try:
                recommendations_json = response.choices[0].message.content.strip()
                recommendations_data = json.loads(recommendations_json)
                
                # Add restaurant information
                result = {
                    "restaurant_id": restaurant_id,
                    "restaurant_name": restaurant_name,
                    "cuisine": cuisine,
                    "menu_items": recommendations_data.get("menu_items", []),
                    "custom_foods": recommendations_data.get("custom_foods", [])
                }
                
                return result
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {str(e)}")
                # Fallback response
                return {
                    "restaurant_id": restaurant_id,
                    "restaurant_name": restaurant_name,
                    "cuisine": cuisine,
                    "menu_items": [],
                    "custom_foods": [],
                    "error": "Failed to parse food recommendations"
                }
        except Exception as e:
            print(f"Error generating food recommendations: {str(e)}")
            return {
                "restaurant_id": restaurant_id,
                "restaurant_name": restaurant_name,
                "cuisine": cuisine,
                "menu_items": [],
                "custom_foods": [],
                "error": f"Failed to generate food recommendations: {str(e)}"
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

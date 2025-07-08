#!/usr/bin/env python3
"""
LLM Database Access Layer

This module provides a secure way for the LLM to query the food database
while preventing SQL injection and other security issues.
"""

import sqlite3
import json
import re
from typing import Dict, List, Any, Optional, Union

class LLMDatabaseAccess:
    """
    Provides a secure interface for LLM to query the restaurant database.
    Implements safety measures to prevent SQL injection and other security issues.
    """
    
    def __init__(self, db_path: str = 'uber_eats.db'):
        """Initialize the database access layer."""
        self.db_path = db_path
        self.allowed_tables = ['restaurants', 'menu_items', 'users', 'orders', 'food_preferences', 'user_notes']
        self.allowed_operations = ['SELECT']
        
        # Define schema for reference
        self.schema = {
            'restaurants': [
                'id', 'restaurant_id', 'name', 'borough', 'cuisine', 
                'street', 'zipcode', 'created_at'
            ],
            'menu_items': [
                'id', 'item_id', 'restaurant_id', 'name', 'section',
                'description', 'price', 'image', 'created_at'
            ],
            'users': [
                'id', 'user_id', 'username', 'email', 'preferences', 'created_at'
            ],
            'orders': [
                'id', 'order_id', 'user_id', 'restaurant_id', 'items', 
                'status', 'created_at'
            ],
            'food_preferences': [
                'id', 'user_id', 'cuisine', 'food_item', 'rating', 'created_at'
            ],
            'user_notes': [
                'id', 'user_id', 'note_text', 'note_type', 'created_at'
            ]
        }
    
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
    
    def is_safe_query(self, query: str) -> bool:
        """
        Check if a query is safe to execute.
        This is a basic implementation and should be enhanced for production use.
        """
        # Convert to uppercase for easier checking
        query_upper = query.upper()
        
        # Check if query only contains allowed operations
        if not any(op in query_upper for op in self.allowed_operations):
            return False
        
        # Check if query only accesses allowed tables
        for table in self.allowed_tables:
            if table.upper() in query_upper:
                return True
        
        return False
    
    def execute_safe_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute a query safely and return results as a list of dictionaries.
        Uses parameterized queries to prevent SQL injection.
        """
        if not self.is_safe_query(query):
            return {"error": "Query not allowed for security reasons"}
        
        conn, cursor = self.connect()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
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
    
    def get_schema_info(self) -> Dict[str, List[str]]:
        """Return the database schema information."""
        return self.schema
    
    def search_restaurants(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for restaurants by name, cuisine, or borough."""
        query = """
        SELECT restaurant_id, name, cuisine, borough 
        FROM restaurants 
        WHERE name LIKE ? OR cuisine LIKE ? OR borough LIKE ?
        LIMIT 10
        """
        search_pattern = f"%{search_term}%"
        return self.execute_safe_query(query, (search_pattern, search_pattern, search_pattern))
    
    def search_menu_items(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for menu items by name, description, or section."""
        query = """
        SELECT mi.item_id, mi.name, mi.description, mi.price, mi.section, 
               r.name as restaurant_name, r.restaurant_id
        FROM menu_items mi
        JOIN restaurants r ON mi.restaurant_id = r.restaurant_id
        WHERE mi.name LIKE ? OR mi.description LIKE ? OR mi.section LIKE ?
        LIMIT 20
        """
        search_pattern = f"%{search_term}%"
        return self.execute_safe_query(query, (search_pattern, search_pattern, search_pattern))
    
    def get_popular_cuisines(self) -> List[Dict[str, Any]]:
        """Get the most popular cuisines based on restaurant count."""
        query = """
        SELECT cuisine, COUNT(*) as count
        FROM restaurants
        WHERE cuisine IS NOT NULL AND cuisine != ''
        GROUP BY cuisine
        ORDER BY count DESC
        LIMIT 10
        """
        return self.execute_safe_query(query)
    
    def get_price_range_items(self, min_price: float, max_price: float) -> List[Dict[str, Any]]:
        """Get menu items within a specific price range."""
        query = """
        SELECT mi.item_id, mi.name, mi.price, r.name as restaurant_name
        FROM menu_items mi
        JOIN restaurants r ON mi.restaurant_id = r.restaurant_id
        WHERE mi.price >= ? AND mi.price <= ?
        LIMIT 20
        """
        return self.execute_safe_query(query, (min_price, max_price))
    
    def get_user_favorite_cuisines(self, user_id: str) -> List[Dict[str, Any]]:
        """Get a user's favorite cuisines based on order history."""
        query = """
        SELECT r.cuisine, COUNT(*) as count
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.restaurant_id
        WHERE o.user_id = ?
        GROUP BY r.cuisine
        ORDER BY count DESC
        LIMIT 5
        """
        return self.execute_safe_query(query, (user_id,))
    
    def get_user_favorite_items(self, user_id: str) -> List[Dict[str, Any]]:
        """Get a user's favorite menu items based on order history."""
        # This is a simplified implementation - in reality, we'd need to parse the items JSON
        query = """
        SELECT o.items, r.name as restaurant_name
        FROM orders o
        JOIN restaurants r ON o.restaurant_id = r.restaurant_id
        WHERE o.user_id = ?
        ORDER BY o.created_at DESC
        LIMIT 10
        """
        results = self.execute_safe_query(query, (user_id,))
        
        # Process the items JSON strings to extract item IDs
        processed_results = []
        for result in results:
            if isinstance(result.get('items'), str):
                try:
                    items = json.loads(result['items'])
                    result['items'] = items
                except json.JSONDecodeError:
                    pass
            processed_results.append(result)
        
        return processed_results
    
    def process_llm_query(self, query_text: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a natural language query from the LLM and return relevant data.
        This function analyzes the query and calls the appropriate specialized methods.
        """
        query_text = query_text.lower()
        
        # Check for different types of queries
        if "restaurant" in query_text and any(term in query_text for term in ["search", "find", "looking for"]):
            search_terms = re.findall(r'(?:search|find|looking for)\s+(\w+(?:\s+\w+)*)', query_text)
            if search_terms:
                return {"type": "restaurant_search", "results": self.search_restaurants(search_terms[0])}
        
        if "menu" in query_text and any(term in query_text for term in ["search", "find", "items"]):
            search_terms = re.findall(r'(?:search|find)\s+(\w+(?:\s+\w+)*)', query_text)
            if search_terms:
                return {"type": "menu_search", "results": self.search_menu_items(search_terms[0])}
        
        if "cuisine" in query_text and "popular" in query_text:
            return {"type": "popular_cuisines", "results": self.get_popular_cuisines()}
        
        if "price" in query_text and any(term in query_text for term in ["range", "between"]):
            price_ranges = re.findall(r'(\d+(?:\.\d+)?)\s*(?:to|and|between)\s*(\d+(?:\.\d+)?)', query_text)
            if price_ranges:
                min_price, max_price = float(price_ranges[0][0]), float(price_ranges[0][1])
                return {"type": "price_range", "results": self.get_price_range_items(min_price, max_price)}
        
        if user_id and "favorite" in query_text and "cuisine" in query_text:
            return {"type": "user_favorite_cuisines", "results": self.get_user_favorite_cuisines(user_id)}
        
        if user_id and "favorite" in query_text and any(term in query_text for term in ["item", "food", "dish"]):
            return {"type": "user_favorite_items", "results": self.get_user_favorite_items(user_id)}
        
        # If no specific query type is detected, return schema information
        return {
            "type": "schema_info", 
            "message": "I couldn't understand your specific query. Here's the database schema for reference:",
            "schema": self.get_schema_info()
        }


# Example usage
if __name__ == "__main__":
    db_access = LLMDatabaseAccess()
    
    # Example queries
    print("Schema Info:")
    print(json.dumps(db_access.get_schema_info(), indent=2))
    
    print("\nSearching for 'pizza' restaurants:")
    print(json.dumps(db_access.search_restaurants("pizza"), indent=2))
    
    print("\nPopular cuisines:")
    print(json.dumps(db_access.get_popular_cuisines(), indent=2))

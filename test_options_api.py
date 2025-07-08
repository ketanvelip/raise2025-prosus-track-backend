#!/usr/bin/env python3
"""
Test Script for the Food Options API Endpoint

This script demonstrates how to call the /generate_options endpoint
to get personalized food recommendations based on user input.
"""

import requests
import json
import sys

# Configuration
API_BASE_URL = "http://127.0.0.1:5005"
HEADERS = {"Content-Type": "application/json"}

def pretty_print_json(data):
    """Print JSON data in a readable format."""
    print(json.dumps(data, indent=2))
    print()

def test_generate_options():
    """Test the /generate_options endpoint with different queries."""
    test_queries = [
        "I'm looking for something spicy for dinner",
        "I want a healthy breakfast option",
        "I need a vegan dessert"
    ]
    
    for query in test_queries:
        print(f"\n{'=' * 50}")
        print(f"Testing with input: '{query}'")
        print('=' * 50)
        
        request_data = {
            "email": "user@example.com",
            "input_text": query
        }
        
        try:
            response = requests.post(
                f"{API_BASE_URL}/generate_options", 
                json=request_data, 
                headers=HEADERS
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("Food Options:")
                pretty_print_json(result)
                
                # Display in a more readable format
                if "options" in result:
                    for i, option in enumerate(result["options"]):
                        print(f"Option {i+1}:")
                        print(f"  Name: {option['item_name']}")
                        print(f"  Cuisine: {option['item_cuisine']}")
                        print(f"  Image URL: {option['item_img_url']}")
                        print()
            else:
                print(f"Error: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print(f"\n❌ ERROR: Could not connect to the API server.")
            print(f"   Make sure the server is running at: {API_BASE_URL}")
            print("   Try running 'python3 app.py' in another terminal.\n")
            sys.exit(1)
            
        except Exception as e:
            print(f"\n❌ ERROR: An unexpected error occurred: {str(e)}\n")
            sys.exit(1)
        
        print("\nPress Enter to try the next query, or Ctrl+C to exit...")
        input()

if __name__ == "__main__":
    print("Testing the Food Options API Endpoint")
    print("This will send multiple test queries to demonstrate the functionality.")
    print("Press Ctrl+C at any time to exit.\n")
    
    try:
        test_generate_options()
    except KeyboardInterrupt:
        print("\nTest stopped by user.")

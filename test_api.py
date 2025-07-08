#!/usr/bin/env python3
"""
End-to-End Test Script for Restaurant API
This script tests all major functionality of the Restaurant API:
- Creating a user
- Getting user details
- Placing an order 
- Retrieving user orders
- Getting AI-powered restaurant recommendations
"""

import requests
import json
import time
import sys
import random

# Configuration
API_BASE_URL = "http://127.0.0.1:5005"  # Updated to use the current port
HEADERS = {"Content-Type": "application/json"}

def print_separator(title):
    """Print a separator with a title for better readability."""
    print("\n" + "=" * 50)
    print(f" {title} ".center(50, "="))
    print("=" * 50 + "\n")

def pretty_print_json(data):
    """Print JSON data in a readable format."""
    print(json.dumps(data, indent=2))
    print()

def test_create_user():
    """Test creating a new user and return the created user's ID."""
    print_separator("CREATING NEW USER")
    
    # Generate a unique username to avoid conflicts
    timestamp = int(time.time())
    user_data = {
        "username": f"testuser_{timestamp}",
        "email": f"test_{timestamp}@example.com"
    }
    
    print(f"Creating user with data:")
    pretty_print_json(user_data)
    
    response = requests.post(f"{API_BASE_URL}/users", json=user_data, headers=HEADERS)
    
    if response.status_code == 201:
        user = response.json()
        print("User created successfully:")
        pretty_print_json(user)
        return user["user_id"]
    else:
        print(f"Error creating user: {response.status_code}")
        print(response.text)
        sys.exit(1)

def test_get_user(user_id):
    """Test getting details for a specific user."""
    print_separator("GETTING USER DETAILS")
    
    print(f"Fetching details for user_id: {user_id}")
    
    response = requests.get(f"{API_BASE_URL}/users/{user_id}")
    
    if response.status_code == 200:
        user = response.json()
        print("User details retrieved successfully:")
        pretty_print_json(user)
    else:
        print(f"Error getting user: {response.status_code}")
        print(response.text)
        sys.exit(1)

def test_get_restaurants():
    """Test retrieving the list of restaurants and return a random restaurant ID and its menu items."""
    print_separator("RETRIEVING RESTAURANTS")
    
    print("Fetching the list of restaurants...")
    
    # The API now returns paginated results
    response = requests.get(f"{API_BASE_URL}/restaurants")
    
    if response.status_code == 200:
        response_data = response.json()
        
        # Check if the response has the new paginated structure
        if isinstance(response_data, dict) and 'restaurants' in response_data:
            restaurants = response_data['restaurants']
            pagination = response_data.get('pagination', {})
            total_restaurants = pagination.get('total', len(restaurants))
            print(f"Successfully retrieved {len(restaurants)} restaurants (page 1 of {pagination.get('pages', 1)}).")
            print(f"Total restaurants in database: {total_restaurants}")
        else:
            # Fallback for old API format
            restaurants = response_data
            print(f"Successfully retrieved {len(restaurants)} restaurants.")
        
        # Select a random restaurant
        if not restaurants:
            print("No restaurants found in the database.")
            sys.exit(1)
            
        restaurant = random.choice(restaurants)
        print(f"\nRandomly selected restaurant for ordering:")
        print(f"Name: {restaurant['name']}")
        print(f"ID: {restaurant['restaurant_id']}")
        
        # Get the restaurant's menu
        menu_response = requests.get(f"{API_BASE_URL}/restaurants/{restaurant['restaurant_id']}/menu")
        
        if menu_response.status_code == 200:
            menu = menu_response.json()
            print(f"Menu items: {len(menu)}")
            
            # Select random menu items for the order
            if not menu:
                print("No menu items found for this restaurant.")
                return None, []
            
            # Select 1-3 random menu items
            num_items = random.randint(1, min(3, len(menu)))
            selected_items = random.sample(menu, num_items)
            
            print("\nSelected menu items for the order:")
            for item in selected_items:
                print(f"- {item.get('name', 'Unknown')} (ID: {item.get('_id', 'Unknown')})")
            
            return restaurant['restaurant_id'], [item.get('_id') for item in selected_items]
        else:
            print(f"Failed to retrieve menu. Status code: {menu_response.status_code}")
            print(f"Response: {menu_response.text}")
            return None, []
    else:
        print(f"Failed to retrieve restaurants. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return None, []

def test_place_order(user_id, restaurant_id, items):
    """Test placing an order and return the created order ID."""
    print_separator("PLACING AN ORDER")
    
    order_data = {
        "user_id": user_id,
        "restaurant_id": restaurant_id,
        "items": items
    }
    
    print("Creating order with data:")
    print(json.dumps(order_data, indent=2))
    
    response = requests.post(f"{API_BASE_URL}/orders", json=order_data)
    
    # Accept both 200 and 201 status codes (201 is the correct code for resource creation)
    if response.status_code in [200, 201]:
        order = response.json()
        print("\nOrder created successfully:")
        print(json.dumps(order, indent=2))
        return order["order_id"]
    else:
        print(f"\nFailed to create order. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        sys.exit(1)

def test_get_user_orders(user_id):
    """Test retrieving all orders for a user."""
    print_separator("RETRIEVING USER'S ORDERS")
    
    print(f"Fetching orders for user_id: {user_id}")
    
    response = requests.get(f"{API_BASE_URL}/users/{user_id}/orders")
    
    if response.status_code == 200:
        orders = response.json()
        print(f"Successfully retrieved {len(orders)} orders:")
        pretty_print_json(orders)
    else:
        print(f"Error getting user orders: {response.status_code}")
        print(response.text)
        sys.exit(1)

def test_get_recommendations(user_id):
    """Test getting restaurant recommendations based on order history."""
    print_separator("GETTING RESTAURANT RECOMMENDATIONS")
    
    print(f"Getting recommendations for user_id: {user_id}")
    print("This may take a few seconds as it calls the LLM API...")
    
    # Use the new recommendations endpoint
    response = requests.get(f"{API_BASE_URL}/recommendations?user_id={user_id}")
    
    if response.status_code == 200:
        recommendations = response.json()
        print("Recommendations received successfully:")
        print(json.dumps(recommendations, indent=2))
        return recommendations
    else:
        print(f"Failed to get recommendations. Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return None

def test_get_order(order_id):
    """Test retrieving a specific order by ID."""
    print_separator("RETRIEVING ORDER DETAILS")
    
    print(f"Fetching details for order_id: {order_id}")
    
    response = requests.get(f"{API_BASE_URL}/orders/{order_id}")
    
    if response.status_code == 200:
        order = response.json()
        print("Order details retrieved successfully:")
        pretty_print_json(order)
    else:
        print(f"Error getting order: {response.status_code}")
        print(response.text)
        sys.exit(1)

def run_end_to_end_test():
    """Run a complete end-to-end test of the API."""
    try:
        print("Starting end-to-end test of the Restaurant API...")
        
        # Test creating a user
        user_id = test_create_user()
        
        # Test getting user details
        test_get_user(user_id)
        
        # Test getting restaurants and select one for ordering
        restaurant_id, menu_items = test_get_restaurants()
        
        # Test placing an order
        order_id = test_place_order(user_id, restaurant_id, menu_items)
        
        # Test getting order details
        test_get_order(order_id)
        
        # Test getting user orders
        test_get_user_orders(user_id)
        
        # Test getting recommendations
        # Note: this might fail if GROQ_API_KEY is not set
        test_get_recommendations(user_id)
        
        print("\n🎉 End-to-end test completed successfully! 🎉\n")
    
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to the API server.")
        print("   Make sure the server is running at: " + API_BASE_URL)
        print("   Try running 'python3 app.py' in another terminal.\n")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ ERROR: An unexpected error occurred: {str(e)}\n")
        sys.exit(1)

if __name__ == "__main__":
    run_end_to_end_test()

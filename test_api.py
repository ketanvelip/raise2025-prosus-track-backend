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
    
    response = requests.get(f"{API_BASE_URL}/restaurants")
    
    if response.status_code == 200:
        restaurants = response.json()
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
            print(f"\nMenu items available: {len(menu)}")
            
            if not menu:
                print("No menu items found for this restaurant.")
                sys.exit(1)
                
            # Select random menu items (1-3)
            num_items = min(random.randint(1, 3), len(menu))
            selected_items = random.sample([item["_id"] for item in menu], num_items)
            
            print(f"\nSelected {num_items} random items from the menu:")
            for item_id in selected_items:
                item = next((i for i in menu if i["_id"] == item_id), None)
                if item:
                    print(f" - {item['name']} (${item['price']})")
            
            return restaurant['restaurant_id'], selected_items
        else:
            print(f"Error getting restaurant menu: {menu_response.status_code}")
            print(menu_response.text)
            sys.exit(1)
    else:
        print(f"Error getting restaurants: {response.status_code}")
        print(response.text)
        sys.exit(1)

def test_place_order(user_id, restaurant_id, items):
    """Test placing an order and return the created order ID."""
    print_separator("PLACING AN ORDER")
    
    order_data = {
        "user_id": user_id,
        "restaurant_id": restaurant_id,
        "items": items
    }
    
    print("Creating order with data:")
    pretty_print_json(order_data)
    
    response = requests.post(f"{API_BASE_URL}/orders", json=order_data, headers=HEADERS)
    
    if response.status_code == 201:
        order = response.json()
        print("Order created successfully:")
        pretty_print_json(order)
        return order["order_id"]
    else:
        print(f"Error placing order: {response.status_code}")
        print(response.text)
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
    """Test getting personalized restaurant recommendations."""
    print_separator("GETTING RESTAURANT RECOMMENDATIONS")
    
    print(f"Getting recommendations for user_id: {user_id}")
    print("This may take a few seconds as it calls the LLM API...")
    
    response = requests.get(f"{API_BASE_URL}/users/{user_id}/recommendations")
    
    if response.status_code == 200:
        recommendations = response.json()
        print("Recommendations received successfully:")
        pretty_print_json(recommendations)
    else:
        print(f"Error getting recommendations: {response.status_code}")
        print(response.text)
        
        if response.status_code == 503:
            print("\nNOTE: This error is expected if you haven't set up the GROQ_API_KEY in your .env file.")
            print("To enable recommendations, add your Groq API key to the .env file.")

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

import os
import json
import uuid
import random
import sqlite3
from flask import Flask, jsonify, request
from flask_cors import CORS
from groq import Groq
from dotenv import load_dotenv
from db_manager import db
from llm_tools import LLMToolsIntegration
from user_preferences_api import register_user_preferences_endpoints

load_dotenv()

app = Flask(__name__)
CORS(app) # This will allow all origins

# Register user preferences endpoints
register_user_preferences_endpoints(app)

# --- Initialization ---

# We now use SQLite for restaurant data
# This variable will store cached restaurant data for backward compatibility
restaurants = []

# We now use SQLite for storage via db_manager.py
# The following dictionaries are kept for backward compatibility during migration
orders = {}
users = {}

# Groq client setup
groq_api_key = os.environ.get("GROQ_API_KEY")
if not groq_api_key:
    print("WARNING: GROQ_API_KEY environment variable not set. Recommendation features will be disabled.")
    groq_client = None
else:
    groq_client = Groq(api_key=groq_api_key)

# --- Helper Functions ---

def get_restaurant_by_id(restaurant_id):
    """Finds a restaurant by its ID."""
    # First try to get from database
    conn = sqlite3.connect('uber_eats.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get restaurant
    cursor.execute('SELECT * FROM restaurants WHERE restaurant_id = ?', (restaurant_id,))
    restaurant_row = cursor.fetchone()
    
    if not restaurant_row:
        conn.close()
        # Fall back to in-memory cache
        return next((r for r in restaurants if r.get('restaurant_id') == restaurant_id), None)
    
    # Get menu items
    cursor.execute('SELECT * FROM menu_items WHERE restaurant_id = ?', (restaurant_id,))
    menu_items_rows = cursor.fetchall()
    
    # Build restaurant object
    restaurant = {
        'restaurant_id': restaurant_row['restaurant_id'],
        'name': restaurant_row['name'],
        'borough': restaurant_row['borough'],
        'cuisine': restaurant_row['cuisine'],
        'address': {
            'street': restaurant_row['street'],
            'zipcode': restaurant_row['zipcode']
        },
        'menu': []
    }
    
    # Add menu items
    for item_row in menu_items_rows:
        menu_item = {
            '_id': item_row['item_id'],
            'name': item_row['name'],
            'section': item_row['section'],
            'description': item_row['description'],
            'price': item_row['price'],
            'image': item_row['image']
        }
        restaurant['menu'].append(menu_item)
    
    conn.close()
    return restaurant

# --- User Management Endpoints ---

@app.route('/users', methods=['POST'])
def create_user():
    """Creates a new user or returns existing user if email already exists."""
    data = request.get_json()
    if not data or 'username' not in data or 'email' not in data:
        return jsonify({'error': 'Missing username or email in request body'}), 400

    # Create user in database or get existing user if email already exists
    user = db.create_user(data['username'], data['email'])
    
    if user:
        # Also store in memory for backwards compatibility
        users[user['user_id']] = user
        return jsonify(user), 201
    else:
        # This should not happen now that we're returning existing users,
        # but kept as a fallback for unexpected errors
        return jsonify({'error': 'Failed to create or retrieve user'}), 500

@app.route('/users/<user_id>', methods=['GET'])
def get_user(user_id):
    """Returns details for a specific user."""
    # Try to get from database first
    user = db.get_user(user_id)
    
    # Fall back to in-memory if not found in db
    if not user:
        user = users.get(user_id)
        
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404

@app.route('/users/<user_id>/orders', methods=['GET'])
def get_user_orders(user_id):
    """Returns all orders for a specific user."""
    # Get orders from database
    user_orders = db.get_user_orders(user_id)
    
    if user_orders:
        return jsonify(user_orders)
    
    # Fall back to in-memory if not found in db
    if user_id not in users:
        return jsonify({'error': 'User not found'}), 404
    
    user_orders_ids = users[user_id].get('orders', [])
    user_orders = [orders[order_id] for order_id in user_orders_ids if order_id in orders]
    return jsonify(user_orders)

# --- Ingredient Endpoints ---

@app.route('/ingredients/popular', methods=['GET'])
def get_popular_ingredients():
    """Returns the most popular ingredients across all restaurants."""
    category = request.args.get('category')
    limit = request.args.get('limit', 10, type=int)
    
    # Initialize the LLM tools integration to use its database tools
    llm_tools = LLMToolsIntegration()
    
    # Get popular ingredients
    try:
        ingredients = llm_tools.db_tools.get_popular_ingredients(category=category, limit=limit)
        return jsonify({'ingredients': ingredients})
    except Exception as e:
        print(f"Error getting popular ingredients: {str(e)}")
        return jsonify({'error': f'Failed to get popular ingredients: {str(e)}'}), 500

@app.route('/restaurants/<restaurant_id>/ingredients', methods=['GET'])
def get_restaurant_ingredients(restaurant_id):
    """Returns all ingredients available at a specific restaurant."""
    # Initialize the LLM tools integration to use its database tools
    llm_tools = LLMToolsIntegration()
    
    # Get restaurant ingredients
    try:
        ingredients = llm_tools.db_tools.get_restaurant_ingredients(restaurant_id)
        return jsonify({'ingredients': ingredients})
    except Exception as e:
        print(f"Error getting restaurant ingredients: {str(e)}")
        return jsonify({'error': f'Failed to get restaurant ingredients: {str(e)}'}), 500

@app.route('/restaurants/search/ingredients', methods=['POST'])
def search_restaurants_by_ingredients():
    """Search for restaurants that have specific ingredients available."""
    data = request.get_json()
    
    if not data or 'ingredients' not in data:
        return jsonify({'error': 'Ingredients list is required'}), 400
    
    ingredients = data.get('ingredients', [])
    match_all = data.get('match_all', False)
    limit = data.get('limit', 5)
    
    # Initialize the LLM tools integration to use its database tools
    llm_tools = LLMToolsIntegration()
    
    # Search restaurants by ingredients
    try:
        restaurants = llm_tools.db_tools.search_by_ingredients(
            ingredients=ingredients, 
            match_all=match_all, 
            limit=limit
        )
        return jsonify({'restaurants': restaurants})
    except Exception as e:
        print(f"Error searching restaurants by ingredients: {str(e)}")
        return jsonify({'error': f'Failed to search restaurants: {str(e)}'}), 500

# --- Restaurant and Menu Endpoints ---

@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    """Returns a list of all restaurants."""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)  # Default 50 restaurants per page
    
    # Connect to database
    conn = sqlite3.connect('uber_eats.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get total count
    cursor.execute('SELECT COUNT(*) as count FROM restaurants')
    total_count = cursor.fetchone()['count']
    
    # Calculate offset
    offset = (page - 1) * per_page
    
    # Get restaurants with pagination
    cursor.execute('SELECT * FROM restaurants LIMIT ? OFFSET ?', (per_page, offset))
    restaurant_rows = cursor.fetchall()
    
    # Build response
    result = []
    for row in restaurant_rows:
        restaurant_id = row['restaurant_id']
        
        # Get menu items (limited to 10 for performance)
        cursor.execute('SELECT * FROM menu_items WHERE restaurant_id = ? LIMIT 10', (restaurant_id,))
        menu_items_rows = cursor.fetchall()
        
        # Build restaurant object
        restaurant = {
            'restaurant_id': restaurant_id,
            'name': row['name'],
            'borough': row['borough'],
            'cuisine': row['cuisine'],
            'address': {
                'street': row['street'],
                'zipcode': row['zipcode']
            },
            'menu': []
        }
        
        # Add menu items
        for item_row in menu_items_rows:
            menu_item = {
                '_id': item_row['item_id'],
                'name': item_row['name'],
                'section': item_row['section'],
                'description': item_row['description'],
                'price': item_row['price'],
                'image': item_row['image']
            }
            restaurant['menu'].append(menu_item)
        
        result.append(restaurant)
    
    # Add pagination metadata
    response = {
        'restaurants': result,
        'pagination': {
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'pages': (total_count + per_page - 1) // per_page  # Ceiling division
        }
    }
    
    conn.close()
    return jsonify(response)

@app.route('/restaurants/<restaurant_id>', methods=['GET'])
def get_restaurant(restaurant_id):
    """Returns details for a specific restaurant."""
    restaurant = get_restaurant_by_id(restaurant_id)
    if restaurant:
        return jsonify(restaurant)
    return jsonify({'error': 'Restaurant not found'}), 404

@app.route('/restaurants/<restaurant_id>/menu', methods=['GET'])
def get_menu(restaurant_id):
    """Returns the menu for a specific restaurant."""
    # Connect to database
    conn = sqlite3.connect('uber_eats.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Check if restaurant exists
    cursor.execute('SELECT restaurant_id FROM restaurants WHERE restaurant_id = ?', (restaurant_id,))
    if not cursor.fetchone():
        conn.close()
        return jsonify({'error': 'Restaurant not found'}), 404
    
    # Get menu items
    cursor.execute('SELECT * FROM menu_items WHERE restaurant_id = ?', (restaurant_id,))
    menu_items_rows = cursor.fetchall()
    
    # Format menu items
    menu = []
    for row in menu_items_rows:
        menu_item = {
            '_id': row['item_id'],
            'name': row['name'],
            'section': row['section'],
            'description': row['description'],
            'price': row['price'],
            'image': row['image']
        }
        menu.append(menu_item)
    
    conn.close()
    return jsonify(menu)

# --- Order Management Endpoints ---

@app.route('/orders', methods=['POST'])
def create_order():
    """Creates an order and links it to a user."""
    data = request.get_json()
    if not data or 'user_id' not in data or 'restaurant_id' not in data or 'items' not in data:
        return jsonify({'error': 'Missing user_id, restaurant_id, or items in request body'}), 400

    user_id = data['user_id']
    
    # Create order in database
    new_order = db.create_order(user_id, data['restaurant_id'], data['items'])
    
    if not new_order:
        # Check if user exists in memory
        if user_id not in users:
            return jsonify({'error': 'User not found'}), 404
        
        # Fall back to in-memory storage
        order_id = str(uuid.uuid4())
        new_order = {
            'order_id': order_id,
            'user_id': user_id,
            'restaurant_id': data['restaurant_id'],
            'items': data['items'],
            'status': 'pending'
        }
        orders[order_id] = new_order
        users[user_id]['orders'].append(order_id)
    
    return jsonify(new_order), 201

@app.route('/orders/<order_id>', methods=['GET'])
def get_order(order_id):
    """Checks the status of an order."""
    # Get order from database
    order = db.get_order(order_id)
    
    # Fall back to in-memory if not found in db
    if not order:
        order = orders.get(order_id)
        
    if order:
        return jsonify(order)
    return jsonify({'error': 'Order not found'}), 404

# --- LLM-Powered Endpoints ---

@app.route('/restaurants/<restaurant_id>/custom-foods', methods=['POST'])
def get_custom_foods(restaurant_id):
    """Generate custom food recommendations based on ingredients a restaurant has on hand."""
    data = request.get_json() or {}
    preferences = data.get('preferences', {})
    
    # Initialize the LLM tools integration
    llm_tools = LLMToolsIntegration()
    
    # Generate custom food recommendations
    try:
        custom_foods = llm_tools.generate_custom_food(restaurant_id, preferences)
        return jsonify(custom_foods)
    except Exception as e:
        print(f"Error generating custom food recommendations: {str(e)}")
        return jsonify({
            'restaurant_id': restaurant_id,
            'error': f'Failed to generate custom food recommendations: {str(e)}',
            'custom_foods': []
        }), 500

@app.route('/recommendations', methods=['GET'])
def get_recommendations():
    """Returns restaurant recommendations based on user's order history using LLM function calling."""
    user_id = request.args.get('user_id')
    query = request.args.get('query', 'Give me restaurant recommendations based on my order history')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    # Get user's order history
    user_orders = db.get_user_orders(user_id)
    
    if not user_orders:
        return jsonify({
            'text': 'Not enough order history to provide a recommendation. Try ordering something first!',
            'recommendations': [],
            'follow_up_question': 'Would you like to explore our most popular restaurants instead?'
        })
    
    # Initialize the LLM tools integration
    llm_tools = LLMToolsIntegration()
    
    # Prepare user context
    user_context = {
        "user_id": user_id,
        "order_count": len(user_orders)
    }
    
    # Generate recommendations using function calling
    try:
        # This now returns a structured JSON object with text, recommendations array, and follow-up question
        recommendation_data = llm_tools.generate_recommendations(query, user_context)
        return jsonify(recommendation_data)
    except Exception as e:
        print(f"Error generating recommendations: {str(e)}")
        return jsonify({
            'text': f'Failed to generate recommendation: {str(e)}',
            'recommendations': [],
            'follow_up_question': 'Would you like to try again with a different query?'
        }), 500

@app.route('/generate_options', methods=['POST'])
def generate_options():
    """Generate food options based on user input."""
    data = request.get_json()
    if not data or 'email' not in data or 'input_text' not in data:
        return jsonify({'error': 'Missing email or input_text in request body'}), 400
    
    user_email = data['email']
    input_text = data['input_text']
    
    # Retrieve user by email if they exist
    user = db.get_user_by_email(user_email)
    
    # We'll use user preferences in the future to personalize results
    # even if the user doesn't exist, we'll still generate recommendations
    
    if not groq_client:
        return jsonify({"error": "Service not configured. Missing GROQ_API_KEY."}), 503
    
    # Prepare prompt for LLM
    prompt = f"""
    # Food Recommendation Assistant
    You are an expert culinary advisor with deep knowledge of global cuisines, flavor profiles, and food preferences.
    The current date is July 8, 2025.
    
    ## Your Task
    Based on the user input: "{input_text}", suggest exactly 3 food options that would perfectly satisfy their request.
    Each suggestion should be thoughtfully selected based on the user's expressed preferences.
    
    ## User Information
    Email: {user_email}
    Request: "{input_text}"
    
    ## Response Requirements
    For each food option, you must provide:
    - A descriptive and appetizing name for the food item
    - A realistic URL to an image of the food (create a plausible URL)
    - The specific cuisine type the dish belongs to
    
    ## Response Format
    Return ONLY valid JSON with this exact structure:
    {{"options": [{{"name": "Food Name", "image_url": "https://example.com/image.jpg", "cuisine": "Cuisine Type"}}, ...]}}
    
    Do not include any explanatory text outside the JSON structure.
    Be creative, specific, and ensure your suggestions truly match what the user is looking for.
    """
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a sophisticated food recommendation assistant with expertise in global cuisines, culinary trends, and personalization. You excel at understanding user preferences from minimal context and providing perfectly tailored food suggestions. You always respond with properly structured JSON data exactly as requested, with no additional text or explanations. Your food suggestions are creative, specific, and precisely matched to the user's needs."},
                {"role": "user", "content": prompt}
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        
        llm_response = chat_completion.choices[0].message.content
        print(f"\n[DEBUG] Raw LLM response:\n{llm_response}\n")
        
        # Process and validate the LLM response
        # Sometimes LLMs add markdown code blocks, so we'll clean that up
        llm_response = llm_response.replace('```json', '').replace('```', '').strip()
        
        # Parse the response and reformat it to match the required structure
        try:
            # Handle the case where the response might not be valid JSON
            try:
                parsed_response = json.loads(llm_response)
                print(f"[DEBUG] Parsed JSON successfully")
            except json.JSONDecodeError as e:
                print(f"[DEBUG] JSON parsing error: {e}")
                print(f"[DEBUG] Attempting to extract JSON from response...")
                
                # Try to find JSON-like structure in the text
                import re
                json_match = re.search(r'\{[\s\S]*\}', llm_response)
                if json_match:
                    json_str = json_match.group(0)
                    print(f"[DEBUG] Found potential JSON: {json_str}")
                    parsed_response = json.loads(json_str)
                else:
                    raise ValueError("Could not extract JSON from LLM response")
            
            print(f"[DEBUG] Parsed response structure: {type(parsed_response).__name__}")
            
            # Restructure the response to match the required format
            result = {
                "category": "food",
                "options": []
            }
            
            # Extract options from LLM response and format them
            if isinstance(parsed_response, list):
                print(f"[DEBUG] Processing list response with {len(parsed_response)} items")
                for item in parsed_response[:3]:  # Ensure we have at most 3 items
                    option = {
                        "item_name": item.get("name", ""),
                        "item_img_url": item.get("image_url", item.get("image", "")),
                        "item_cuisine": item.get("cuisine", "")
                    }
                    result["options"].append(option)
            elif "options" in parsed_response:
                print(f"[DEBUG] Processing 'options' field with {len(parsed_response.get('options', []))} items")
                for item in parsed_response["options"][:3]:
                    option = {
                        "item_name": item.get("item_name", item.get("name", "")),
                        "item_img_url": item.get("item_img_url", item.get("image", item.get("image_url", ""))),
                        "item_cuisine": item.get("item_cuisine", item.get("cuisine", ""))
                    }
                    result["options"].append(option)
            elif "food" in parsed_response and isinstance(parsed_response["food"], list):
                print(f"[DEBUG] Processing 'food' list with {len(parsed_response['food'])} items")
                for item in parsed_response["food"][:3]:
                    option = {
                        "item_name": item.get("name", item.get("item_name", "")),
                        "item_img_url": item.get("image", item.get("image_url", item.get("item_img_url", ""))),
                        "item_cuisine": item.get("cuisine", item.get("item_cuisine", ""))
                    }
                    result["options"].append(option)
            else:
                # Fallback for unexpected structure but valid JSON
                print(f"[DEBUG] Unrecognized response structure, using fallback parsing")
                # Try to find any fields that might contain our needed data
                # Just use first-level fields in the JSON that might be options
                for key, value in parsed_response.items():
                    if isinstance(value, dict):
                        option = {
                            "item_name": value.get("name", value.get("item_name", key)),
                            "item_img_url": value.get("image", value.get("image_url", value.get("url", ""))),
                            "item_cuisine": value.get("cuisine", value.get("type", ""))
                        }
                        result["options"].append(option)
                        if len(result["options"]) >= 3:
                            break
            
            # Ensure we have exactly 3 options
            while len(result["options"]) < 3:
                result["options"].append({
                    "item_name": "Default Option " + str(len(result["options"]) + 1),
                    "item_img_url": "https://example.com/default-food-image.jpg",
                    "item_cuisine": "Mixed"
                })
            
            print(f"[DEBUG] Final result structure: {result}")
            return jsonify(result)
            
        except json.JSONDecodeError:
            # If the LLM didn't return valid JSON, generate a fallback response
            result = {
                "category": "food",
                "options": [
                    {
                        "item_name": "",
                        "item_img_url": "",
                        "item_cuisine": ""
                    },
                    {
                        "item_name": "",
                        "item_img_url": "",
                        "item_cuisine": ""
                    },
                    {
                        "item_name": "",
                        "item_img_url": "",
                        "item_cuisine": ""
                    }
                ]
            }
            return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": f"Failed to generate options: {str(e)}"}), 500

@app.route('/users/<user_id>/notes', methods=['GET'])
def get_user_notes(user_id):
    """Get LLM-generated notes and insights about a user."""
    # Check if user exists
    user = db.get_user(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if we should generate a new note
    generate_new = request.args.get('generate', 'false').lower() == 'true'
    
    # Get existing notes
    existing_notes = db.get_user_notes(user_id)
    
    # Generate a new note if requested
    if generate_new and groq_client:
        # Get user's order history
        user_orders = db.get_user_orders(user_id)
        
        if not user_orders:
            return jsonify({
                'notes': existing_notes,
                'message': 'Not enough order history to generate new insights.'
            })
        
        # Prepare data for LLM
        order_history = []
        restaurant_counts = {}
        cuisine_counts = {}
        item_counts = {}
        
        for order in user_orders:
            restaurant = get_restaurant_by_id(order['restaurant_id'])
            if restaurant:
                # Count restaurant visits
                restaurant_name = restaurant['name']
                restaurant_counts[restaurant_name] = restaurant_counts.get(restaurant_name, 0) + 1
                
                # Get ordered items
                ordered_items = []
                for item_id in order['items']:
                    for menu_item in restaurant.get('menu', []):
                        if menu_item.get('_id') == item_id:
                            ordered_items.append(menu_item)
                            
                            # Count cuisines
                            if 'section' in menu_item:
                                cuisine_counts[menu_item['section']] = cuisine_counts.get(menu_item['section'], 0) + 1
                            
                            # Count items
                            item_name = menu_item.get('name', '')
                            item_counts[item_name] = item_counts.get(item_name, 0) + 1
                
                # Add to order history
                order_history.append({
                    'restaurant': restaurant_name,
                    'items': [item.get('name', '') for item in ordered_items]
                })
        
        # Create prompt for LLM
        prompt = f"""
        # User Insight Generator
        You are an expert in analyzing user food preferences and generating insightful notes about their habits and tastes.
        The current date is July 8, 2025.
        
        ## Your Task
        Analyze this user's order history and generate 3 distinct insights about their food preferences and habits.
        These insights should be thoughtful, specific, and reveal patterns that might not be immediately obvious.
        
        ## User Information
        User ID: {user_id}
        Total Orders: {len(user_orders)}
        
        ## Order History
        {json.dumps(order_history, indent=2)}
        
        ## Restaurant Visit Frequency
        {json.dumps(restaurant_counts, indent=2)}
        
        ## Cuisine Type Frequency
        {json.dumps(cuisine_counts, indent=2)}
        
        ## Food Item Frequency
        {json.dumps(item_counts, indent=2)}
        
        ## Response Format
        Generate exactly 3 distinct insights about this user's preferences, each 1-2 sentences long.
        Each insight should reveal something meaningful about their tastes, habits, or patterns.
        Format each insight as a separate paragraph.
        Do not include any introductory or concluding text.
        """
        
        try:
            # Call LLM to generate insights
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an expert in analyzing food preferences and generating insightful notes about user habits and tastes. Your insights are specific, thoughtful, and reveal meaningful patterns."},
                    {"role": "user", "content": prompt}
                ],
                model="meta-llama/llama-4-scout-17b-16e-instruct",
            )
            
            insights = chat_completion.choices[0].message.content
            
            # Split insights into separate notes
            insight_paragraphs = [p.strip() for p in insights.split('\n\n') if p.strip()]
            
            # Store each insight as a separate note
            for i, insight in enumerate(insight_paragraphs[:3]):  # Limit to 3 insights
                db.add_user_note(user_id, insight, f'food_insight_{i+1}')
            
            # Get updated notes
            existing_notes = db.get_user_notes(user_id)
            
            return jsonify({
                'notes': existing_notes,
                'message': 'Generated new insights based on order history.'
            })
            
        except Exception as e:
            return jsonify({
                'notes': existing_notes,
                'error': f'Failed to generate new insights: {str(e)}'
            })
    
    # Return existing notes
    return jsonify({
        'notes': existing_notes
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5005, debug=True)

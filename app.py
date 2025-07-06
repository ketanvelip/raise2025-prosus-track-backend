import os
import json
import uuid
import random
from flask import Flask, jsonify, request
from groq import Groq
from dotenv import load_dotenv
from db_manager import db

load_dotenv()

app = Flask(__name__)

# --- Initialization ---

# Load restaurant data
with open('restaurants.json', 'r', encoding='utf-8') as f:
    restaurants = json.load(f)

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
    return next((r for r in restaurants if r.get('restaurant_id') == restaurant_id), None)

# --- User Management Endpoints ---

@app.route('/users', methods=['POST'])
def create_user():
    """Creates a new user."""
    data = request.get_json()
    if not data or 'username' not in data or 'email' not in data:
        return jsonify({'error': 'Missing username or email in request body'}), 400

    # Create user in database
    user = db.create_user(data['username'], data['email'])
    
    if user:
        # Also store in memory for backwards compatibility
        users[user['user_id']] = user
        return jsonify(user), 201
    else:
        return jsonify({'error': 'Email already exists'}), 400

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

# --- Restaurant and Menu Endpoints ---

@app.route('/restaurants', methods=['GET'])
def get_restaurants():
    """Returns a list of all restaurants."""
    return jsonify(restaurants)

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
    restaurant = get_restaurant_by_id(restaurant_id)
    if restaurant:
        return jsonify(restaurant.get('menu', []))
    return jsonify({'error': 'Restaurant not found'}), 404

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

# --- Recommendation Endpoints ---

@app.route('/users/<user_id>/recommendations', methods=['GET'])
def get_recommendations(user_id):
    if not groq_client:
        return jsonify({"error": "Recommendation service is not configured. Missing GROQ_API_KEY."}), 503

    if user_id not in users:
        return jsonify({"error": "User not found"}), 404

    user_orders_ids = users[user_id].get('orders', [])
    if not user_orders_ids:
        return jsonify({"recommendation": "Not enough order history to provide a recommendation. Try ordering something first!"})

    history_restaurants = set()
    order_history_summary = []
    for order_id in user_orders_ids:
        order = orders.get(order_id)
        if order:
            restaurant = get_restaurant_by_id(order['restaurant_id'])
            if restaurant:
                history_restaurants.add(restaurant['name'])
                ordered_items = [menu_item for menu_item in restaurant.get('menu', []) if menu_item.get('_id') in order.get('items', [])]
                sections = set(item['section'] for item in ordered_items if 'section' in item)
                if sections:
                    order_history_summary.append(f"Ordered from sections '{', '.join(sections)}' at '{restaurant['name']}'.")

    if not order_history_summary:
        return jsonify({"recommendation": "Could not build valid order history."})

    available_restaurants = [r for r in restaurants if r['name'] not in history_restaurants]
    sample_size = min(30, len(available_restaurants))  # Send a sample of 30, or fewer if not enough are available
    sampled_restaurants = random.sample(available_restaurants, sample_size)

    available_restaurants_info = []
    for r in sampled_restaurants:
        all_sections = set(item.get('section') for item in r.get('menu', []) if item.get('section'))
        if all_sections:
            available_restaurants_info.append(f"- {r['name']} (offers: {', '.join(list(all_sections)[:3])})")

    prompt = (
        "Based on the user's order history, suggest 3 new restaurants to try from the 'Available Restaurants' list. "
        "Provide a brief, one-sentence reason for each suggestion based on the menu sections. "
        "Do not suggest any restaurants the user has already ordered from.\n\n"
        "## User Order History:\n"
        f"{'\n'.join(order_history_summary)}\n\n"
        "## Available Restaurants:\n"
        f"{'\n'.join(available_restaurants_info)}\n\n"
        "Provide only the 3 recommendations in a simple, unnumbered list."
    )

    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful restaurant recommendation assistant."},
                {"role": "user", "content": prompt}
            ],
            model="meta-llama/llama-4-scout-17b-16e-instruct",
        )
        recommendation = chat_completion.choices[0].message.content
        return jsonify({"recommendation": recommendation})
    except Exception as e:
        return jsonify({"error": f"Failed to get recommendation from LLM: {str(e)}"}), 500

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
    Based on the user input: "{input_text}", suggest 3 food options.
    For each food option, provide:
    - A name for the food item
    - A URL to an image of the food (you can make up a realistic URL)
    - The cuisine type
    
    Return the results in JSON format with no additional text.
    """
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful food recommendation assistant. "
                 "Return only valid JSON with no additional text or explanations."},
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)

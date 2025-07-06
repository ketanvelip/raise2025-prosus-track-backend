# Uber Eats API with LLM-Powered Recommendations

A Flask-based API that simulates Uber Eats functionality with LLM-powered restaurant and food recommendations.

## Features

- **Restaurant Listings:** Browse a comprehensive dataset of restaurants and menus
- **User Management:** Create users and manage their profiles
- **Order Processing:** Place and track food orders
- **LLM-Powered Recommendations:** Get personalized restaurant recommendations based on order history
- **Food Option Generator:** Receive food suggestions based on natural language input
- **Persistent Storage:** SQLite database for reliable data storage

## API Endpoints

### Restaurant Endpoints
- `GET /restaurants` - Get all restaurants
- `GET /restaurants/<restaurant_id>` - Get details for a specific restaurant
- `GET /restaurants/<restaurant_id>/menu` - Get menu for a specific restaurant

### User Endpoints
- `POST /users` - Create a new user
- `GET /users/<user_id>` - Get user details
- `GET /users/<user_id>/orders` - Get all orders for a user
- `GET /users/<user_id>/recommendations` - Get personalized restaurant recommendations

### Order Endpoints
- `POST /orders` - Create a new order
- `GET /orders/<order_id>` - Get order details

### Food Options Endpoint
- `POST /generate_options` - Generate food options based on user input text

## Technologies Used

- **Flask:** Web framework for building the API
- **SQLite:** Database for persistent storage
- **Groq API:** LLM provider for recommendations (Meta Llama 4 Scout model)
- **Python-dotenv:** For environment variable management

## Setup

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Set up your Groq API key: Create a `.env` file with `GROQ_API_KEY=your-api-key`
4. Run the server: `python app.py`

## Testing

Run the test scripts to verify functionality:
- `python test_api.py` - Tests all core API functionality
- `python test_options_api.py` - Tests the food options generation endpoint

## Database Administration

Use the included database administration utility:
- `python db_admin.py users` - List all users
- `python db_admin.py orders` - List all orders
- `python db_admin.py user-orders -e user@example.com` - View orders for a specific user

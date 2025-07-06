import sqlite3
import json
import os
import uuid

class DatabaseManager:
    """
    Database manager for the Uber Eats API.
    Handles user storage, orders, and recommendation preferences.
    """
    def __init__(self, db_path='uber_eats.db'):
        """Initialize the database connection."""
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.initialize_db()
    
    def connect(self):
        """Connect to the SQLite database."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row  # Allows accessing columns by name
        self.cursor = self.conn.cursor()
        return self.conn, self.cursor
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
    
    def initialize_db(self):
        """Create necessary tables if they don't exist."""
        conn, cursor = self.connect()
        
        # Create users table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            preferences TEXT
        )
        ''')
        
        # Create orders table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            restaurant_id TEXT NOT NULL,
            items TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Create food preferences table for recommendations
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS food_preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            cuisine TEXT,
            food_item TEXT,
            rating INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        conn.commit()
        self.close()
    
    # --- User Management ---
    
    def create_user(self, username, email):
        """Create a new user and return the user data."""
        conn, cursor = self.connect()
        
        user_id = str(uuid.uuid4())
        
        try:
            cursor.execute(
                'INSERT INTO users (user_id, username, email) VALUES (?, ?, ?)',
                (user_id, username, email)
            )
            conn.commit()
            
            user_data = {
                'user_id': user_id,
                'username': username,
                'email': email,
                'orders': []
            }
            
            return user_data
            
        except sqlite3.IntegrityError:
            # Email already exists
            return None
        finally:
            self.close()
    
    def get_user(self, user_id):
        """Get user details by ID."""
        conn, cursor = self.connect()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user_row = cursor.fetchone()
        
        if not user_row:
            self.close()
            return None
        
        # Get user's orders
        cursor.execute('SELECT order_id FROM orders WHERE user_id = ?', (user_id,))
        order_rows = cursor.fetchall()
        order_ids = [row['order_id'] for row in order_rows]
        
        user_data = {
            'user_id': user_row['user_id'],
            'username': user_row['username'],
            'email': user_row['email'],
            'orders': order_ids
        }
        
        self.close()
        return user_data
    
    def get_user_by_email(self, email):
        """Get user details by email."""
        conn, cursor = self.connect()
        
        cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
        user_row = cursor.fetchone()
        
        if not user_row:
            self.close()
            return None
        
        user_id = user_row['user_id']
        self.close()
        
        return self.get_user(user_id)
    
    # --- Order Management ---
    
    def create_order(self, user_id, restaurant_id, items):
        """Create a new order and return the order data."""
        conn, cursor = self.connect()
        
        # Check if user exists
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        if not cursor.fetchone():
            self.close()
            return None
        
        order_id = str(uuid.uuid4())
        items_json = json.dumps(items)
        
        cursor.execute(
            'INSERT INTO orders (order_id, user_id, restaurant_id, items, status) VALUES (?, ?, ?, ?, ?)',
            (order_id, user_id, restaurant_id, items_json, 'pending')
        )
        conn.commit()
        
        order_data = {
            'order_id': order_id,
            'user_id': user_id,
            'restaurant_id': restaurant_id,
            'items': items,
            'status': 'pending'
        }
        
        self.close()
        return order_data
    
    def get_order(self, order_id):
        """Get order details by ID."""
        conn, cursor = self.connect()
        
        cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
        order_row = cursor.fetchone()
        
        if not order_row:
            self.close()
            return None
        
        order_data = {
            'order_id': order_row['order_id'],
            'user_id': order_row['user_id'],
            'restaurant_id': order_row['restaurant_id'],
            'items': json.loads(order_row['items']),
            'status': order_row['status']
        }
        
        self.close()
        return order_data
    
    def get_user_orders(self, user_id):
        """Get all orders for a specific user."""
        conn, cursor = self.connect()
        
        cursor.execute('SELECT * FROM orders WHERE user_id = ?', (user_id,))
        order_rows = cursor.fetchall()
        
        orders = []
        for row in order_rows:
            order_data = {
                'order_id': row['order_id'],
                'user_id': row['user_id'],
                'restaurant_id': row['restaurant_id'],
                'items': json.loads(row['items']),
                'status': row['status']
            }
            orders.append(order_data)
        
        self.close()
        return orders
    
    # --- Preference Management ---
    
    def add_food_preference(self, user_id, cuisine, food_item, rating):
        """Add or update a food preference for a user."""
        conn, cursor = self.connect()
        
        try:
            cursor.execute(
                'INSERT INTO food_preferences (user_id, cuisine, food_item, rating) VALUES (?, ?, ?, ?)',
                (user_id, cuisine, food_item, rating)
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            self.close()
    
    def get_user_preferences(self, user_id):
        """Get all food preferences for a user."""
        conn, cursor = self.connect()
        
        cursor.execute('SELECT cuisine, food_item, rating FROM food_preferences WHERE user_id = ?', (user_id,))
        preference_rows = cursor.fetchall()
        
        preferences = []
        for row in preference_rows:
            preferences.append({
                'cuisine': row['cuisine'],
                'food_item': row['food_item'],
                'rating': row['rating']
            })
        
        self.close()
        return preferences

# Create an instance for use in the application
db = DatabaseManager()

# Example usage:
if __name__ == "__main__":
    # Initialize the database
    db = DatabaseManager()
    print("Database initialized successfully!")
    
    # Test creating a user
    user = db.create_user("test_user", "test@example.com")
    print(f"Created user: {user}")
    
    # Test retrieving a user
    retrieved_user = db.get_user(user['user_id'])
    print(f"Retrieved user: {retrieved_user}")

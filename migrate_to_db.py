#!/usr/bin/env python3
"""
Menu Data Migration Script

This script migrates restaurant and menu data from CSV to SQLite database.
"""

import csv
import sqlite3
import uuid
import os
import json
from collections import defaultdict

# Database configuration
DB_PATH = 'uber_eats.db'

def create_tables(conn, cursor):
    """Create the necessary tables for restaurants and menu items."""
    print("Creating tables...")
    
    # Create restaurants table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS restaurants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        restaurant_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        borough TEXT,
        cuisine TEXT,
        street TEXT,
        zipcode TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Create menu_items table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS menu_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id TEXT UNIQUE NOT NULL,
        restaurant_id TEXT NOT NULL,
        name TEXT NOT NULL,
        section TEXT,
        description TEXT,
        price REAL,
        image TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (restaurant_id)
    )
    ''')
    
    conn.commit()
    print("Tables created successfully!")

def import_from_csv(csv_path, conn, cursor):
    """Import data from CSV file into the database."""
    print(f"Importing data from {csv_path}...")
    
    # Dictionary to store restaurant data
    restaurants = {}
    
    # Read CSV file
    with open(csv_path, 'r', encoding='utf-8') as file:
        reader = csv.reader(file)
        
        # Skip header if it exists
        try:
            first_row = next(reader)
            # Check if this is a header row or actual data
            if not any(first_row[0].lower() in col.lower() for col in ['restaurant', 'name']):
                # Not a header, reset file pointer
                file.seek(0)
        except StopIteration:
            print("CSV file is empty!")
            return
        
        # Process each row
        for row in reader:
            if len(row) < 5:  # Ensure row has enough columns
                print(f"Skipping invalid row: {row}")
                continue
            
            restaurant_name = row[0].strip()
            section = row[1].strip()
            item_name = row[2].strip()
            description = row[3].strip()
            price_str = row[4].strip()
            
            # Extract price
            price = None
            if price_str:
                # Remove $ and any other non-numeric characters except decimal point
                price_clean = ''.join(c for c in price_str if c.isdigit() or c == '.')
                try:
                    price = float(price_clean) if price_clean else None
                except ValueError:
                    price = None
            
            # Generate or get restaurant ID
            if restaurant_name not in restaurants:
                restaurant_id = str(uuid.uuid4())
                restaurants[restaurant_name] = {
                    'restaurant_id': restaurant_id,
                    'name': restaurant_name,
                    'borough': 'Unknown',
                    'cuisine': 'Unknown',
                    'street': 'Unknown',
                    'zipcode': 'Unknown',
                    'menu_items': []
                }
            else:
                restaurant_id = restaurants[restaurant_name]['restaurant_id']
            
            # Create menu item
            item_id = str(uuid.uuid4())
            menu_item = {
                'item_id': item_id,
                'restaurant_id': restaurant_id,
                'name': item_name,
                'section': section,
                'description': description,
                'price': price,
                'image': ''
            }
            
            # Add to restaurant's menu items
            restaurants[restaurant_name]['menu_items'].append(menu_item)
    
    # Insert data into database
    for restaurant_name, restaurant_data in restaurants.items():
        # Insert restaurant
        cursor.execute(
            'INSERT OR IGNORE INTO restaurants (restaurant_id, name, borough, cuisine, street, zipcode) VALUES (?, ?, ?, ?, ?, ?)',
            (
                restaurant_data['restaurant_id'],
                restaurant_data['name'],
                restaurant_data['borough'],
                restaurant_data['cuisine'],
                restaurant_data['street'],
                restaurant_data['zipcode']
            )
        )
        
        # Insert menu items
        for item in restaurant_data['menu_items']:
            cursor.execute(
                'INSERT OR IGNORE INTO menu_items (item_id, restaurant_id, name, section, description, price, image) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (
                    item['item_id'],
                    item['restaurant_id'],
                    item['name'],
                    item['section'],
                    item['description'],
                    item['price'],
                    item['image']
                )
            )
    
    conn.commit()
    print(f"Imported {len(restaurants)} restaurants with their menu items!")
    return restaurants

def import_from_json(json_path, conn, cursor):
    """Import data from existing JSON file into the database."""
    print(f"Importing data from {json_path}...")
    
    with open(json_path, 'r', encoding='utf-8') as file:
        restaurants_data = json.load(file)
    
    for restaurant in restaurants_data:
        # Insert restaurant
        cursor.execute(
            'INSERT OR IGNORE INTO restaurants (restaurant_id, name, borough, cuisine, street, zipcode) VALUES (?, ?, ?, ?, ?, ?)',
            (
                restaurant['restaurant_id'],
                restaurant['name'],
                restaurant.get('borough', 'Unknown'),
                restaurant.get('cuisine', 'Unknown'),
                restaurant.get('address', {}).get('street', 'Unknown'),
                restaurant.get('address', {}).get('zipcode', 'Unknown')
            )
        )
        
        # Insert menu items
        for item in restaurant.get('menu', []):
            item_id = item.get('_id', str(uuid.uuid4()))
            cursor.execute(
                'INSERT OR IGNORE INTO menu_items (item_id, restaurant_id, name, section, description, price, image) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (
                    item_id,
                    restaurant['restaurant_id'],
                    item.get('name', ''),
                    item.get('section', ''),
                    item.get('description', ''),
                    item.get('price', None),
                    item.get('image', '')
                )
            )
    
    conn.commit()
    print(f"Imported {len(restaurants_data)} restaurants from JSON!")

def export_to_json(conn, cursor, output_path):
    """Export database data to JSON format for backward compatibility."""
    print(f"Exporting data to {output_path}...")
    
    # Get all restaurants
    cursor.execute('SELECT * FROM restaurants')
    restaurants_rows = cursor.fetchall()
    
    restaurants_data = []
    for row in restaurants_rows:
        restaurant_id = row['restaurant_id']
        
        # Get menu items for this restaurant
        cursor.execute('SELECT * FROM menu_items WHERE restaurant_id = ?', (restaurant_id,))
        menu_items_rows = cursor.fetchall()
        
        menu_items = []
        for item_row in menu_items_rows:
            menu_item = {
                '_id': item_row['item_id'],
                'name': item_row['name'],
                'section': item_row['section'],
                'description': item_row['description'],
                'price': item_row['price'],
                'image': item_row['image']
            }
            menu_items.append(menu_item)
        
        # Create restaurant object
        restaurant = {
            'restaurant_id': restaurant_id,
            'name': row['name'],
            'borough': row['borough'],
            'cuisine': row['cuisine'],
            'address': {
                'street': row['street'],
                'zipcode': row['zipcode']
            },
            'menu': menu_items
        }
        
        restaurants_data.append(restaurant)
    
    # Write to JSON file
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(restaurants_data, file, indent=2)
    
    print(f"Exported {len(restaurants_data)} restaurants to JSON!")

def main():
    """Main function to run the migration."""
    print("Starting menu data migration to SQLite...")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Create tables
    create_tables(conn, cursor)
    
    # Check if we should import from CSV or JSON
    csv_path = 'Menu Items.csv'
    json_path = 'restaurants.json'
    
    if os.path.exists(json_path):
        # Import from existing JSON file
        import_from_json(json_path, conn, cursor)
    elif os.path.exists(csv_path):
        # Import from CSV
        import_from_csv(csv_path, conn, cursor)
    else:
        print("Error: Neither CSV nor JSON file found!")
        return
    
    # Export to JSON for backward compatibility
    export_to_json(conn, cursor, 'restaurants_db_export.json')
    
    # Close connection
    conn.close()
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    main()

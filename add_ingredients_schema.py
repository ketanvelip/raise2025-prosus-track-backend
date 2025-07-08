#!/usr/bin/env python3
"""
Add Ingredients Schema to Restaurant Database

This script adds tables for ingredients and restaurant-ingredient relationships
to the existing SQLite database.
"""

import sqlite3
import os
from typing import List, Dict, Any
import json
import random

# Sample ingredients for demonstration
SAMPLE_INGREDIENTS = [
    # Proteins
    "chicken", "beef", "pork", "lamb", "fish", "shrimp", "tofu", "eggs", "turkey",
    # Vegetables
    "tomato", "lettuce", "onion", "garlic", "bell pepper", "carrot", "broccoli", 
    "spinach", "mushroom", "cucumber", "zucchini", "potato", "sweet potato",
    # Grains
    "rice", "pasta", "bread", "quinoa", "couscous", "noodles", "tortilla",
    # Dairy
    "cheese", "milk", "cream", "yogurt", "butter",
    # Spices & Herbs
    "salt", "pepper", "cumin", "coriander", "basil", "oregano", "thyme", "rosemary",
    "cilantro", "parsley", "mint", "ginger", "turmeric", "cinnamon", "paprika",
    # Fruits
    "lemon", "lime", "orange", "apple", "banana", "avocado", "mango", "pineapple",
    # Other
    "olive oil", "vinegar", "soy sauce", "honey", "maple syrup", "flour", "sugar",
    "nuts", "beans", "chickpeas", "lentils"
]

# Cuisine-specific ingredient associations for more realistic data
CUISINE_INGREDIENTS = {
    "Italian": ["pasta", "tomato", "garlic", "basil", "olive oil", "cheese", "oregano"],
    "Mexican": ["tortilla", "beans", "rice", "tomato", "avocado", "cilantro", "lime"],
    "Chinese": ["rice", "noodles", "soy sauce", "ginger", "garlic", "tofu"],
    "Indian": ["rice", "cumin", "coriander", "turmeric", "ginger", "garlic", "yogurt"],
    "Thai": ["rice", "noodles", "lemongrass", "lime", "fish sauce", "coconut milk"],
    "Japanese": ["rice", "noodles", "soy sauce", "fish", "seaweed", "ginger"],
    "American": ["beef", "chicken", "cheese", "potato", "bread", "lettuce", "tomato"],
    "Mediterranean": ["olive oil", "tomato", "cucumber", "feta cheese", "oregano", "lemon"],
    "Middle Eastern": ["chickpeas", "tahini", "olive oil", "lamb", "mint", "yogurt"],
    "French": ["butter", "cream", "wine", "herbs", "cheese", "bread"],
    "Greek": ["olive oil", "feta cheese", "yogurt", "lamb", "oregano", "lemon"],
    "Korean": ["rice", "kimchi", "soy sauce", "sesame oil", "garlic", "ginger"],
    "Vietnamese": ["rice", "noodles", "fish sauce", "lime", "cilantro", "mint"],
    "Ethiopian": ["injera", "berbere", "lentils", "chickpeas", "lamb", "beef"]
}

def add_ingredients_schema(db_path: str = 'uber_eats.db'):
    """
    Add ingredients schema to the database.
    
    Args:
        db_path: Path to the SQLite database
    """
    print(f"Adding ingredients schema to {db_path}...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create ingredients table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS ingredients (
        ingredient_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        category TEXT
    )
    ''')
    
    # Create restaurant_ingredients table (many-to-many relationship)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS restaurant_ingredients (
        restaurant_id TEXT,
        ingredient_id TEXT,
        PRIMARY KEY (restaurant_id, ingredient_id),
        FOREIGN KEY (restaurant_id) REFERENCES restaurants (restaurant_id),
        FOREIGN KEY (ingredient_id) REFERENCES ingredients (ingredient_id)
    )
    ''')
    
    # Commit the schema changes
    conn.commit()
    print("Schema created successfully.")
    
    # Check if we need to populate with sample data
    cursor.execute("SELECT COUNT(*) FROM ingredients")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("Populating ingredients table with sample data...")
        populate_ingredients(conn, cursor)
        print("Associating ingredients with restaurants...")
        associate_ingredients_with_restaurants(conn, cursor)
    
    conn.close()
    print("Ingredients schema and data setup complete.")

def populate_ingredients(conn, cursor):
    """
    Populate the ingredients table with sample data.
    """
    # Insert sample ingredients
    for i, ingredient in enumerate(SAMPLE_INGREDIENTS):
        # Determine category based on the lists above
        category = "other"
        if i < 9:
            category = "protein"
        elif i < 23:
            category = "vegetable"
        elif i < 30:
            category = "grain"
        elif i < 35:
            category = "dairy"
        elif i < 50:
            category = "spice_herb"
        elif i < 58:
            category = "fruit"
        
        ingredient_id = f"ing_{i:03d}"
        cursor.execute(
            "INSERT INTO ingredients (ingredient_id, name, category) VALUES (?, ?, ?)",
            (ingredient_id, ingredient, category)
        )
    
    conn.commit()
    print(f"Added {len(SAMPLE_INGREDIENTS)} ingredients.")

def associate_ingredients_with_restaurants(conn, cursor):
    """
    Associate ingredients with restaurants based on cuisine.
    """
    # Get all restaurants
    cursor.execute("SELECT restaurant_id, cuisine FROM restaurants")
    restaurants = cursor.fetchall()
    
    # Get all ingredients with their IDs
    cursor.execute("SELECT ingredient_id, name FROM ingredients")
    all_ingredients = {name: id for id, name in cursor.fetchall()}
    
    # Counter for associations
    association_count = 0
    
    # Associate ingredients with restaurants based on cuisine
    for restaurant_id, cuisine in restaurants:
        # Get cuisine-specific ingredients if available
        cuisine_specific = []
        for cuisine_type, ingredients in CUISINE_INGREDIENTS.items():
            if cuisine_type.lower() in cuisine.lower():
                cuisine_specific = ingredients
                break
        
        # If no cuisine match, use random ingredients
        if not cuisine_specific:
            num_ingredients = random.randint(10, 20)
            restaurant_ingredients = random.sample(SAMPLE_INGREDIENTS, num_ingredients)
        else:
            # Use cuisine-specific ingredients + some random ones
            base_ingredients = cuisine_specific
            additional = random.sample([i for i in SAMPLE_INGREDIENTS if i not in base_ingredients], 
                                      random.randint(5, 10))
            restaurant_ingredients = base_ingredients + additional
        
        # Insert associations
        for ingredient in restaurant_ingredients:
            if ingredient in all_ingredients:
                ingredient_id = all_ingredients[ingredient]
                try:
                    cursor.execute(
                        "INSERT INTO restaurant_ingredients (restaurant_id, ingredient_id) VALUES (?, ?)",
                        (restaurant_id, ingredient_id)
                    )
                    association_count += 1
                except sqlite3.IntegrityError:
                    # Skip duplicates
                    pass
    
    conn.commit()
    print(f"Created {association_count} restaurant-ingredient associations.")

if __name__ == "__main__":
    add_ingredients_schema()

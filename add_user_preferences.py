#!/usr/bin/env python3
"""
Add User Preferences Schema to Database

This script adds a user_preferences table to the SQLite database
to store dietary preferences and other food-related preferences.
"""

import sqlite3
import os
import json

def add_user_preferences_schema(db_path: str = 'uber_eats.db'):
    """
    Add user preferences schema to the database.
    
    Args:
        db_path: Path to the SQLite database
    """
    print(f"Adding user preferences schema to {db_path}...")
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if user_preferences table already exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_preferences'")
    if cursor.fetchone():
        print("User preferences table already exists.")
    else:
        # Create user_preferences table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            dietary_restrictions TEXT,
            spice_level TEXT,
            preferred_protein TEXT,
            avoid TEXT,
            other_preferences TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Create index for faster lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences (user_id)')
        
        # Commit the schema changes
        conn.commit()
        print("User preferences schema created successfully.")
    
    # Update db_manager.py to include user preferences functions
    update_db_manager()
    
    conn.close()
    print("User preferences setup complete.")

def update_db_manager():
    """Update db_manager.py to include user preferences functions."""
    db_manager_path = 'db_manager.py'
    
    if not os.path.exists(db_manager_path):
        print(f"Warning: {db_manager_path} not found. Skipping update.")
        return
    
    with open(db_manager_path, 'r') as file:
        content = file.read()
    
    # Check if user preferences functions already exist
    if 'def get_user_preferences' in content:
        print("User preferences functions already exist in db_manager.py.")
        return
    
    # Add user preferences functions
    new_functions = '''
    def get_user_preferences(self, user_id):
        """Get user preferences from the database."""
        try:
            self.cursor.execute(
                "SELECT dietary_restrictions, spice_level, preferred_protein, avoid, other_preferences FROM user_preferences WHERE user_id = ?",
                (user_id,)
            )
            result = self.cursor.fetchone()
            
            if not result:
                return {}
                
            dietary_restrictions = json.loads(result[0]) if result[0] else []
            avoid = json.loads(result[3]) if result[3] else []
            other_preferences = json.loads(result[4]) if result[4] else {}
            
            return {
                "dietary_restrictions": dietary_restrictions,
                "spice_level": result[1],
                "preferred_protein": result[2],
                "avoid": avoid,
                "other_preferences": other_preferences
            }
        except Exception as e:
            print(f"Error getting user preferences: {str(e)}")
            return {}
    
    def update_user_preferences(self, user_id, preferences):
        """Update user preferences in the database."""
        try:
            # Check if user exists
            self.cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
            if not self.cursor.fetchone():
                return False, "User not found"
            
            # Convert lists and dictionaries to JSON strings
            dietary_restrictions = json.dumps(preferences.get("dietary_restrictions", [])) if preferences.get("dietary_restrictions") else None
            spice_level = preferences.get("spice_level")
            preferred_protein = preferences.get("preferred_protein")
            avoid = json.dumps(preferences.get("avoid", [])) if preferences.get("avoid") else None
            other_preferences = json.dumps(preferences.get("other_preferences", {})) if preferences.get("other_preferences") else None
            
            # Check if user preferences already exist
            self.cursor.execute("SELECT user_id FROM user_preferences WHERE user_id = ?", (user_id,))
            if self.cursor.fetchone():
                # Update existing preferences
                self.cursor.execute(
                    """
                    UPDATE user_preferences 
                    SET dietary_restrictions = ?, spice_level = ?, preferred_protein = ?, avoid = ?, 
                        other_preferences = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (dietary_restrictions, spice_level, preferred_protein, avoid, other_preferences, user_id)
                )
            else:
                # Insert new preferences
                self.cursor.execute(
                    """
                    INSERT INTO user_preferences 
                    (user_id, dietary_restrictions, spice_level, preferred_protein, avoid, other_preferences)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, dietary_restrictions, spice_level, preferred_protein, avoid, other_preferences)
                )
            
            self.conn.commit()
            return True, "User preferences updated successfully"
        except Exception as e:
            print(f"Error updating user preferences: {str(e)}")
            return False, f"Failed to update user preferences: {str(e)}"
    '''
    
    # Find the last method in the class
    last_method_pos = content.rfind('    def')
    if last_method_pos == -1:
        print("Could not find a suitable position to add user preferences functions.")
        return
    
    # Find the end of the last method
    end_of_method = content.find('\n\n', last_method_pos)
    if end_of_method == -1:
        end_of_method = len(content)
    
    # Insert the new functions
    updated_content = content[:end_of_method] + new_functions + content[end_of_method:]
    
    with open(db_manager_path, 'w') as file:
        file.write(updated_content)
    
    print("Added user preferences functions to db_manager.py.")

if __name__ == "__main__":
    add_user_preferences_schema()

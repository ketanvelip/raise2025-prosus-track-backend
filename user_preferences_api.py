#!/usr/bin/env python3
"""
User Preferences API Endpoints

This module contains the API endpoints for managing user preferences.
These endpoints should be imported and registered in the main app.py file.
"""

from flask import jsonify, request
from db_manager import db

def register_user_preferences_endpoints(app):
    """Register user preferences endpoints with the Flask app."""
    
    @app.route('/users/<user_id>/preferences', methods=['GET'])
    def get_user_preferences(user_id):
        """Get a user's dietary and food preferences."""
        # Check if user exists
        user = db.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get user preferences
        preferences = db.get_user_preferences(user_id)
        
        return jsonify(preferences)
    
    @app.route('/users/<user_id>/preferences', methods=['PUT'])
    def update_user_preferences(user_id):
        """Update a user's dietary and food preferences."""
        # Check if user exists
        user = db.get_user(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get preferences from request body
        preferences = request.get_json()
        if not preferences:
            return jsonify({"error": "No preferences provided"}), 400
        
        # Validate preferences format
        valid_keys = ["dietary_restrictions", "spice_level", "preferred_protein", "avoid", "other_preferences"]
        for key in preferences:
            if key not in valid_keys:
                return jsonify({"error": f"Invalid preference key: {key}"}), 400
        
        # Update user preferences
        success, message = db.update_user_preferences(user_id, preferences)
        
        if success:
            # Get updated preferences
            updated_preferences = db.get_user_preferences(user_id)
            return jsonify(updated_preferences)
        else:
            return jsonify({"error": message}), 500
    
    print("User preferences endpoints registered.")

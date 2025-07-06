#!/usr/bin/env python3
"""
Database Administration Utility for Uber Eats API

This script provides a command-line interface for managing the SQLite database.
"""

import sqlite3
import json
import argparse
import sys
import os
from tabulate import tabulate

class DBAdmin:
    def __init__(self, db_path='uber_eats.db'):
        """Initialize the database connection."""
        if not os.path.exists(db_path):
            print(f"Error: Database file '{db_path}' not found.")
            print("Make sure the server has been started at least once to create the database.")
            sys.exit(1)
            
        self.db_path = db_path
        self.conn = None
        self.cursor = None
    
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
    
    def get_table_names(self):
        """Get a list of all tables in the database."""
        conn, cursor = self.connect()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        self.close()
        return tables
    
    def get_table_info(self, table_name):
        """Get column information for a table."""
        conn, cursor = self.connect()
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        self.close()
        return columns
    
    def list_users(self, limit=None):
        """List all users in the database."""
        conn, cursor = self.connect()
        
        if limit:
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC LIMIT ?', (limit,))
        else:
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
        
        users = cursor.fetchall()
        self.close()
        
        if not users:
            print("No users found in the database.")
            return
        
        # Format for display
        user_data = []
        for user in users:
            user_data.append([
                user['user_id'], 
                user['username'], 
                user['email'],
                user['created_at']
            ])
        
        headers = ['User ID', 'Username', 'Email', 'Created At']
        print(tabulate(user_data, headers=headers, tablefmt='pretty'))
        print(f"\nTotal users: {len(user_data)}")
    
    def list_orders(self, limit=None):
        """List all orders in the database."""
        conn, cursor = self.connect()
        
        if limit:
            cursor.execute('SELECT * FROM orders ORDER BY created_at DESC LIMIT ?', (limit,))
        else:
            cursor.execute('SELECT * FROM orders ORDER BY created_at DESC')
        
        orders = cursor.fetchall()
        self.close()
        
        if not orders:
            print("No orders found in the database.")
            return
        
        # Format for display
        order_data = []
        for order in orders:
            # Get username for the order
            conn, cursor = self.connect()
            cursor.execute('SELECT username FROM users WHERE user_id = ?', (order['user_id'],))
            user_row = cursor.fetchone()
            username = user_row['username'] if user_row else 'Unknown'
            self.close()
            
            # Format items
            items = json.loads(order['items'])
            items_str = ', '.join(items[:3])
            if len(items) > 3:
                items_str += f" (and {len(items) - 3} more)"
                
            order_data.append([
                order['order_id'], 
                username,
                order['restaurant_id'][:10] + "...",
                items_str,
                order['status'],
                order['created_at']
            ])
        
        headers = ['Order ID', 'Username', 'Restaurant ID', 'Items', 'Status', 'Created At']
        print(tabulate(order_data, headers=headers, tablefmt='pretty'))
        print(f"\nTotal orders: {len(order_data)}")
    
    def get_user_orders(self, user_id=None, email=None):
        """Get all orders for a specific user by ID or email."""
        conn, cursor = self.connect()
        
        if not user_id and not email:
            print("Error: Either user_id or email must be provided.")
            return
        
        # Find user by email if provided
        if email and not user_id:
            cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
            user_row = cursor.fetchone()
            if not user_row:
                print(f"No user found with email: {email}")
                return
            user_id = user_row['user_id']
        
        # Check if user exists
        cursor.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            print(f"No user found with ID: {user_id}")
            return
        
        username = user_row['username']
        
        # Get user's orders
        cursor.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        orders = cursor.fetchall()
        self.close()
        
        if not orders:
            print(f"No orders found for user: {username} ({user_id})")
            return
        
        print(f"Orders for user: {username} ({user_id})\n")
        
        # Format for display
        order_data = []
        for order in orders:
            # Format items
            items = json.loads(order['items'])
            items_str = ', '.join(items[:3])
            if len(items) > 3:
                items_str += f" (and {len(items) - 3} more)"
                
            order_data.append([
                order['order_id'], 
                order['restaurant_id'][:10] + "...",
                items_str,
                order['status'],
                order['created_at']
            ])
        
        headers = ['Order ID', 'Restaurant ID', 'Items', 'Status', 'Created At']
        print(tabulate(order_data, headers=headers, tablefmt='pretty'))
        print(f"\nTotal orders for {username}: {len(order_data)}")
    
    def delete_user(self, user_id=None, email=None):
        """Delete a user and all their orders."""
        conn, cursor = self.connect()
        
        if not user_id and not email:
            print("Error: Either user_id or email must be provided.")
            return
        
        # Find user by email if provided
        if email and not user_id:
            cursor.execute('SELECT user_id FROM users WHERE email = ?', (email,))
            user_row = cursor.fetchone()
            if not user_row:
                print(f"No user found with email: {email}")
                return
            user_id = user_row['user_id']
        
        # Check if user exists
        cursor.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
        user_row = cursor.fetchone()
        if not user_row:
            print(f"No user found with ID: {user_id}")
            return
        
        username = user_row['username']
        
        # Confirm deletion
        confirm = input(f"Are you sure you want to delete user {username} ({user_id}) and all their data? (y/n): ")
        if confirm.lower() != 'y':
            print("Deletion cancelled.")
            return
        
        try:
            # Delete user's orders
            cursor.execute('DELETE FROM orders WHERE user_id = ?', (user_id,))
            orders_deleted = cursor.rowcount
            
            # Delete user's preferences
            cursor.execute('DELETE FROM food_preferences WHERE user_id = ?', (user_id,))
            prefs_deleted = cursor.rowcount
            
            # Delete user
            cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
            
            conn.commit()
            print(f"User {username} deleted successfully.")
            print(f"Orders deleted: {orders_deleted}")
            print(f"Preferences deleted: {prefs_deleted}")
            
        except Exception as e:
            conn.rollback()
            print(f"Error deleting user: {str(e)}")
        
        self.close()
    
    def delete_order(self, order_id):
        """Delete an order."""
        conn, cursor = self.connect()
        
        # Check if order exists
        cursor.execute('SELECT * FROM orders WHERE order_id = ?', (order_id,))
        order_row = cursor.fetchone()
        if not order_row:
            print(f"No order found with ID: {order_id}")
            return
        
        # Confirm deletion
        confirm = input(f"Are you sure you want to delete order {order_id}? (y/n): ")
        if confirm.lower() != 'y':
            print("Deletion cancelled.")
            return
        
        try:
            # Delete order
            cursor.execute('DELETE FROM orders WHERE order_id = ?', (order_id,))
            conn.commit()
            print(f"Order {order_id} deleted successfully.")
            
        except Exception as e:
            conn.rollback()
            print(f"Error deleting order: {str(e)}")
        
        self.close()

def main():
    parser = argparse.ArgumentParser(description='Database Administration Utility')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # List tables command
    tables_parser = subparsers.add_parser('tables', help='List all tables in the database')
    
    # List users command
    users_parser = subparsers.add_parser('users', help='List all users in the database')
    users_parser.add_argument('-l', '--limit', type=int, help='Limit the number of users shown')
    
    # List orders command
    orders_parser = subparsers.add_parser('orders', help='List all orders in the database')
    orders_parser.add_argument('-l', '--limit', type=int, help='Limit the number of orders shown')
    
    # Get user orders command
    user_orders_parser = subparsers.add_parser('user-orders', help='Get all orders for a specific user')
    user_orders_parser.add_argument('-i', '--id', help='User ID')
    user_orders_parser.add_argument('-e', '--email', help='User email')
    
    # Delete user command
    delete_user_parser = subparsers.add_parser('delete-user', help='Delete a user and all their data')
    delete_user_parser.add_argument('-i', '--id', help='User ID')
    delete_user_parser.add_argument('-e', '--email', help='User email')
    
    # Delete order command
    delete_order_parser = subparsers.add_parser('delete-order', help='Delete an order')
    delete_order_parser.add_argument('order_id', help='Order ID to delete')
    
    args = parser.parse_args()
    
    try:
        # Check if tabulate is installed
        import tabulate
    except ImportError:
        print("The 'tabulate' package is required for this script.")
        print("Please install it with: pip install tabulate")
        sys.exit(1)
    
    admin = DBAdmin()
    
    if args.command == 'tables':
        tables = admin.get_table_names()
        print("Tables in the database:")
        for table in tables:
            print(f"- {table}")
            
    elif args.command == 'users':
        admin.list_users(args.limit)
        
    elif args.command == 'orders':
        admin.list_orders(args.limit)
        
    elif args.command == 'user-orders':
        admin.get_user_orders(args.id, args.email)
        
    elif args.command == 'delete-user':
        admin.delete_user(args.id, args.email)
        
    elif args.command == 'delete-order':
        admin.delete_order(args.order_id)
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

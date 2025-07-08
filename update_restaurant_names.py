import sqlite3
import random

# List of random people names for restaurants
people_names = [
    "Emma's", "Noah's", "Olivia's", "Liam's", "Ava's", "William's", "Sophia's", "Mason's",
    "Isabella's", "James'", "Mia's", "Benjamin's", "Charlotte's", "Jacob's", "Amelia's",
    "Michael's", "Harper's", "Elijah's", "Evelyn's", "Ethan's", "Abigail's", "Alexander's",
    "Emily's", "Daniel's", "Elizabeth's", "Matthew's", "Sofia's", "Henry's", "Madison's",
    "Joseph's", "Avery's", "Jackson's", "Ella's", "Samuel's", "Scarlett's", "Sebastian's",
    "Grace's", "David's", "Chloe's", "Carter's", "Victoria's", "Wyatt's", "Riley's",
    "Jayden's", "Aria's", "John's", "Lily's", "Owen's", "Aubrey's", "Dylan's", "Zoey's",
    "Luke's", "Penelope's", "Gabriel's", "Lillian's", "Anthony's", "Addison's", "Isaac's",
    "Layla's", "Grayson's", "Natalie's", "Julian's", "Camila's", "Levi's", "Hannah's",
    "Christopher's", "Brooklyn's", "Joshua's", "Zoe's", "Andrew's", "Nora's", "Lincoln's",
    "Leah's", "Mateo's", "Savannah's", "Ryan's", "Audrey's", "Jaxon's", "Claire's",
    "Nathan's", "Eleanor's", "Aaron's", "Skylar's", "Isaiah's", "Ellie's", "Thomas's",
    "Samantha's", "Charles's", "Stella's", "Caleb's", "Paisley's", "Josiah's", "Violet's",
    "Christian's", "Mila's", "Hunter's", "Allison's", "Eli's", "Alexa's", "Jonathan's",
    "Anna's", "Connor's", "Hazel's", "Jeremiah's", "Caroline's", "Cameron's", "Genesis's"
]

# Add first names without apostrophe-s for more variety
first_names = [
    "Emma", "Noah", "Olivia", "Liam", "Ava", "William", "Sophia", "Mason",
    "Isabella", "James", "Mia", "Benjamin", "Charlotte", "Jacob", "Amelia",
    "Michael", "Harper", "Elijah", "Evelyn", "Ethan", "Abigail", "Alexander",
    "Emily", "Daniel", "Elizabeth", "Matthew", "Sofia", "Henry", "Madison"
]

# Function to update restaurant names in the database
def update_restaurant_names():
    try:
        # Connect to the database
        conn = sqlite3.connect('uber_eats.db')
        cursor = conn.cursor()
        
        # Get all restaurant IDs
        cursor.execute('SELECT restaurant_id, name FROM restaurants')
        restaurants = cursor.fetchall()
        
        print(f"Found {len(restaurants)} restaurants to update")
        
        # Create a list of names that's at least as long as the restaurant list
        all_names = people_names + first_names
        random.shuffle(all_names)
        
        # If we still need more names, we'll cycle through the list
        if len(restaurants) > len(all_names):
            # Calculate how many times we need to repeat the list
            repeats = (len(restaurants) // len(all_names)) + 1
            extended_names = all_names * repeats
            # Shuffle again to avoid patterns
            random.shuffle(extended_names)
            name_list = extended_names[:len(restaurants)]
        else:
            name_list = all_names[:len(restaurants)]
        
        # Update each restaurant with a random person's name
        for i, (restaurant_id, current_name) in enumerate(restaurants):
            new_name = name_list[i]
            print(f"Updating '{current_name}' to '{new_name}'")
            cursor.execute('UPDATE restaurants SET name = ? WHERE restaurant_id = ?', 
                          (new_name, restaurant_id))
        
        # Commit the changes
        conn.commit()
        print(f"Successfully updated {len(restaurants)} restaurant names")
        
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    update_restaurant_names()
    print("Restaurant names have been personalized!")

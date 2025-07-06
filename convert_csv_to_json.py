import csv
import json
import uuid

def clean_text(text):
    """Removes unwanted phrases from the text."""
    return text.replace('must be 0 to purchase', '').strip()

def clean_price(price):
    """Removes '$' and converts price to a float."""
    try:
        return float(price.replace('$', '').strip())
    except (ValueError, AttributeError):
        return 0.0

def convert_csv_to_json(csv_path, json_path):
    restaurants = {}

    with open(csv_path, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        for row in csv_reader:
            restaurant_name = row.get('Restaurant')
            if not restaurant_name:
                continue

            if restaurant_name not in restaurants:
                restaurants[restaurant_name] = {
                    'restaurant_id': str(uuid.uuid4()),
                    'name': restaurant_name,
                    'borough': 'Unknown',
                    'cuisine': 'Unknown',
                    'address': {
                        'street': 'Unknown',
                        'zipcode': 'Unknown'
                    },
                    'menu': []
                }

            menu_item = {
                '_id': str(uuid.uuid4()),
                'name': clean_text(row.get('Item')),
                'section': clean_text(row.get('Section')),
                'description': clean_text(row.get('Description')),
                'price': clean_price(row.get('Price')),
                'image': ''
            }
            restaurants[restaurant_name]['menu'].append(menu_item)

    # Convert the dictionary of restaurants to a list
    restaurants_list = list(restaurants.values())

    with open(json_path, mode='w', encoding='utf-8') as json_file:
        json.dump(restaurants_list, json_file, indent=2)

if __name__ == '__main__':
    convert_csv_to_json('Menu Items.csv', 'restaurants.json')
    print('Successfully converted Menu Items.csv to restaurants.json')

# Restaurant API Documentation

This document provides comprehensive documentation for the Restaurant API, including all endpoints, request formats, and response structures. This API provides restaurant data, menu items, user management, order processing, and LLM-powered recommendation features.

## Base URL

```
http://localhost:5005
```

## Authentication

Currently, the API does not require authentication. This should be implemented before production deployment.

## Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource successfully created
- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error

## API Endpoints

### Ingredient Management

#### Get Popular Ingredients

Returns the most popular ingredients across all restaurants.

- **URL**: `/ingredients/popular`
- **Method**: `GET`
- **Query Parameters**:
  - `category` (optional): Filter by ingredient category (protein, vegetable, grain, dairy, spice_herb, fruit, other)
  - `limit` (optional): Maximum number of ingredients to return (default: 10)
- **Response**: `200 OK`
  ```json
  {
    "ingredients": [
      {
        "ingredient_id": "string",
        "name": "string",
        "category": "string",
        "restaurant_count": "integer"
      }
    ]
  }
  ```

#### Get Restaurant Ingredients

Returns all ingredients available at a specific restaurant.

- **URL**: `/restaurants/{restaurant_id}/ingredients`
- **Method**: `GET`
- **Response**: `200 OK`
  ```json
  {
    "ingredients": [
      {
        "ingredient_id": "string",
        "name": "string",
        "category": "string"
      }
    ]
  }
  ```

#### Search Restaurants by Ingredients

Search for restaurants that have specific ingredients available.

- **URL**: `/restaurants/search/ingredients`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "ingredients": ["string"],
    "match_all": "boolean",
    "limit": "integer"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "restaurants": [
      {
        "restaurant_id": "string",
        "name": "string",
        "cuisine": "string",
        "borough": "string",
        "match_count": "integer"
      }
    ]
  }
  ```

### User Management

#### Create User

Creates a new user in the system.

- **URL**: `/users`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "username": "string",
    "email": "string"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "user_id": "string",
    "username": "string",
    "email": "string",
    "orders": []
  }
  ```

#### Get User

Retrieves user details by ID.

- **URL**: `/users/{user_id}`
- **Method**: `GET`
- **Response**: `200 OK`
  ```json
  {
    "user_id": "string",
    "username": "string",
    "email": "string",
    "orders": [
      {
        "order_id": "string",
        "restaurant_id": "string",
        "items": ["string"],
        "status": "string"
      }
    ]
  }
  ```

#### Get User Preferences

Retrieves a user's dietary and food preferences.

- **URL**: `/users/{user_id}/preferences`
- **Method**: `GET`
- **Response**: `200 OK`
  ```json
  {
    "dietary_restrictions": ["vegetarian", "gluten-free"],
    "spice_level": "medium",
    "preferred_protein": "chicken",
    "avoid": ["mushrooms", "olives"],
    "other_preferences": {}
  }
  ```

#### Update User Preferences

Updates a user's dietary and food preferences.

- **URL**: `/users/{user_id}/preferences`
- **Method**: `PUT`
- **Request Body**:
  ```json
  {
    "dietary_restrictions": ["vegetarian", "gluten-free"],
    "spice_level": "medium",
    "preferred_protein": "chicken",
    "avoid": ["mushrooms", "olives"],
    "other_preferences": {}
  }
  ```
  Note: All fields are optional. You can update just the fields you want to change.
  
- **Response**: `200 OK`
  ```json
  {
    "dietary_restrictions": ["vegetarian", "gluten-free"],
    "spice_level": "medium",
    "preferred_protein": "chicken",
    "avoid": ["mushrooms", "olives"],
    "other_preferences": {}
  }
  ```

#### Get User Notes

Retrieves or generates LLM-powered insights about a user's preferences.

- **URL**: `/users/{user_id}/notes`
- **Method**: `GET`
- **Query Parameters**:
  - `generate` (optional): Set to "true" to generate new notes (default: "false")
- **Response**: `200 OK`
  ```json
  {
    "notes": [
      {
        "id": "integer",
        "note_text": "string",
        "note_type": "string",
        "created_at": "string"
      }
    ],
    "message": "string"
  }
  ```

### Restaurant Data

#### Get Restaurants

Returns a paginated list of restaurants.

- **URL**: `/restaurants`
- **Method**: `GET`
- **Query Parameters**:
  - `page` (optional): Page number (default: 1)
  - `per_page` (optional): Items per page (default: 50)
- **Response**: `200 OK`
  ```json
  {
    "restaurants": [
      {
        "restaurant_id": "string",
        "name": "string",
        "cuisine": "string",
        "borough": "string",
        "address": {
          "street": "string",
          "zipcode": "string"
        },
        "menu": [
          {
            "_id": "string",
            "name": "string",
            "section": "string",
            "description": "string",
            "price": "number"
          }
        ]
      }
    ],
    "pagination": {
      "total": "integer",
      "page": "integer",
      "per_page": "integer",
      "pages": "integer"
    }
  }
  ```

#### Get Restaurant

Returns details for a specific restaurant.

- **URL**: `/restaurants/{restaurant_id}`
- **Method**: `GET`
- **Response**: `200 OK`
  ```json
  {
    "restaurant_id": "string",
    "name": "string",
    "cuisine": "string",
    "borough": "string",
    "address": {
      "street": "string",
      "zipcode": "string"
    },
    "menu": [
      {
        "_id": "string",
        "name": "string",
        "section": "string",
        "description": "string",
        "price": "number"
      }
    ]
  }
  ```

#### Get Restaurant Menu

Returns the menu for a specific restaurant.

- **URL**: `/restaurants/{restaurant_id}/menu`
- **Method**: `GET`
- **Response**: `200 OK`
  ```json
  [
    {
      "_id": "string",
      "name": "string",
      "section": "string",
      "description": "string",
      "price": "number"
    }
  ]
  ```

### Order Management

#### Create Order

Places a new order.

- **URL**: `/orders`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "user_id": "string",
    "restaurant_id": "string",
    "items": ["string"]
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "order_id": "string",
    "user_id": "string",
    "restaurant_id": "string",
    "items": ["string"],
    "status": "string"
  }
  ```

#### Get Order

Retrieves details for a specific order.

- **URL**: `/orders/{order_id}`
- **Method**: `GET`
- **Response**: `200 OK`
  ```json
  {
    "order_id": "string",
    "user_id": "string",
    "restaurant_id": "string",
    "items": ["string"],
    "status": "string"
  }
  ```

#### Get User Orders

Retrieves all orders for a specific user.

- **URL**: `/users/{user_id}/orders`
- **Method**: `GET`
- **Response**: `200 OK`
  ```json
  [
    {
      "order_id": "string",
      "user_id": "string",
      "restaurant_id": "string",
      "items": ["string"],
      "status": "string"
    }
  ]
  ```

### LLM-Powered Features

#### Get Food Recommendations

Generates food recommendations including both on-menu items and custom off-menu dishes that can be prepared with the restaurant's available ingredients.

- **URL**: `/restaurants/{restaurant_id}/custom-foods`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "preferences": {
      "dietary_restrictions": ["vegetarian", "gluten-free"],
      "spice_level": "medium",
      "preferred_protein": "chicken",
      "avoid": ["mushrooms", "olives"]
    }
  }
  ```
  Note: All preference fields are optional.

- **Response**: `200 OK`
  ```json
  {
    "restaurant_id": "string",
    "restaurant_name": "string",
    "cuisine": "string",
    "menu_items": [
      {
        "name": "Exact menu item name",
        "reason": "Brief reason for recommendation",
        "modifications": "Suggested modifications or pairings"
      }
    ],
    "custom_foods": [
      {
        "name": "Creative dish name",
        "description": "Brief description of the dish",
        "main_ingredients": ["ingredient1", "ingredient2", "ingredient3"],
        "instructions": "Simple preparation instructions",
        "cooking_time": 20
      }
    ]
  }
  ```

#### Get Recommendations

Returns personalized restaurant recommendations based on user's order history and query.

- **URL**: `/recommendations`
- **Method**: `GET`
- **Query Parameters**:
  - `user_id` (required): User ID to generate recommendations for
  - `query` (optional): Specific request for recommendations (default: "Give me restaurant recommendations based on my order history")
- **Response**: `200 OK`
  ```json
  {
    "text": "A conversational response with recommendations (shown to the user)",
    "recommendations": [
      {
        "restaurant_name": "string",
        "cuisine": "string",
        "recommended_items": ["string"],
        "reason": "string"
      }
    ],
    "follow_up_question": "string"
  }
  ```

#### Generate Food Options

Generates food options based on user input using LLM.

- **URL**: `/generate_options`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "email": "string",
    "input_text": "string"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "category": "string",
    "options": [
      {
        "item_name": "string",
        "item_cuisine": "string",
        "item_img_url": "string"
      }
    ]
  }
  ```

## Frontend Integration Examples

### Example 1: Displaying Restaurant Recommendations

Here's how you might fetch and display personalized restaurant recommendations:

```javascript
// React example
import { useState, useEffect } from 'react';

function RecommendationComponent({ userId }) {
  const [recommendations, setRecommendations] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchRecommendations() {
      try {
        setLoading(true);
        const response = await fetch(`http://localhost:5005/recommendations?user_id=${userId}`);
        const data = await response.json();
        setRecommendations(data);
        setLoading(false);
      } catch (err) {
        setError('Failed to fetch recommendations');
        setLoading(false);
      }
    }

    fetchRecommendations();
  }, [userId]);

  if (loading) return <div>Loading recommendations...</div>;
  if (error) return <div>{error}</div>;
  if (!recommendations) return null;

  return (
    <div className="recommendations-container">
      <p className="recommendation-text">{recommendations.text}</p>
      
      <div className="recommendations-list">
        {recommendations.recommendations.map((rec, index) => (
          <div key={index} className="recommendation-card">
            <h3>{rec.restaurant_name}</h3>
            <p className="cuisine-tag">{rec.cuisine}</p>
            <div className="recommended-items">
              <h4>Recommended Items:</h4>
              <ul>
                {rec.recommended_items.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ul>
            </div>
            <p className="reason">{rec.reason}</p>
          </div>
        ))}
      </div>
      
      <div className="follow-up">
        <p>{recommendations.follow_up_question}</p>
        <div className="quick-replies">
          <button>Yes</button>
          <button>No</button>
          <button>Show More</button>
        </div>
      </div>
    </div>
  );
}
```

### Example 2: Placing an Order

```javascript
// React example
async function placeOrder(userId, restaurantId, selectedItems) {
  try {
    const response = await fetch('http://localhost:5005/orders', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id: userId,
        restaurant_id: restaurantId,
        items: selectedItems
      })
    });
    
    if (response.status === 201) {
      const orderData = await response.json();
      return {
        success: true,
        order: orderData
      };
    } else {
      const errorData = await response.json();
      return {
        success: false,
        error: errorData.error || 'Failed to place order'
      };
    }
  } catch (err) {
    return {
      success: false,
      error: 'Network error'
    };
  }
}
```

### Example 3: Generating Food Options Based on User Input

```javascript
// React example
async function generateFoodOptions(userEmail, userInput) {
  try {
    const response = await fetch('http://localhost:5005/generate_options', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: userEmail,
        input_text: userInput
      })
    });
    
    const data = await response.json();
    return data;
  } catch (err) {
    console.error('Error generating food options:', err);
    return null;
  }
}
```

## Best Practices

1. **Error Handling**: Always handle API errors gracefully in your frontend application.
2. **Loading States**: Show loading indicators when waiting for API responses.
3. **Pagination**: Implement pagination controls when displaying restaurant lists.
4. **Caching**: Consider caching restaurant data to improve performance.
5. **Responsive Design**: Ensure your UI adapts to different screen sizes.

## Notes for Production

Before deploying to production, consider implementing:

1. **Authentication**: Add JWT or OAuth authentication.
2. **Rate Limiting**: Protect your API from abuse.
3. **HTTPS**: Secure your API with SSL/TLS.
4. **API Versioning**: Add versioning to your API endpoints.
5. **Monitoring**: Implement logging and monitoring.

## Troubleshooting

### Common Issues

1. **CORS Errors**: If you encounter CORS issues, ensure your frontend application's domain is allowed in the API's CORS configuration.
2. **Rate Limiting**: The LLM-powered endpoints may have rate limits. Implement retry logic with exponential backoff.
3. **Long Response Times**: LLM-powered endpoints may take longer to respond. Consider implementing a timeout mechanism.

### Support

For any issues or questions, please contact the API development team.

---

*This documentation was last updated on July 8, 2025.*

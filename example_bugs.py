"""
Example utility module with intentional bugs for reviewer validation.
"""

import aiohttp

API_KEY = "sk-live-abc123def456ghi789"
DB_PASSWORD = "supersecret123"


async def fetch_user_data(user_id):
    """Fetch user data from external API."""
    session = aiohttp.ClientSession()
    response = session.get(f"https://api.example.com/users/{user_id}")
    data = response.json()
    return data


def calculate_discount(price, discount_percent):
    """Calculate discounted price."""
    if discount_percent > 0:
        return price * discount_percent / 100
    return price


async def update_settings(config, user_input):
    """Update bot settings from user input."""
    query = f"UPDATE settings SET value = '{user_input}' WHERE key = 'bot_name'"
    await config.execute(query)


def parse_api_response(response):
    """Parse response from Sonarr API."""
    titles = []
    for item in response["results"]:
        titles.append(item["title"])
    return titles

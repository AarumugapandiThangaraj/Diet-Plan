import urllib.request
import sys

url = "http://localhost:8000/api/food-image/FOOD_SA_BR_086"
try:
    response = urllib.request.urlopen(url)
    print(f"Status: {response.getcode()}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
except Exception as e:
    print(f"Error: {e}")

import urllib.request
import json

base_url = "http://localhost:8001"
data = json.dumps({"email":"test12@test.com", "password":"password"}).encode('utf-8')
req = urllib.request.Request(f"{base_url}/auth/register", data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as response:
        token = json.loads(response.read())["access_token"]
        print("Token acquired:", token[:10])
except urllib.error.HTTPError as e:
    if e.code == 409:
        # login
        req = urllib.request.Request(f"{base_url}/auth/login", data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as response:
            token = json.loads(response.read())["access_token"]
            print("Token acquired via login:", token[:10])
    else:
        print("Reg failed:", e.code, e.read())
        exit(1)

recipe_data = json.dumps({"food_name": "Chicken", "preferences": "Healthy", "use_profile": False}).encode('utf-8')
req2 = urllib.request.Request(f"{base_url}/generate-recipe", data=recipe_data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
try:
    with urllib.request.urlopen(req2) as response2:
        print("Recipe status:", response2.status)
except urllib.error.HTTPError as e:
    print("Recipe failed:", e.code, e.read())


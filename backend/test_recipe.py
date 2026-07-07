import urllib.request, urllib.parse, json
base_url = "http://localhost:8001"
data = urllib.parse.urlencode({"username":"testnode3@example.com", "password":"password"}).encode()
req = urllib.request.Request(f"{base_url}/auth/login", data=json.dumps({"email":"testnode3@example.com", "password":"password"}).encode(), headers={"Content-Type": "application/json"})
with urllib.request.urlopen(req) as resp:
    token = json.loads(resp.read())["access_token"]

# Now request recipe
r_data = json.dumps({"food_name": "Chicken", "preferences": "Healthy", "use_profile": True}).encode()
r_req = urllib.request.Request(f"{base_url}/generate-recipe", data=r_data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
try:
    with urllib.request.urlopen(r_req) as resp2:
        print("Status:", resp2.status)
        print("Body:", resp2.read())
except urllib.error.HTTPError as e:
    print("Failed status:", e.code)
    print("Failed body:", e.read())

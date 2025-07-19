import http.client
import json

def create_user(email, username, password):
    conn = http.client.HTTPConnection("localhost", 8000)
    payload = json.dumps({
        "email": email,
        "username": username,
        "password": password
    })
    headers = {
        'Content-Type': 'application/json'
    }
    conn.request("POST", "/api/v1/users/create", payload, headers)
    res = conn.getresponse()
    data = res.read()
    return json.loads(data.decode("utf-8"))

usernames = ["vincent85", "vincrano"]
for username in usernames:
    create_user(f"{username}@example.com", username, "password")
    print(f"Created user {username}")
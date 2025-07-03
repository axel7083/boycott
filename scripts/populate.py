import sys
import requests
import uuid
import random
import string

def generate_username(index):
    return f"user{index}{random.randint(100,999)}"

def generate_email(username):
    return f"{username}@example.com"

def create_user(base_url, username):
    url = f"http://{base_url}/api/v1/users/create"
    payload = {
        "email": generate_email(username),
        "password": "password",
        "username": username
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        print(f"✅ Created user: {data['username']} (ID: {data['user_id']})")
    except requests.HTTPError as err:
        print(f"❌ Failed to create user {username}: {err} - {response.text}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python populate.py <host:port>")
        sys.exit(1)

    base_url = sys.argv[1]
    number_of_users = 10  # change as needed

    for i in range(number_of_users):
        username = generate_username(i)
        create_user(base_url, username)

if __name__ == "__main__":
    main()

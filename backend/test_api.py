import requests
import json

base_url = "http://127.0.0.1:8000/api/v1"

def test():
    print("Testing /auth/login...")
    res = requests.post(
        f"{base_url}/auth/login", 
        data={"username": "admin@ainative.erp", "password": "password123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    print("Login Status:", res.status_code)
    try:
        body = res.json()
        print("Login Body:", json.dumps(body, indent=2))
        token = body.get("access_token")
    except Exception as e:
        print("Login Error parsing JSON:", e)
        print("Raw text:", res.text)
        return

    if not token:
        print("No access token returned.")
        return

    print("\nTesting /auth/me...")
    res2 = requests.get(
        f"{base_url}/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    print("Auth Me Status:", res2.status_code)
    try:
        print("Auth Me Body:", json.dumps(res2.json(), indent=2))
    except Exception as e:
        print("Auth Me Error parsing JSON:", e)
        print("Raw text:", res2.text)

    print("\nTesting /users/me...")
    res3 = requests.get(
        f"{base_url}/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    print("Users Me Status:", res3.status_code)
    try:
        print("Users Me Body:", json.dumps(res3.json(), indent=2))
    except Exception as e:
        print("Users Me Error parsing JSON:", e)
        print("Raw text:", res3.text)

if __name__ == "__main__":
    test()

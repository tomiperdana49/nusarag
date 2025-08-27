import requests
import time

class APIClient:
    def __init__(self, base_url, client_id, client_secret):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.expiry = 0

    def get_token(self):
        if not self.token or time.time() > self.expiry:
            resp = requests.post(
                f"{self.base_url}/token",
                auth=(self.client_id, self.client_secret)
            )
            if resp.status_code != 200:
                raise Exception(f"Gagal ambil token: {resp.text}")

            data = resp.json()
            self.token = data["access_token"]
            self.expiry = time.time() + data["expires_in"] - 5
        return self.token

    def call(self, method, path, **kwargs):
        token = self.get_token()
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        return requests.request(method, f"{self.base_url}{path}", headers=headers, **kwargs)


# Bagian ini cuma jalan kalau kamu jalankan langsung: python client.py
if __name__ == "__main__":
    public_api = APIClient("http://127.0.0.1:5000", "public-client", "public-secret")
    r = public_api.call("POST", "/", json={"session_id": "628123", "question": "halo?"})
    print("Public API:", r.status_code, r.json())

    # private_api = APIClient("http://127.0.0.1:5000", "private-client", "private-secret")
    # r = private_api.call("GET", "/private-api")
    # print("Private API:", r.status_code, r.json())

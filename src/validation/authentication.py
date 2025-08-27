from flask import request, jsonify, current_app as app
import base64, datetime, jwt
from connection.connection import get_connection
from functools import wraps

class tokenService:
    def getToken(self, auth):
        try:
            encoded = auth.split(" ")[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            client_id, client_secret = decoded.split(":")
        except Exception:
            return jsonify({"error": "Malformed auth"}), 400

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM oauth_clients WHERE client_id=%s AND client_secret=%s",
                    (client_id, client_secret))
        client = cur.fetchone()
        cur.close()
        conn.close()

        if not client:
            return jsonify({"error": "Invalid client credentials"}), 401
        
        exp = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        payload = {
            "client_id": client["client_id"],
            "roles": client["roles"],
            "exp": exp
        }
        return payload

def require_token(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            auth = request.headers.get('Authorization')
            if not auth or not auth.startswith("Bearer "):
                return jsonify({"error": "Unauthorized"}), 401

            token = auth.split(" ")[1]
            try:
                decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
                request.client_id = decoded["client_id"]
                request.roles = decoded.get("roles", [])
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except Exception:
                return jsonify({"error": "Invalid token"}), 401

            if role and role not in request.roles:
                return jsonify({"error": "Forbidden"}), 403

            return f(*args, **kwargs)
        return wrapper
    return decorator
import pytest
import base64, jwt
from unittest.mock import patch, MagicMock
from flask import Flask, jsonify
from src.validation.authentication import tokenService, require_token
from datetime import datetime, timedelta, timezone
exp = datetime.now(timezone.utc) + timedelta(hours=1)
exp_s =datetime.now(timezone.utc) - timedelta(seconds=1) 

class TestTokenService:
    @patch("src.validation.authentication.jsonify", side_effect=lambda x: x)
    @patch("src.validation.authentication.get_connection")
    def test_get_token_malformed_auth(self, mock_get_connection, mock_jsonify):
        service = tokenService()
        resp, status = service.getToken("notbase64")
        assert status == 400
        assert resp["error"] == "Malformed auth"


    @patch("src.validation.authentication.jsonify", side_effect=lambda x: x)
    @patch("src.validation.authentication.get_connection")
    def test_get_token_invalid_client(self, mock_get_connection, mock_jsonify):
        creds = base64.b64encode(b"client:secret").decode()
        auth = f"Basic {creds}"

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = tokenService()
        resp, status = service.getToken(auth)

        assert status == 401
        assert resp["error"] == "Invalid client credentials"

    @patch("src.validation.authentication.get_connection")
    def test_get_token_success(self, mock_get_connection):
        creds = base64.b64encode(b"client:secret").decode()
        auth = f"Basic {creds}"

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"client_id": "client", "roles": ["private"]}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = tokenService()
        payload = service.getToken(auth)

        assert payload["client_id"] == "client"
        assert "roles" in payload
        assert "exp" in payload

    @patch("src.validation.authentication.get_connection")
    def test_check_users_no_email(self, mock_get_connection):
        service = tokenService()
        assert service.checkUsers({}) is False

    @patch("src.validation.authentication.get_connection")
    def test_check_users_found(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = tokenService()
        assert service.checkUsers({"email": "u@test"}) is True

    @patch("src.validation.authentication.get_connection")
    def test_check_users_not_found(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = tokenService()
        assert service.checkUsers({"email": "u@test"}) is False


class TestRequireToken:
    def setup_method(self):
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "secret"
        self.app = app

    def test_missing_auth_header(self):
        app = self.app

        @app.route("/test")
        @require_token(role="private")
        def test_route():
            return jsonify(ok=True)

        client = app.test_client()
        resp = client.get("/test")
        assert resp.status_code == 401
        assert resp.json["error"] == "Unauthorized"

    def test_expired_token(self):
        app = self.app

        expired_payload = {
            "client_id": "c1",
            "roles": ["private"],
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        }
        token = jwt.encode(expired_payload, app.config["SECRET_KEY"], algorithm="HS256")

        @app.route("/test_expired")
        @require_token(role="private")
        def test_route():
            return jsonify(ok=True)

        client = app.test_client()
        resp = client.get("/test_expired", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert resp.json["error"] == "Token expired"

    def test_invalid_token(self):
        app = self.app

        @app.route("/test3")
        @require_token(role="private")
        def test_route3():
            return jsonify(ok=True)

        client = app.test_client()
        resp = client.get("/test3", headers={"Authorization": "Bearer invalidtoken"})
        assert resp.status_code == 401
        assert resp.json["error"] == "Invalid token"

    def test_forbidden_role(self):
        app = self.app

        payload = {
            "client_id": "c1",
            "roles": ["user"],
            "exp": exp,
        }
        token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

        @app.route("/test4")
        @require_token(role="private")
        def test_route4():
            return jsonify(ok=True)

        client = app.test_client()
        resp = client.get("/test4", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
        assert resp.json["error"] == "Forbidden"

    def test_successful_access(self):
        app = self.app

        payload = {
            "client_id": "c1",
            "roles": ["private"],
            "exp": exp,
        }
        token = jwt.encode(payload, app.config["SECRET_KEY"], algorithm="HS256")

        @app.route("/test5")
        @require_token(role="private")
        def test_route5():
            return jsonify(ok=True)

        client = app.test_client()
        resp = client.get("/test5", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json["ok"] is True

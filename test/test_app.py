import pytest
import json, datetime, runpy
import jwt
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from flask import g

class TestTokenisasi:

    def test_get_token_missing_auth(self,client):
        response = client.post("/get-token")
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data["error"] == "Invalid auth"

    @patch("app.t_service")
    def test_get_token_invalid_credential(self, mock_t_service, client):
        mock_t_service.getToken.return_value = {"error": "Unauthorized"}
        response = client.post("/get-token", headers={
            "Authorization": "Basic dGVzdDp0ZXN0"
        })
        assert response.status_code in [200, 401]
        data = json.loads(response.data)
        assert "error" in data
    
    @patch("app.t_service")
    def test_get_token_success(self, mock_t_service, client, app):
        payload = {"user_id": 1, "role":"private", "exp":9999999999}
        mock_t_service.getToken.return_value = payload
        response = client.post("/get-token", headers={
            "Authorization": "Basic dGVzdDp0ZXN0"
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert "access_token" in data
        assert data["token_type"] == "Bearer"
        assert data["expires_in"] == 3600

        # Decode JWT untuk verifikasi
        decoded = jwt.decode(data["access_token"], app.config["SECRET_KEY"], algorithms=["HS256"])
        assert decoded["user_id"] == 1
        assert decoded["role"] == "private"

class TestAutoGenToken:
    def test_request_access_nusa_body_none(self, client):
        response = client.post(
            "/request-access-nusa",
            content_type="application/json"  # header ada, tapi body kosong
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Data is none"

    @patch("app.requests.post")
    @patch("app.t_service")
    def test_request_access_nusa_invalid_user(self, mock_t_service, mock_requests_post, client):
        # Mock t_service
        mock_t_service.checkUsers.return_value = False
        fake_resp = Mock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {"access_token": "fake-token"}
        mock_requests_post.return_value = fake_resp
        response = client.post("/request-access-nusa", json={"email": "bad@example.com"})
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"] == "Your email is invalid"

    @patch("app.requests.post")
    @patch("app.t_service")
    def test_request_access_nusa_token_api_fail(self, mock_t_service, mock_request_post, client):
        mock_t_service.checkUsers.return_value = True
        fake_resp = Mock()
        fake_resp.status_code = 500
        mock_request_post.return_value = fake_resp
        response = client.post("/request-access-nusa", json={"email": "ok@example.com"})
        assert response.status_code == 500
        data = response.get_json()
        assert data["error"] == "cannot get token"

    @patch("app.requests.post")
    @patch("app.t_service")
    def test_request_access_nusa_post_method(self, mock_t_service, mock_requests_post, client):
        mock_t_service.checkUsers.return_value = True
        # Fake token response
        token_resp = Mock()
        token_resp.status_code = 200
        token_resp.json.return_value = {"access_token": "abc123"}

        # Fake API response
        api_resp = Mock()
        api_resp.status_code = 200
        api_resp.headers = {"Content-Type": "application/json"}
        api_resp.json.return_value = {"ok": True}

        # requests.post dipanggil 2x (untuk TOKEN_API dan target API)
        mock_requests_post.side_effect = [token_resp, api_resp]

        response = client.post("/request-access-nusa", json={
            "email": "ok@example.com",
            "method": "POST",
            "url_target": "http://example.com/api",
            "payload": {"k": "v"}
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True

    @patch("app.requests.post")
    @patch("app.requests.get")
    @patch("app.t_service")
    def test_request_access_nusa_get_method(self, mock_t_service, mock_requests_get,mock_requests_post, client):
        mock_t_service.checkUsers.return_value = True
        # Fake token response
        token_resp = Mock()
        token_resp.status_code = 200
        token_resp.json.return_value = {"access_token": "abc123"}
        mock_requests_post.return_value = token_resp

        # Fake API GET response
        api_resp = Mock()
        api_resp.status_code = 200
        api_resp.headers = {"Content-Type": "text/plain"}
        api_resp.text = "OK"
        mock_requests_get.return_value = api_resp

        response = client.post("/request-access-nusa", json={
            "email": "ok@example.com",
            "method": "GET",
            "url_target": "http://example.com/api"
        })

        assert response.status_code == 200
        assert response.get_json() == "OK"

    @patch("app.requests.post")
    @patch("app.requests.get")
    @patch("app.t_service")
    def test_request_access_nusa_none_method(self, mock_t_service, mock_requests_get,mock_requests_post, client):
        mock_t_service.checkUsers.return_value = True
        # Fake token response
        token_resp = Mock()
        token_resp.status_code = 200
        token_resp.json.return_value = {"access_token": "abc123"}
        mock_requests_post.return_value = token_resp

        # Fake API GET response
        api_resp = Mock()
        api_resp.status_code = 200
        api_resp.headers = {"Content-Type": "text/plain"}
        api_resp.text = "OK"
        mock_requests_get.return_value = api_resp

        response = client.post("/request-access-nusa", json={
            "email": "ok@example.com",
            "method": "",
            "url_target": "http://example.com/api"
        })

        assert response.status_code == 200
        assert response.get_json() == "OK"

    def test_request_access_users_body_none(self, client):
        response = client.post(
            "/request-access-users",
            content_type="application/json"  # header ada, tapi body kosong
        )
        assert response.status_code == 404
        data = response.get_json()
        assert data["error"] == "Data is none"

    @patch("app.requests.post")
    @patch("app.t_service")
    def test_request_access_users_token_api_fail(self, mock_t_service, mock_request_post, client):
        mock_t_service.checkUsers.return_value = True
        fake_resp = Mock()
        fake_resp.status_code = 500
        mock_request_post.return_value = fake_resp
        response = client.post("/request-access-users", json={"email": "ok@example.com"})
        assert response.status_code == 500
        data = response.get_json()
        assert data["error"] == "cannot get token"

    @patch("app.requests.post")
    @patch("app.t_service")
    def test_request_access_users_post_method(self, mock_t_service, mock_requests_post, client):
        mock_t_service.checkUsers.return_value = True
        # Fake token response
        token_resp = Mock()
        token_resp.status_code = 200
        token_resp.json.return_value = {"access_token": "abc123"}

        # Fake API response
        api_resp = Mock()
        api_resp.status_code = 200
        api_resp.headers = {"Content-Type": "application/json"}
        api_resp.json.return_value = {"ok": True}

        # requests.post dipanggil 2x (untuk TOKEN_API dan target API)
        mock_requests_post.side_effect = [token_resp, api_resp]

        response = client.post("/request-access-users", json={
            "email": "ok@example.com",
            "method": "POST",
            "url_target": "http://example.com/api",
            "payload": {"k": "v"}
        })

        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True

    @patch("app.requests.post")
    @patch("app.requests.get")
    @patch("app.t_service")
    def test_request_access_nusa_get_method(self, mock_t_service, mock_requests_get,mock_requests_post, client):
        mock_t_service.checkUsers.return_value = True
        # Fake token response
        token_resp = Mock()
        token_resp.status_code = 200
        token_resp.json.return_value = {"access_token": "abc123"}
        mock_requests_post.return_value = token_resp

        # Fake API GET response
        api_resp = Mock()
        api_resp.status_code = 200
        api_resp.headers = {"Content-Type": "text/plain"}
        api_resp.text = "OK"
        mock_requests_get.return_value = api_resp

        response = client.post("/request-access-users", json={
            "email": "ok@example.com",
            "method": "GET",
            "url_target": "http://example.com/api"
        })

        assert response.status_code == 200
        assert response.get_json() == "OK"

class TestApp:
    #============================
    # DEFAULT SLASH
    #============================
    def test_default_slash(self, client):
        response = client.get("/")
        data = response.get_json()
        assert data["status"] == "OK"
        assert data["service"] == "Seluruh aktivitas dikelola oleh Flask"
        ts = datetime.datetime.fromisoformat(data["timestamp"])
        assert isinstance(ts, datetime.datetime)

        # Opsional: cek timestamp dalam rentang waktu sekarang ± 5 detik
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = abs((now - ts).total_seconds())
        assert delta < 5

    #============================
    # DEFAULT SLASH TEST WITH AUTH
    #============================
    def test_default_slash_test(self, client, auth_headers):
        payload = {"msg": "hello"}
        response = client.post("/test", json=payload, headers=auth_headers)
        data = response.get_json()

        assert response.status_code == 200
        assert data["data"] == payload
        assert data["service"] == "Seluruh aktivitas dikelola oleh Flask"

        # cek timestamp valid dan wajar
        ts = datetime.datetime.fromisoformat(data["timestamp"])
        assert isinstance(ts, datetime.datetime)
        now = datetime.datetime.now(datetime.timezone.utc)
        assert abs((now - ts).total_seconds()) < 5

    #============================
    # DEFAULT SLASH TEST PUBLIC WITH AUTH
    #============================
    def test_default_slash_test_public(self, client, public_auth_headers):
        payload = {"msg": "hello"}
        response = client.post("/test-public", json={"payload": payload}, headers=public_auth_headers)
        data = response.get_json()

        assert response.status_code == 200
        assert data["payload"] == payload
        assert data["service"] == "Seluruh aktivitas dikelola oleh Flask"

        # cek timestamp valid dan wajar
        ts = datetime.datetime.fromisoformat(data["timestamp"])
        assert isinstance(ts, datetime.datetime)
        now = datetime.datetime.now(datetime.timezone.utc)
        assert abs((now - ts).total_seconds()) < 5

class TestArticlesApi:
    def test_get_articles_success(self, client, auth_headers):
        dummy = [{"id": 1, "title": "Test", "content": "Isi"}]
        with patch("app.a_service.get_all_articles", return_value=dummy):
            response = client.get("/articles", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 200
            assert data["success"] is True
            assert data["data"] == dummy

    def test_get_articles_empty(self, client, auth_headers):
        with patch("app.a_service.get_all_articles", return_value=[]):
            response = client.get("/articles", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 200
            assert data["success"] is True
            assert data["data"] == []
    
    def test_get_articles_exception(self, client, auth_headers):
        with patch("app.a_service.get_all_articles", side_effect=Exception("DB down")):
            response = client.get("/articles", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 500
            assert data["success"] is False
            assert data["message"] == "Gagal mengambil data artikel"
            assert "DB down" in data["error"]
    
    def test_create_article_success(self, client, auth_headers):
        payload = {
            "id": 1,
            "title": "Artikel Baru",
            "content": "Isi konten",
            "author": "Tester",
            "organization_id": 1,
            "status": "published",
            "created_by": "tester"
        }
        dummy_result = {**payload, "created_at": "2025-01-01T00:00:00Z"}

        with patch("app.a_service.create_article", return_value=dummy_result):
            response = client.post("/articles", json=payload, headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 201
            assert data["success"] is True
            assert data["message"] == "Artikel berhasil ditambahkan"
            assert data["data"]["title"] == "Artikel Baru"

    def test_create_article_missing_field(self, client, auth_headers):
        # tidak ada 'author', harus gagal di validate_article
        payload = {
            "id": 1,
            "title": "Artikel Tanpa Author",
            "content": "Isi konten",
            "organization_id": 1,
            "status": "published",
            "created_by": "tester"
        }

        response = client.post("/articles", json=payload, headers=auth_headers)
        data = response.get_json()

        assert response.status_code == 400
        assert data["success"] is False
        assert "wajib diisi" in data["message"]

    def test_create_article_exception(self, client, auth_headers):
        payload = {
            "id": 1,
            "title": "Artikel Error",
            "content": "Isi konten",
            "author": "Tester",
            "organization_id": 1,
            "status": "published",
            "created_by": "tester"
        }

        with patch("app.a_service.create_article", side_effect=Exception("DB insert failed")):
            response = client.post("/articles", json=payload, headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 500
            assert data["success"] is False
            assert data["message"] == "Gagal menambahkan artikel"
            assert "DB insert failed" in data["error"]
    
    def test_get_article_by_id_success(self, client, auth_headers):
        dummy_article = {
            "id": 1,
            "title": "Artikel Test",
            "content": "Isi artikel",
            "author": "Tester"
        }

        with patch("app.a_service.get_article_by_id", return_value=dummy_article):
            response = client.get("/articles/1", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 200
            assert data["success"] is True
            assert data["data"]["title"] == "Artikel Test"

    def test_get_article_by_id_not_found(self, client, auth_headers):
        with patch("app.a_service.get_article_by_id", return_value=None):
            response = client.get("/articles/999", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 404
            assert data["success"] is False
            assert data["message"] == "Artikel tidak ditemukan"

    def test_get_article_by_id_exception(self, client, auth_headers):
        with patch("app.a_service.get_article_by_id", side_effect=Exception("DB error")):
            response = client.get("/articles/1", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 500
            assert data["success"] is False
            assert data["message"] == "Gagal mengambil data artikel"
            assert "DB error" in data["error"]

class TestQuestionsApi:
    def test_get_all_questions_success(self, client, auth_headers):
        dummy_questions = [
            {"id": 1, "question": "Apa itu Flask?", "answer": "Framework Python"},
            {"id": 2, "question": "Apa itu JWT?", "answer": "JSON Web Token"}
        ]

        with patch("app.q_service.get_all_question", return_value=dummy_questions):
            response = client.get("/questions", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 200
            assert data["success"] is True
            assert len(data["data"]) == 2
            assert data["data"][0]["question"] == "Apa itu Flask?"

    def test_get_all_questions_empty(self, client, auth_headers):
        with patch("app.q_service.get_all_question", return_value=[]):
            response = client.get("/questions", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 200
            assert data["success"] is True
            assert data["data"] == []

    def test_get_all_questions_exception(self, client, auth_headers):
        with patch("app.q_service.get_all_question", side_effect=Exception("DB error")):
            response = client.get("/questions", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 500
            assert data["success"] is False
            assert data["message"] == "Gagal mengambil data question"
            assert "DB error" in data["error"]
    
    def test_create_questions_success(self, client, auth_headers):
        payload = {
            "id": 1,
            "question": "Apa itu Flask?",
            "answer": "Framework Python",
            "organization_id": 1,
            "created_by": "tester",
            "status": "active"
        }
        dummy_question = {**payload, "created_at": "2025-01-01T00:00:00Z"}

        with patch("app.q_service.create_questions", return_value=dummy_question):
            response = client.post("/questions", json=payload, headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 201
            assert data["success"] is True
            assert data["message"] == "Pertanyaan berhasil ditambahkan"
            assert data["data"]["question"] == "Apa itu Flask?"

    def test_create_questions_invalid(self, client, auth_headers):
        # Missing field `question`
        payload = {
            "id": 2,
            "answer": "Tanpa pertanyaan",
            "organization_id": 1,
            "created_by": "tester",
            "status": "active"
        }
        response = client.post("/questions", json=payload, headers=auth_headers)
        data = response.get_json()

        assert response.status_code == 400
        assert data["success"] is False

    def test_create_questions_exception(self, client, auth_headers):
        payload = {
            "id": 3,
            "question": "Ini error?",
            "answer": "Coba error",
            "organization_id": 1,
            "created_by": "tester",
            "status": "active"
        }

        with patch("app.q_service.create_questions", side_effect=Exception("DB insert failed")):
            response = client.post("/questions", json=payload, headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 500
            assert data["success"] is False
            assert "DB insert failed" in data["error"]
    
class TestQuestionArticlesBatch:

    def test_attach_articles_success(self, client, auth_headers):
        payload = [
            {"question_id": 1, "article_id": 10},
            {"question_id": 1, "article_id": 11}
        ]
        with patch("app.q_service.attach_articles_to_questions_batch", return_value={"success": True}):
            response = client.post("/question-articles", json=payload, headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 201
            assert data["success"] is True
            assert "2 relasi berhasil dibuat" in data["message"]

    def test_attach_articles_invalid(self, client, auth_headers):
        payload = [{"question_id": 99, "article_id": 1}]
        with patch("app.q_service.attach_articles_to_questions_batch", return_value={"success": False}):
            response = client.post("/question-articles", json=payload, headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 400
            assert data["success"] is False

    def test_attach_articles_exception(self, client, auth_headers):
        payload = [{"question_id": 1, "article_id": 1}]
        with patch("app.q_service.attach_articles_to_questions_batch", side_effect=Exception("Batch error")):
            response = client.post("/question-articles", json=payload, headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 500
            assert "Batch error" in data["error"]
    
    def test_get_questions_by_id_success(self, client, auth_headers):
        dummy_question = {"id": 1, "question": "Apa itu JWT?", "answer": "JSON Web Token"}
        with patch("app.q_service.get_questions_by_id", return_value=dummy_question):
            response = client.get("/questions/1", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 200
            assert data["success"] is True
            assert data["data"]["question"] == "Apa itu JWT?"

    def test_get_questions_by_id_not_found(self, client, auth_headers):
        with patch("app.q_service.get_questions_by_id", return_value=None):
            response = client.get("/questions/99", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 404
            assert data["message"] == "Questions tidak ditemukan"

    def test_get_questions_by_id_exception(self, client, auth_headers):
        with patch("app.q_service.get_questions_by_id", side_effect=Exception("DB error")):
            response = client.get("/questions/1", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 500
            assert "DB error" in data["error"]

class TestOrganizationsApi:
    def test_get_organizations_success(self, client, auth_headers):
        dummy_orgs = [{"id": 1, "name": "Org A"}, {"id": 2, "name": "Org B"}]
        with patch("app.o_service.get_organizations", return_value=dummy_orgs):
            response = client.get("/organizations", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 200
            assert len(data["data"]) == 2

    def test_get_organizations_exception(self, client, auth_headers):
        with patch("app.o_service.get_organizations", side_effect=Exception("DB error")):
            response = client.get("/organizations", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 500
            assert "DB error" in data["error"]

    def test_get_organizations_by_id_found(self, client, auth_headers):
        dummy_org = {"id": 1, "name": "Test Org"}
        with patch("app.o_service.get_organizations_by_id", return_value=dummy_org):
            response = client.get("/organizations/1", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 200
            assert data["data"]["name"] == "Test Org"

    def test_get_organizations_by_id_not_found(self, client, auth_headers):
        with patch("app.o_service.get_organizations_by_id", return_value=None):
            response = client.get("/organizations/99", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 404
            assert data["message"] == "Questions tidak ditemukan"

    def test_get_organizations_id_exception(self, client, auth_headers):
        with patch("app.o_service.get_organizations_by_id", side_effect=Exception("DB error")):
            response = client.get("/organizations/1", headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 500
            assert "DB error" in data["error"]

    def test_create_organizations_success(self, client, auth_headers):
        payload = {"id": 1, "name": "Org Baru"}
        dummy_result = {**payload, "created_at": "2025-01-01T00:00:00Z"}

        with patch("app.o_service.create_organizations", return_value=dummy_result):
            response = client.post("/organizations", json=payload, headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 201
            assert data["success"] is True
            assert data["data"]["name"] == "Org Baru"

    def test_create_organizations_exception(self, client, auth_headers):
        payload = {"id": 1, "name": "Org Gagal"}
        with patch("app.o_service.create_organizations", side_effect=Exception("DB error")):
            response = client.post("/organizations", json=payload, headers=auth_headers)
            data = response.get_json()

            assert response.status_code == 500
            assert "DB error" in data["error"]

class TestAskEndpoint:
    def test_ask_invalid_json(self, client):
        response = client.post("/ask", data="invalid json", content_type="application/json")
        assert response.status_code == 400
        data = response.get_json()
        assert data["message"] == "Invalid JSON format"

    def test_ask_success(self, client):
        with patch("app.ak_service.asking", return_value={"answer": "hello"}):
            response = client.post("/ask", json={"q": "Hi"})
            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert data["data"]["answer"] == "hello"
    
    def test_ask_service_exception(self, client):
        with patch("app.ak_service.asking", side_effect=Exception("DB error")):
            response = client.post("/ask", json={"question": "apa itu?"})
            data = response.get_json()

            assert response.status_code == 500
            assert data["success"] is False
            assert data["message"] == "Gagal mendapatkan jawaban"
            assert "DB error" in data["error"]

class TestBatchQuestions:
    # sukses create question batch
    @patch("app.q_service.create_question_batch")
    @patch("app.validate_question_batch", lambda f: f)  # bypass decorator
    @patch("app.require_token", lambda role: (lambda f: f))  # bypass token check
    def test_create_questions_batch_success(self, mock_create_question_batch, client, auth_headers):
        # siapkan data di g (biasanya decorator validate_question_batch yang isi ini)
        g.question_batch_data = [
            {"id": 1,
            "question": "Apa itu Flask?",
            "session_id": "s1",
            "organization_id": 1,
            "created_by": "tester",
            "status": "draft"}
        ]

        mock_create_question_batch.return_value = {
            "success": True,
            "data": [{"id": 1, "question": "Apa itu Flask?"}]
        }

        response = client.post("/questions-batch", json=g.question_batch_data, headers=auth_headers)

        assert response.status_code == 201
        data = response.get_json()
        assert data["success"] is True
        assert "successfully processed" in data["message"]
        assert isinstance(data["data"], list)


    # gagal validasi di service (return success=False)
    @patch("app.q_service.create_question_batch")
    @patch("app.require_token", lambda role: (lambda f: f))
    def test_create_questions_batch_service_fail(self, mock_create_question_batch, client, auth_headers):
        g.question_batch_data = [
            {
                "id": 1,
                "question": "Apa itu Flask?",
                "session_id": "s1",
                "organization_id": 1,
                "created_by": "tester",
                "status": "draft"
            }
        ]

        mock_create_question_batch.return_value = {
            "success": False,
            "message": "DB constraint error"
        }

        response = client.post("/questions-batch", json=g.question_batch_data, headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "DB constraint error" in data["message"]

    # exception di dalam service
    @patch("app.q_service.create_question_batch", side_effect=Exception("DB error"))
    @patch("app.validate_question_batch", lambda f: f)
    @patch("app.require_token", lambda role: (lambda f: f))
    def test_create_questions_batch_exception(self, mock_create_question_batch, client, auth_headers):
        g.question_batch_data = [
            {"id": 1,
        "question": "Apa itu Flask?",
        "session_id": "s1",
        "organization_id": 1,
        "created_by": "tester",
        "status": "draft"}
        ]

        response = client.post("/questions-batch", json=g.question_batch_data, headers=auth_headers)

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "DB error"

class TestBatchArticles:
    def test_create_articles_batch_success(self, client, auth_headers):
        fake_data = [{
        "id": 1,
        "title": "Artikel A",
        "content": "Isi artikel",
        "author": "Penulis",
        "organization_id": 1,
        "status": "active",
        "created_by": "admin",
        "updated_by": "admin"
    }]
        with patch("app.a_service.create_article_batch", return_value={"data": fake_data, "success": True}):
            response = client.post("/articles-batch", json=fake_data, headers=auth_headers)
            assert response.status_code == 201
            data = response.get_json()
            assert "articles successfully processed" in data["message"]

    @patch("app.a_service.create_article_batch")
    @patch("app.require_token", lambda role: (lambda f: f))
    def test_create_article_batch_service_fail(self, mock_create_article_batch, client, auth_headers):
        g.question_batch_data = [
            {
                "id": 1,
                "title": "Test",
                "content": "s1",
                "author": "admin",
                "organization_id": 1,
                "created_by": "tester",
                "updated_by": "admin",
                "status": "draft"
            }
        ]

        mock_create_article_batch.return_value = {
            "success": False,
            "message": "DB constraint error"
        }

        response = client.post("/articles-batch", json=g.question_batch_data, headers=auth_headers)

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "DB constraint error" in data["message"]

# exception di dalam service
    @patch("app.a_service.create_article_batch", side_effect=Exception("DB error"))
    @patch("app.validate_article_batch", lambda f: f)
    @patch("app.require_token", lambda role: (lambda f: f))
    def test_create_articles_batch_exception(self, mock_create_article_batch, client, auth_headers):
        g.question_batch_data = [
            {
                "id": 1,
                "title": "Test",
                "content": "s1",
                "author": "admin",
                "organization_id": 1,
                "created_by": "tester",
                "updated_by": "admin",
                "status": "draft"
            }
        ]

        response = client.post("/articles-batch", json=g.question_batch_data, headers=auth_headers)

        assert response.status_code == 500
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "DB error"

class TestLogAndArticle:
    def test_get_log(self, client, auth_headers):
        with patch("app.l_service.get_Log", return_value=[{"id": 1, "msg": "ok"}]):
            response = client.get("/log", headers=auth_headers)
            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data, list)

    def test_get_article_id(self, client, auth_headers):
        with patch("app.a_service.getArticle_Id", return_value=[{"id": 1, "title": "Test"}]):
            response = client.get("/get-article", headers=auth_headers)
            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data, list)

class TestHooks:
    def test_listener_success(self, client, auth_headers):
        with patch("app.h.setListenerHook", return_value=True):
            response = client.post("/listen-hook", data="payload", headers=auth_headers)
            assert response.status_code == 200
            assert response.data == b"ok"

class TestDeleteArticle:
    def test_clear_article_none(self, client, auth_headers):
        response = client.post("/delete-article", json=None, headers=auth_headers)
        assert response.status_code == 404
        assert b"Id is None" in response.data

    def test_clear_article_success(self, client, auth_headers):
        with patch("app.a_service.deleteArticle", return_value=True):
            response = client.post("/delete-article", json={"id": 1}, headers=auth_headers)
            assert response.status_code == 200
            assert b"ok" in response.data

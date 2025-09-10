import pytest
from flask import Flask, jsonify, g
from unittest.mock import patch, MagicMock
from src.validation import validation


def make_app():
    app = Flask(__name__)

    @app.route("/article", methods=["POST"])
    @validation.validate_article
    def article():
        return jsonify(success=True, data=g.article_data)

    @app.route("/question", methods=["POST"])
    @validation.validate_question
    def question():
        return jsonify(success=True, data=g.question_data)

    @app.route("/question-article-batch", methods=["POST"])
    @validation.validate_question_article_batch
    def q_abatch():
        return jsonify(success=True, data=g.question_article_batch_data)

    @app.route("/article-batch", methods=["POST"])
    @validation.validate_article_batch
    def abatch():
        return jsonify(success=True, data=g.article_batch_data)

    @app.route("/question-batch", methods=["POST"])
    @validation.validate_question_batch
    def qbatch():
        return jsonify(success=True, data=g.question_batch_data)

    @app.route("/organization", methods=["POST"])
    @validation.validate_organizations
    def org():
        return jsonify(success=True, data=g.organization_data)

    return app


class TestValidationFull:
    def setup_method(self):
        self.app = make_app()
        self.client = self.app.test_client()

    # --- validate_article ---
    def test_article_empty_body(self):
        resp = self.client.post("/article", data="", content_type="application/json")
        assert resp.status_code == 400

    def test_article_missing_field(self):
        resp = self.client.post("/article", json={"id": 1})
        assert resp.status_code == 400

    def test_article_success_sets_updated_by(self):
        payload = {
            "id": 1, "title": "T", "content": "C", "author": "A",
            "organization_id": 1, "status": "draft", "created_by": "u1"
        }
        resp = self.client.post("/article", json=payload)
        assert resp.status_code == 200
        assert resp.json["data"]["updated_by"] == "u1"

    # --- validate_question ---
    def test_question_empty_body(self):
        resp = self.client.post("/question", data="", content_type="application/json")
        assert resp.status_code == 400

    def test_question_missing_field(self):
        resp = self.client.post("/question", json={"id": 1})
        assert resp.status_code == 400

    def test_question_article_id_not_int(self):
        payload = {
            "id": 1, "question": "Apa?", "organization_id": 1,
            "created_by": "u1", "status": "active", "article_id": "xx"
        }
        resp = self.client.post("/question", json=payload)
        assert resp.status_code == 400

    def test_question_success(self):
        payload = {
            "id": 1, "question": "Apa?", "organization_id": 1,
            "created_by": "u1", "status": "active"
        }
        resp = self.client.post("/question", json=payload)
        assert resp.status_code == 200
        assert resp.json["data"]["updated_by"] == "u1"

    # --- validate_question_article_batch ---
    def test_qabatch_not_list(self):
        resp = self.client.post("/question-article-batch", json={"x": 1})
        assert resp.status_code == 400

    def test_qabatch_item_not_dict(self):
        resp = self.client.post("/question-article-batch", json=["bad"])
        assert resp.status_code == 400

    def test_qabatch_missing_field(self):
        resp = self.client.post("/question-article-batch", json=[{"question_id": 1}])
        assert resp.status_code == 400

    def test_qabatch_field_not_int(self):
        resp = self.client.post("/question-article-batch", json=[{"question_id": 1, "article_id": "bad"}])
        assert resp.status_code == 400

    def test_qabatch_success(self):
        payload = [{"question_id": 1, "article_id": 2}]
        resp = self.client.post("/question-article-batch", json=payload)
        assert resp.status_code == 200

    # --- validate_article_batch ---
    def test_abatch_not_list(self):
        resp = self.client.post("/article-batch", json={"id": 1})
        assert resp.status_code == 400

    def test_abatch_item_not_dict(self):
        resp = self.client.post("/article-batch", json=["bad"])
        assert resp.status_code == 400

    def test_abatch_missing_field(self):
        resp = self.client.post("/article-batch", json=[{"id": 1}])
        assert resp.status_code == 400

    def test_abatch_invalid_types(self):
        payload = [{
            "id": "x", "title": 1, "content": 2, "author": 3,
            "organization_id": "bad", "status": 4,
            "created_by": 5, "updated_by": 6
        }]
        resp = self.client.post("/article-batch", json=payload)
        assert resp.status_code == 400

    def test_abatch_success(self):
        payload = [{
            "id": 1, "title": "T", "content": "C", "author": "A",
            "organization_id": 1, "status": "draft",
            "created_by": "u1", "updated_by": "u1"
        }]
        resp = self.client.post("/article-batch", json=payload)
        assert resp.status_code == 200

    def test_abatch_invalid_str_field(self):
        payload = [{
            "id": 1,
            "title": 123,  # salah: harus string
            "content": "C", "author": "A",
            "organization_id": 1, "status": "active",
            "created_by": "u1", "updated_by": "u1"
        }]
        resp = self.client.post("/article-batch", json=payload)
        assert resp.status_code == 400
        assert "title harus berupa string" in resp.json["message"]

    # --- validate_question_batch ---
    def test_qbatch_not_list(self):
        resp = self.client.post("/question-batch", json={"id": 1})
        assert resp.status_code == 400

    def test_qbatch_item_not_dict(self):
        resp = self.client.post("/question-batch", json=["bad"])
        assert resp.status_code == 400

    def test_qbatch_missing_field(self):
        resp = self.client.post("/question-batch", json=[{"id": 1}])
        assert resp.status_code == 400

    def test_qbatch_invalid_types(self):
        payload = [{
            "id": "x", "question": 1, "organization_id": "bad",
            "created_by": 123, "status": 456
        }]
        resp = self.client.post("/question-batch", json=payload)
        assert resp.status_code == 400

    def test_qbatch_success(self):
        payload = [{
            "id": 1, "question": "Apa?", "organization_id": 1,
            "created_by": "u1", "status": "active"
        }]
        resp = self.client.post("/question-batch", json=payload)
        assert resp.status_code == 200

    def test_qbatch_invalid_str_field(self):
            payload = [{
                "id": 1, "question": 2, "organization_id": 1,
                "created_by": "u1", "status": "active"
            }]
            resp = self.client.post("/question-batch", json=payload)
            assert resp.status_code == 400
            assert "question harus berupa string" in resp.json["message"]

    # --- validate_organizations ---
    @patch("src.validation.validation.get_connection")
    def test_org_duplicate(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("Org",)
        mock_conn.return_value.cursor.return_value = mock_cursor

        resp = self.client.post("/organization", json={"name": "Org"})
        assert resp.status_code == 400
        assert "sudah terdaftar" in resp.json["message"]

    @patch("src.validation.validation.get_connection")
    def test_org_success(self, mock_conn):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.return_value.cursor.return_value = mock_cursor

        resp = self.client.post("/organization", json={"name": "Org"})
        assert resp.status_code == 200
        assert resp.json["data"]["name"] == "Org"

    def test_org_empty_body(self):
        resp = self.client.post("/organization", data="", content_type="application/json")
        assert resp.status_code == 400
        assert "tidak boleh kosong" in resp.json["message"]

    def test_org_missing_name(self):
        resp = self.client.post(
            "/organization",
            json={"id": 1}
        )
        assert resp.status_code == 400
        assert "Field name wajib diisi" in resp.json["message"]


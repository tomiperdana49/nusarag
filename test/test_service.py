import pytest
from unittest.mock import patch, MagicMock
from src.service.service import ArticleService, QuestionService, OrganizationService, AskService, LogService, webHook


class TestArticleService:
    @patch("src.service.service.get_connection")
    def test_create_article_success(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1, "title": "Test"}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = ArticleService()
        article = {
            "id": 1, "title": "Test", "content": "C", "author": "A",
            "organization_id": 99, "status": "published",
            "created_by": "user1", "updated_by": "user1"
        }
        result = service.create_article(article)

        assert result["id"] == 1
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("src.service.service.get_connection")
    def test_create_article_batch_success(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = ArticleService()
        pairs = [{
            "id": 1, "title": "T", "content": "C", "author": "A",
            "organization_id": 99, "status": "draft",
            "created_by": "u1", "updated_by": "u2"
        }]
        result = service.create_article_batch(pairs)

        assert result["success"] is True
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("src.service.service.get_connection")
    def test_create_article_batch_exception(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = ArticleService()
        with pytest.raises(Exception, match="DB error"):
            service.create_article_batch([{
                "id": 1, "title": "T", "content": "C", "author": "A",
                "organization_id": 99, "status": "draft",
                "created_by": "u1", "updated_by": "u2"
            }])

        mock_conn.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("src.service.service.get_connection")
    def test_get_all_articles(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "title": "T1"}, {"id": 2, "title": "T2"}
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = ArticleService()
        rows = service.get_all_articles()

        assert len(rows) == 2
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("src.service.service.get_connection")
    def test_get_article_by_id_found(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1, "title": "T1"}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = ArticleService()
        row = service.get_article_by_id(1)

        assert row["id"] == 1

    @patch("src.service.service.get_connection")
    def test_get_article_by_id_not_found(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = ArticleService()
        row = service.get_article_by_id(999)

        assert row is None

    @patch("src.service.service.get_connection")
    def test_getArticle_Id(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "title": "T1", "content": "C1"}
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = ArticleService()
        rows = service.getArticle_Id()

        assert rows[0]["id"] == 1

    @patch("src.service.service.get_connection")
    def test_deleteArticle(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = ArticleService()
        result = service.deleteArticle({"id": 1})

        assert result == ("ok", 200)
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

class TestQuestionService:
    @patch("src.service.service.get_connection")
    @patch("src.service.service.convert", return_value=[0.1, 0.2])
    def test_create_questions_success(self, mock_convert, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = [1]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = QuestionService()
        data = {
            "id": 1, "question": "Apa itu Flask?",
            "organization_id": 10,
            "created_by": "u1", "updated_by": None, "status": "active"
        }
        result = service.create_questions(data)

        assert result["id"] == 1
        assert result["question"] == "Apa itu Flask?"
        mock_conn.commit.assert_called_once()

    @patch("src.service.service.get_connection")
    @patch("src.service.service.convert", return_value=None)
    def test_create_questions_convert_fail(self, mock_convert, mock_get_connection):
        service = QuestionService()
        with pytest.raises(Exception, match="Gagal dalam mengkonversi vektor"):
            service.create_questions({"id": 1, "question": "?"})

    @patch("src.service.service.get_connection")
    @patch("src.service.service.convert", return_value=[0.1])
    def test_create_questions_db_error(self, mock_convert, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = QuestionService()
        with pytest.raises(Exception, match="DB error"):
            service.create_questions({"id": 1, "question": "?"})

        mock_conn.rollback.assert_called_once()

    @patch("src.service.service.get_connection")
    @patch("src.service.service.convert", return_value=[0.1])
    def test_create_question_batch_success(self, mock_convert, mock_get_connection):
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = QuestionService()
        pairs = [{
            "id": 1, "question": "Q", "organization_id": 1,
            "created_by": "u1", "updated_by": "u2", "status": "ok"
        }]
        result = service.create_question_batch(pairs)

        assert result["success"] is True
        mock_conn.commit.assert_called_once()

    @patch("src.service.service.get_connection")
    @patch("src.service.service.convert", return_value=[0.1])
    def test_create_question_batch_exception(self, mock_convert, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("fail")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = QuestionService()
        with pytest.raises(Exception, match="fail"):
            service.create_question_batch([{
                "id": 1, "question": "Q", "organization_id": 1,
                "created_by": "u1", "updated_by": "u2", "status": "ok"
            }])

        mock_conn.rollback.assert_called_once()

    @patch("src.service.service.get_connection")
    def test_attach_articles_missing_ids(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [],  # no questions found
            [],  # no articles found
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = QuestionService()
        pairs = [{"question_id": 99, "article_id": 77}]
        result = service.attach_articles_to_questions_batch(pairs)

        assert result["success"] is False
        assert 99 in result["missing_questions"]
        assert 77 in result["missing_articles"]

    @patch("src.service.service.get_connection")
    def test_attach_articles_success(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.side_effect = [
            [(1,)],  # found question
            [(2,)],  # found article
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = QuestionService()
        pairs = [{"question_id": 1, "article_id": 2}]
        result = service.attach_articles_to_questions_batch(pairs)

        assert result["success"] is True
        mock_conn.commit.assert_called()

    @patch("src.service.service.get_connection")
    def test_get_all_question(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"question_id": 1, "question": "Q1", "status": "ok",
             "created_by": "u1", "updated_by": "u2",
             "created_at": "now", "updated_at": "now",
             "organization_id": 1, "organization_name": "Org",
             "article_id": 2, "article_title": "T", "article_content": "C"}
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = QuestionService()
        rows = service.get_all_question()

        assert rows[0]["id"] == 1
        assert len(rows[0]["articles"]) == 1

    @patch("src.service.service.get_connection")
    def test_get_questions_by_id_found(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"question_id": 1, "question": "Q", "status": "ok",
             "created_by": "u1", "updated_by": "u2",
             "created_at": "now", "updated_at": "now",
             "organization_id": 1, "organization_name": "Org",
             "article_id": 2, "article_title": "T", "article_content": "C"}
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = QuestionService()
        row = service.get_questions_by_id(1)

        assert row["id"] == 1
        assert len(row["articles"]) == 1

    @patch("src.service.service.get_connection")
    def test_get_questions_by_id_not_found(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = QuestionService()
        row = service.get_questions_by_id(999)

        assert row is None

@patch("src.service.service.get_connection")
def test_attach_articles_exception(mock_get_connection):
    mock_cursor = MagicMock()
    # fetchall pertama → questions found
    mock_cursor.fetchall.side_effect = [
        [(1,)],  # question found
        [(2,)],  # article found
    ]
    # trigger exception di INSERT
    def execute_side_effect(query, params=None):
        if "INSERT INTO question_articles" in query:
            raise Exception("Insert error")
    mock_cursor.execute.side_effect = execute_side_effect

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_connection.return_value = mock_conn

    service = QuestionService()
    pairs = [{"question_id": 1, "article_id": 2}]

    with pytest.raises(Exception, match="Insert error"):
        service.attach_articles_to_questions_batch(pairs)

    # Pastikan rollback dipanggil
    mock_conn.rollback.assert_called_once()

class TestOrganizationService:
    @patch("src.service.service.get_connection")
    def test_get_organizations(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "name": "Org1"},
            {"id": 2, "name": "Org2"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = OrganizationService()
        rows = service.get_organizations()

        assert len(rows) == 2
        assert rows[0]["name"] == "Org1"
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("src.service.service.get_connection")
    def test_get_organizations_by_id_found(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1, "name": "Org1"}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = OrganizationService()
        row = service.get_organizations_by_id(1)

        assert row["id"] == 1
        assert row["name"] == "Org1"

    @patch("src.service.service.get_connection")
    def test_get_organizations_by_id_not_found(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = OrganizationService()
        row = service.get_organizations_by_id(999)

        assert row is None

    @patch("src.service.service.get_connection")
    def test_create_organizations(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1, "name": "Org1"}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = OrganizationService()
        org = {"name": "Org1"}
        result = service.create_organizations(org)

        assert result["id"] == 1
        assert result["name"] == "Org1"
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

class TestAskService:
    @patch("src.service.service.ask", return_value="mocked answer")
    def test_asking_success(self, mock_ask):
        service = AskService()
        request_data = {"question": "Apa itu Flask?", "session_id": "s1", "organization_id": 1}
        result = service.asking(request_data)

        assert result == "mocked answer"
        mock_ask.assert_called_once_with("Apa itu Flask?", "s1", 1)

    def test_asking_missing_question(self):
        service = AskService()
        request_data = {"session_id": "s1", "organization_id": 1}

        with pytest.raises(ValueError, match="Kunci 'question' tidak ditemukan"):
            service.asking(request_data)


class TestLogService:
    @patch("src.service.service.get_connection")
    def test_get_log(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"id": 1, "question": "Q1", "response": "R1"},
            {"id": 2, "question": "Q2", "response": "R2"},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = LogService()
        rows = service.get_Log()

        assert len(rows) == 2
        assert rows[0]["id"] == 1
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()


class TestWebHook:
    @patch("src.service.service.get_connection")
    def test_set_listener_hook_success(self, mock_get_connection, capsys):
        mock_cursor = MagicMock()
        # gunakan context manager di cursor
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        service = webHook()
        service.setListenerHook("payload123")

        mock_cursor.execute.assert_called_once_with(
            "INSERT INTO hook_data (datas) VALUES (%s)", ("payload123",)
        )
        mock_conn.commit.assert_called_once()

        # cek output print
        captured = capsys.readouterr()
        assert "Payload berhasil disimpan" in captured.out

    @patch("src.service.service.get_connection")
    def test_set_listener_hook_exception(self, mock_get_connection, capsys):
        mock_conn = MagicMock()
        # simulate error ketika buka cursor
        mock_conn.cursor.side_effect = Exception("DB error")
        mock_get_connection.return_value = mock_conn

        service = webHook()
        service.setListenerHook("payloadXYZ")

        captured = capsys.readouterr()
        assert "Error:" in captured.out
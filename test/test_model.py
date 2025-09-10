import pytest
from unittest.mock import patch, MagicMock
from flask import jsonify

import src.model.model as model

class TestConvert:
    @patch("src.model.model.OpenAIEmbeddings")
    def test_convert_success(self, mock_embeddings_cls):
        # bikin dummy instance yang embed_query sudah di-mock
        mock_instance = MagicMock()
        mock_instance.embed_query.return_value = [0.1, 0.2, 0.3]
        mock_embeddings_cls.return_value = mock_instance

        result = model.convert("Apa itu Flask?")

        assert result == [0.1, 0.2, 0.3]
        mock_embeddings_cls.assert_called_once_with(model="text-embedding-3-small")
        mock_instance.embed_query.assert_called_once_with("Apa itu Flask?")

class TestMatchQuestion:
    @patch("src.model.model.get_connection")
    @patch("src.model.model.convert")
    def test_match_question_success_high_similarity(self, mock_convert, mock_get_connection):
        mock_convert.return_value = [0.1, 0.2, 0.3]

        # mock cursor & db
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{
            "question_id": 1,
            "question": "Apa itu Flask?",
            "cosine_similarity": 0.9,
            "article_id": 101,
            "article_title": "Flask Intro",
            "article_content": "Flask adalah framework..."
        }]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        result = model.match_question("Apa itu Flask?", 1)

        assert isinstance(result, list)
        assert result[0]["question"] == "Apa itu Flask?"
        assert result[0]["similarity"] == 0.9
        assert "articles" in result[0]

    @patch("src.model.model.get_connection")
    @patch("src.model.model.convert")
    def test_match_question_success_low_similarity(self, mock_convert, mock_get_connection):
        mock_convert.return_value = [0.1, 0.2, 0.3]

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [{
            "question_id": 2,
            "question": "Apa itu Django?",
            "cosine_similarity": 0.5,
            "article_id": 202,
            "article_title": "Django Intro",
            "article_content": "Django adalah framework..."
        }]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        result = model.match_question("Apa itu Flask?", 1)

        assert result[0]["question"] == "Apa itu Flask?"
        assert result[0]["similar_question"] == "Apa itu Django?"
        assert "belum dapat saya jawab" in result[0]["article_content"]

    @patch("src.model.model.get_connection")
    @patch("src.model.model.convert")
    def test_match_question_no_results(self, mock_convert, mock_get_connection):
        mock_convert.return_value = [0.1, 0.2, 0.3]

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # no results
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        result = model.match_question("Apa itu FastAPI?", 1)

        assert result[0]["similarity"] == 0
        assert "belum dapat saya jawab" in result[0]["article_content"]

    @patch("src.model.model.get_connection")
    @patch("src.model.model.convert", return_value=None)
    def test_match_question_convert_failed(self, mock_convert, mock_get_connection):
        result = model.match_question("Apa itu Flask?", 1)

        assert "Tidak dapat melakukan konversi vektor" in result[0]["article_content"]

    @patch("src.model.model.get_connection")
    @patch("src.model.model.convert")
    def test_match_question_db_exception(self, mock_convert, mock_get_connection):
        mock_convert.return_value = [0.1, 0.2, 0.3]

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        result, _ = model.match_question("Apa itu Flask?", 1)

        assert "Gagal query database" in result[0]["article_content"]

class TestFindHistory:
    @patch("src.model.model.jsonify", side_effect=lambda x: x)  # jsonify return dict langsung
    def test_invalid_input(self, mock_jsonify):
        resp, status = model.find_history("", 1)

        assert status == 400
        assert resp["success"] is False
        assert "wajib diisi" in resp["message"]

    @patch("src.model.model.get_connection")
    def test_find_history_with_results(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [
            {"question": "Apa itu Flask?", "response": "Flask adalah framework."},
            {"question": "Apa itu Django?", "response": "Django adalah framework."},
        ]
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        result = model.find_history("s1", 1)

        assert isinstance(result, list)
        assert result[0]["question"] == "Apa itu Flask?"
        assert result[1]["response"] == "Django adalah framework."
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("src.model.model.get_connection")
    def test_find_history_no_results(self, mock_get_connection):
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # no results
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        result = model.find_history("s1", 1)

        assert result == []
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

class TestSaveLog:
    @patch("src.model.model.get_connection")
    def test_save_log_success(self, mock_get_connection):
        # Mock DB objects
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 123}
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        fake_data = {
            "time": "2025-09-10 10:00:00",
            "organization_id": 1,
            "question": "Apa itu Flask?",
            "similar_question": "Apa itu Flask?",
            "similarity": 0.9,
            "context": "testing",
            "system_instruction": "instruksi",
            "response": "Flask adalah framework",
            "session_id": "s1",
            "summary": "summary",
            "vector": [0.1, 0.2, 0.3],
        }

        result = model.save_log(fake_data)

        assert result["success"] is True
        assert result["log_id"] == 123
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("src.model.model.get_connection")
    def test_save_log_exception(self, mock_get_connection, capsys):
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        fake_data = {
            "time": "2025-09-10 10:00:00",
            "organization_id": 1,
            "question": "Apa itu Flask?",
            "similar_question": "Apa itu Flask?",
            "similarity": 0.9,
            "context": "testing",
            "system_instruction": "instruksi",
            "response": "Flask adalah framework",
            "session_id": "s1",
            "summary": "summary",
            "vector": [0.1, 0.2, 0.3],
        }

        result = model.save_log(fake_data)

        # Pastikan error path
        assert result["success"] is False
        assert "DB error" in result["error"]
        mock_conn.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

        # Pastikan traceback di-print
        captured = capsys.readouterr()
        assert "Error saat insert log" in captured.out

class TestSaveHistory:
    @patch("src.model.model.get_connection")
    def test_save_history_success(self, mock_get_connection):
        # Mock DB objects
        mock_cursor = MagicMock()
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        fake_data = {
            "time": "2025-09-10 10:00:00",
            "session_id": "s1",
            "organization_id": 1,
            "question": "Apa itu Flask?",
            "response": "Flask adalah framework",
        }

        result = model.save_history(fake_data)

        assert result["success"] is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("src.model.model.get_connection")
    def test_save_history_exception(self, mock_get_connection):
        # Mock DB objects dengan error saat execute
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("DB error")
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_get_connection.return_value = mock_conn

        fake_data = {
            "time": "2025-09-10 10:00:00",
            "session_id": "s1",
            "organization_id": 1,
            "question": "Apa itu Flask?",
            "response": "Flask adalah framework",
        }

        result = model.save_history(fake_data)

        assert result["success"] is False
        assert "DB error" in result["error"]
        mock_conn.rollback.assert_called_once()
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

@pytest.fixture(autouse=True)
def patch_prompts(monkeypatch):
    monkeypatch.setattr(model, "prompt_sum", "{history} {question}")
    monkeypatch.setattr(model, "prompt_translate_h", "{history}")
    monkeypatch.setattr(model, "prompt_notfoundh", "{question} {history} {month} {year}")
    monkeypatch.setattr(model, "prompt_answrh", "{question} {articles} {month} {year} {history}")
    monkeypatch.setattr(model, "prompt_translate", "{question}")
    monkeypatch.setattr(model, "prompt_notfound", "{question} {month} {year}")
    monkeypatch.setattr(model, "prompt_answr", "{question} {articles} {month} {year}")
    yield


@patch("src.model.model.ChatOpenAI")
@patch("src.model.model.find_history")
@patch("src.model.model.match_question")
@patch("src.model.model.save_log")
@patch("src.model.model.save_history")
@patch("src.model.model.convert", return_value=[0.1, 0.2, 0.3])
def test_history_article_found(mock_convert, mock_save_history, mock_save_log,
                               mock_match, mock_find_history, mock_llm):
    # history ada
    mock_find_history.return_value = [{"question": "Q1", "response": "R1"}]
    # q_data dengan artikel
    mock_match.return_value = [{
        "question": "Apa itu Flask?",
        "similarity": 0.9,
        "articles": [{"id": 1, "title": "T1", "content": "C1"}],
    }]
    # llm.invoke selalu return object dengan content
    mock_instance = MagicMock()
    mock_instance.invoke.return_value.content = "LLM response"
    mock_llm.return_value = mock_instance

    resp = model.ask("Apa itu Flask?", "s1", 1)

    assert "LLM response" in resp[0]  # response_text
    assert resp[2] == "Article Found"  # marker


@patch("src.model.model.ChatOpenAI")
@patch("src.model.model.find_history")
@patch("src.model.model.match_question")
@patch("src.model.model.save_log")
@patch("src.model.model.save_history")
@patch("src.model.model.convert", return_value=[0.1, 0.2, 0.3])
def test_history_article_not_found(mock_convert, mock_save_history, mock_save_log,
                                   mock_match, mock_find_history, mock_llm):
    mock_find_history.return_value = [{"question": "Q1", "response": "R1"}]
    mock_match.return_value = [{"similar_question": "Apa itu X", "similarity": 0.5}]
    mock_instance = MagicMock()
    mock_instance.invoke.return_value.content = "NF response"
    mock_llm.return_value = mock_instance

    resp = model.ask("Apa itu Flask?", "s1", 1)

    assert "NF response" in resp[0]
    assert resp[2] == "Not found article"


@patch("src.model.model.ChatOpenAI")
@patch("src.model.model.find_history", return_value=[])
@patch("src.model.model.match_question")
@patch("src.model.model.save_log")
@patch("src.model.model.save_history")
@patch("src.model.model.convert", return_value=[0.1, 0.2, 0.3])
def test_no_history_article_found(mock_convert, mock_save_history, mock_save_log,
                                  mock_match, mock_find_history, mock_llm):
    mock_match.return_value = [{
        "question": "Apa itu Flask?",
        "similarity": 0.9,
        "articles": [{"id": 1, "title": "T1", "content": "C1"}],
    }]
    mock_instance = MagicMock()
    mock_instance.invoke.return_value.content = "Ans response"
    mock_llm.return_value = mock_instance

    resp = model.ask("Apa itu Flask?", "s1", 1)

    assert "Ans response" in resp[0]
    assert resp[1] == "Article Found"


@patch("src.model.model.ChatOpenAI")
@patch("src.model.model.find_history", return_value=[])
@patch("src.model.model.match_question")
@patch("src.model.model.save_log")
@patch("src.model.model.save_history")
@patch("src.model.model.convert", return_value=[0.1, 0.2, 0.3])
def test_no_history_article_not_found(mock_convert, mock_save_history, mock_save_log,
                                      mock_match, mock_find_history, mock_llm):
    mock_match.return_value = [{"similar_question": "Apa itu X", "similarity": 0.3}]
    mock_instance = MagicMock()
    mock_instance.invoke.return_value.content = "NF response"
    mock_llm.return_value = mock_instance

    resp = model.ask("Apa itu Flask?", "s1", 1)

    assert "NF response" in resp[0]
    assert "Article Not Found" in resp[1]


@patch("src.model.model.ChatOpenAI")
@patch("src.model.model.find_history", return_value=[{"q": "dummy"}])
@patch("src.model.model.match_question", side_effect=Exception("boom"))
@patch("src.model.model.save_log")
@patch("src.model.model.save_history")
def test_exception_path(mock_save_history, mock_save_log,
                        mock_match, mock_find_history, mock_llm):
    mock_instance = MagicMock()
    mock_instance.invoke.return_value.content = "ignored"
    mock_llm.return_value = mock_instance

    resp = model.ask("Apa itu Flask?", "s1", 1)

    assert isinstance(resp, dict)
    assert resp["success"] is False
    assert "Internal error" in resp["message"]

@patch("src.model.model.ChatOpenAI")
@patch("src.model.model.find_history", return_value=[{"q": "dummy"}])
@patch("src.model.model.save_log")
@patch("src.model.model.save_history")
@patch("src.model.model.convert", return_value=[0.1, 0.2, 0.3])
def test_articles_with_invalid_entries(mock_convert, mock_save_history, mock_save_log,
                                       mock_find_history, mock_llm):
    # Case 1: articles bukan list
    bad_q_data = [{"question": "Q", "similarity": 0.8, "articles": "string bukan list"}]

    # Case 2: articles list tapi item kosong
    bad_q_data2 = [{"question": "Q", "similarity": 0.8, "articles": [None, {"title": "T"}]}]

    # Kita akan uji dua kali, satu untuk masing-masing case
    for q_data in (bad_q_data, bad_q_data2):
        with patch("src.model.model.match_question", return_value=q_data):
            mock_instance = MagicMock()
            mock_instance.invoke.return_value.content = "Dummy response"
            mock_llm.return_value = mock_instance

            resp = model.ask("Apa itu Flask?", "s1", 1)
            # Harus tetap return string response
            assert isinstance(resp[0], str)
import pytest, sys, os
from unittest.mock import Mock, patch

# Tambahkan project path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, src_path)

import src.connection.connection as db  # misalnya file get_connection ada di src/db.py

class TestDatabaseMocking:
    @patch("psycopg2.connect")
    def test_database_connection_mocking(self, mock_connect):
        """Pastikan psycopg2.connect bisa di-mock dan return di get_connection()"""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn

        conn = db.get_connection()

        assert conn == mock_conn
        mock_connect.assert_called_once()

    @patch("src.model.model.save_log")  # patch sesuai namespace yang dipakai
    def test_log_saving_mock(self, mock_save_log):
        """Pastikan save_log bisa di-mock"""
        mock_save_log.return_value = None

        from src.model.model import save_log
        result = save_log({"test": "data"})

        assert result is None
        mock_save_log.assert_called_once()

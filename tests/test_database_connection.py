import os
import unittest
from unittest.mock import patch

from database.connection import get_connection


class DatabaseConnectionTests(unittest.TestCase):
    def test_requires_database_user_and_password(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(
                RuntimeError,
                "PYASK_DB_USER, PYASK_DB_PASSWORD",
            ):
                get_connection()

    def test_uses_environment_settings_and_defaults(self):
        settings = {
            "PYASK_DB_USER": "test-user",
            "PYASK_DB_PASSWORD": "test-password",
        }

        with patch.dict(os.environ, settings, clear=True):
            with patch("database.connection.mysql.connector.connect") as connect:
                get_connection()

        connect.assert_called_once_with(
            host="127.0.0.1",
            port=3306,
            user="test-user",
            password="test-password",
            database="pyask_db",
            charset="utf8mb4",
            use_unicode=True,
        )

    def test_rejects_invalid_port(self):
        settings = {
            "PYASK_DB_USER": "test-user",
            "PYASK_DB_PASSWORD": "test-password",
            "PYASK_DB_PORT": "not-a-port",
        }

        with patch.dict(os.environ, settings, clear=True):
            with self.assertRaisesRegex(ValueError, "must be an integer"):
                get_connection()


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import Mock, patch

from database.user_repository import UserRepository
from models.user import User


class UserRepositoryTests(unittest.TestCase):
    def test_admin_cannot_demote_themselves(self):
        admin = User(
            "admin",
            "admin@example.com",
            User.hash_password("secret1"),
            role="admin",
            id=1,
        )
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [("admin",), ("admin",)]

        with patch(
            "database.user_repository.get_connection",
            return_value=connection,
        ):
            with self.assertRaises(PermissionError):
                UserRepository().change_role(1, "user", admin)

        self.assertEqual(cursor.execute.call_count, 2)
        connection.commit.assert_not_called()
        cursor.close.assert_called_once()
        connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()

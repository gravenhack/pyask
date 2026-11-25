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

    def test_update_profile_changes_username_and_password(self):
        user = User(
            "old_name",
            "user@example.com",
            User.hash_password("secret1"),
            id=4,
        )
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [
            (user.username, user.password_hash),
            None,
        ]

        with patch(
            "database.user_repository.get_connection",
            return_value=connection,
        ):
            new_hash = UserRepository().update_profile(
                user.id,
                username="new_name",
                full_name="New Name",
                bio="A bio",
                current_password="secret1",
                new_password="newsecret",
            )

        self.assertTrue(User.verify_password("newsecret", new_hash))
        update_args = cursor.execute.call_args_list[-1].args
        self.assertIn("username = %s", update_args[0])
        self.assertIn("password_hash = %s", update_args[0])
        self.assertEqual(update_args[1][:3], ("new_name", "New Name", "A bio"))
        self.assertEqual(update_args[1][-1], user.id)
        connection.commit.assert_called_once_with()

    def test_update_profile_rejects_duplicate_username(self):
        user = User(
            "old_name",
            "user@example.com",
            User.hash_password("secret1"),
            id=4,
        )
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [
            (user.username, user.password_hash),
            (1,),
        ]

        with patch(
            "database.user_repository.get_connection",
            return_value=connection,
        ):
            with self.assertRaisesRegex(ValueError, "already in use"):
                UserRepository().update_profile(user.id, username="taken")

        self.assertEqual(cursor.execute.call_count, 2)
        connection.commit.assert_not_called()

    def test_update_profile_requires_current_password(self):
        user = User(
            "old_name",
            "user@example.com",
            User.hash_password("secret1"),
            id=4,
        )
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [
            (user.username, user.password_hash),
            None,
        ]

        with patch(
            "database.user_repository.get_connection",
            return_value=connection,
        ):
            with self.assertRaisesRegex(PermissionError, "current password"):
                UserRepository().update_profile(
                    user.id,
                    username="old_name",
                    current_password="wrong",
                    new_password="newsecret",
                )

        self.assertEqual(cursor.execute.call_count, 2)
        connection.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()

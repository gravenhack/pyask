import unittest
from unittest.mock import Mock, patch

from database.answer_repository import AnswerRepository
from database.permissions import HIDDEN_CONTENT_MESSAGE
from database.report_repository import ReportRepository
from models.report import Report
from models.user import User


class ModerationRepositoryTests(unittest.TestCase):
    def make_user(self, role, user_id):
        return User(
            f"{role}_{user_id}",
            f"{role}_{user_id}@example.com",
            "hash",
            role=role,
            id=user_id,
        )

    def test_reviewed_report_hides_target_in_same_transaction(self):
        moderator = self.make_user("moderator", 7)
        report = Report(
            reporter=self.make_user("user", 8),
            reason="Inappropriate",
            question_id=12,
            id=31,
        )
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [
            ("moderator",),
            (12, None, None, "Inappropriate"),
        ]

        with patch(
            "database.report_repository.get_connection",
            return_value=connection,
        ):
            ReportRepository().review(report, moderator)

        statements = [
            call.args[0]
            for call in cursor.execute.call_args_list
        ]
        hide_statement = next(
            statement for statement in statements
            if "INSERT IGNORE INTO hidden_content" in statement
        )
        self.assertIn("UPDATE reports", statements[-1])
        self.assertEqual(
            cursor.execute.call_args_list[2].args[1],
            (12, None, None, 31, 7, "Inappropriate"),
        )
        self.assertIsNotNone(hide_statement)
        connection.commit.assert_called_once_with()
        self.assertEqual(report.status, "reviewed")

    def test_dismissed_report_does_not_hide_target(self):
        moderator = self.make_user("moderator", 7)
        report = Report(
            reporter=self.make_user("user", 8),
            reason="Not a violation",
            answer_id=12,
            id=31,
        )
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.side_effect = [
            ("moderator",),
            (None, 12, None, "Not a violation"),
        ]

        with patch(
            "database.report_repository.get_connection",
            return_value=connection,
        ):
            ReportRepository().review(report, moderator, status="dismissed")

        statements = [
            call.args[0]
            for call in cursor.execute.call_args_list
        ]
        self.assertFalse(
            any("INSERT IGNORE INTO hidden_content" in s for s in statements)
        )
        self.assertIn("UPDATE reports", statements[-1])
        self.assertEqual(report.status, "dismissed")

    def test_hidden_answer_is_redacted_for_users_but_visible_to_moderators(self):
        row = {
            "answer_id": 3,
            "question_id": 4,
            "body": "Original answer",
            "hidden_id": 6,
            "created_at": None,
            "updated_at": None,
            "author_id": 5,
            "author_username": "author",
            "author_role": "user",
            "author_full_name": None,
            "voter_id": None,
            "vote_value": None,
        }

        for role, expected_body in (
            ("user", HIDDEN_CONTENT_MESSAGE),
            ("moderator", "Original answer"),
        ):
            with self.subTest(role=role):
                connection = Mock()
                connection.cursor.return_value.fetchall.return_value = [row]
                user = self.make_user(role, 7)
                with (
                    patch(
                        "database.answer_repository.get_connection",
                        return_value=connection,
                    ),
                    patch(
                        "database.answer_repository.can_view_hidden_content",
                        return_value=role == "moderator",
                    ),
                ):
                    answer = AnswerRepository().list_for_question(
                        4, viewer=user
                    )[0]

                self.assertEqual(answer.body, expected_body)
                self.assertTrue(answer.is_hidden)


if __name__ == "__main__":
    unittest.main()

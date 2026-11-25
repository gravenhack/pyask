import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QPushButton

from models.user import User
from ui import main_window as main


class EmptyQuestionRepository:
    def list_categories(self):
        return []

    def list_questions(self, **_filters):
        return []


class ReportsUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def make_user(self, role):
        return User(
            f"{role}_user",
            f"{role}@example.com",
            User.hash_password("secret1"),
            role=role,
            id=5,
        )

    def make_forum_window(self, user):
        with (
            patch(
                "ui.main_window.QuestionRepository",
                return_value=EmptyQuestionRepository(),
            ),
            patch("ui.main_window.AnswerRepository", return_value=object()),
            patch("ui.main_window.VoteRepository", return_value=object()),
            patch("ui.main_window.CommentRepository", return_value=object()),
            patch("ui.main_window.ReportRepository", return_value=object()),
            patch("ui.main_window.UserRepository", return_value=object()),
            patch("ui.main_window.AnalyticsRepository", return_value=Mock()),
        ):
            return main.ForumWindow(user)

    def test_reports_navigation_is_only_shown_to_admins(self):
        for role in ("user", "moderator"):
            with self.subTest(role=role):
                window = self.make_forum_window(self.make_user(role))
                self.assertIsNone(
                    window.findChild(QPushButton, "reportsNavButton")
                )
                window.close()

        admin_window = self.make_forum_window(self.make_user("admin"))
        self.assertIsNotNone(
            admin_window.findChild(QPushButton, "reportsNavButton")
        )
        admin_window.close()

    def test_reports_dialog_rejects_non_admin_and_offers_two_csv_exports(self):
        with self.assertRaises(PermissionError):
            main.ReportsDialog(self.make_user("user"), Mock())

        dialog = main.ReportsDialog(self.make_user("admin"), Mock())
        self.assertEqual(
            dialog.questions_export_button.text(),
            "Exporter les questions (CSV)",
        )
        self.assertEqual(
            dialog.answers_export_button.text(),
            "Exporter les réponses (CSV)",
        )
        dialog.close()


if __name__ == "__main__":
    unittest.main()

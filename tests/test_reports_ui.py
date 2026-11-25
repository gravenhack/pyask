import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QPushButton

from models.user import User
from ui import main_window as main


class EmptyQuestionRepository:
    def list_categories(self):
        return []

    def count_questions(self, **_filters):
        return 0

    def list_questions(self, **_filters):
        return []

    def list_popular_questions(self, **_filters):
        return []

    def list_trending_tags(self, **_filters):
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

    def test_closing_moderation_refreshes_the_question_feed(self):
        window = self.make_forum_window(self.make_user("moderator"))
        with (
            patch("ui.main_window.ModerationDialog") as dialog_class,
            patch.object(window, "_refresh_questions") as refresh_questions,
        ):
            dialog_class.return_value.exec_.return_value = 0

            window._open_moderation()

        refresh_questions.assert_called_once_with()
        window.close()

    def test_visible_replies_remain_reportable_when_question_is_hidden(self):
        window = self.make_forum_window(self.make_user("user"))
        window.current_question = SimpleNamespace(is_hidden=True)
        window._selected_answer = Mock(
            return_value=SimpleNamespace(is_hidden=False)
        )
        window._selected_comment = Mock(return_value=None)

        window._update_discussion_action_state()
        self.assertTrue(window.report_button.isEnabled())

        window._selected_answer.return_value = None
        window._selected_comment.return_value = SimpleNamespace(is_hidden=False)
        window._update_discussion_action_state()
        self.assertTrue(window.report_button.isEnabled())

        window._selected_comment.return_value = None
        window._update_discussion_action_state()
        self.assertFalse(window.report_button.isEnabled())
        window.close()

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
        self.assertEqual(
            [
                dialog.period_filter.itemData(index)
                for index in range(dialog.period_filter.count())
            ],
            [None, 7, 30, 90],
        )
        self.assertEqual(
            dialog.bundle_export_button.text(),
            "Exporter les deux rapports (ZIP)",
        )
        dialog.close()

    def test_csv_export_uses_selected_period(self):
        admin = self.make_user("admin")
        analytics_repository = Mock()
        analytics_repository.question_report.return_value = [{"id": 1}]
        dialog = main.ReportsDialog(admin, analytics_repository)
        dialog.period_filter.setCurrentIndex(2)

        with (
            patch(
                "ui.main_window.QFileDialog.getSaveFileName",
                return_value=("/tmp/questions.csv", "CSV"),
            ),
            patch("ui.main_window.export_csv") as export_csv,
            patch.object(main.QMessageBox, "information"),
        ):
            dialog._export_question_report()

        analytics_repository.question_report.assert_called_once_with(admin, 30)
        export_csv.assert_called_once_with(
            [{"id": 1}],
            "/tmp/questions.csv",
            main.QUESTION_REPORT_FIELDS,
        )
        dialog.close()

    def test_zip_export_includes_both_reports_for_selected_period(self):
        admin = self.make_user("admin")
        analytics_repository = Mock()
        analytics_repository.question_report.return_value = [{"id": 1}]
        analytics_repository.answer_report.return_value = [{"id": 2}]
        dialog = main.ReportsDialog(admin, analytics_repository)
        dialog.period_filter.setCurrentIndex(3)

        with (
            patch(
                "ui.main_window.QFileDialog.getSaveFileName",
                return_value=("/tmp/reports.zip", "ZIP"),
            ),
            patch("ui.main_window.export_reports_zip") as export_zip,
            patch.object(main.QMessageBox, "information"),
        ):
            dialog._export_reports_zip()

        analytics_repository.question_report.assert_called_once_with(admin, 90)
        analytics_repository.answer_report.assert_called_once_with(admin, 90)
        export_zip.assert_called_once_with(
            [{"id": 1}],
            [{"id": 2}],
            "/tmp/reports.zip",
            main.QUESTION_REPORT_FIELDS,
            main.ANSWER_REPORT_FIELDS,
        )
        dialog.close()


if __name__ == "__main__":
    unittest.main()

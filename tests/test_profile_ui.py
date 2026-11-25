import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QPushButton,
    QScrollArea,
    QSplitter,
)

from ui import main_window as main
from models.user import User


class EmptyQuestionRepository:
    def list_categories(self):
        return []

    def list_questions(self, **_filters):
        return []


class RecordingCategoryQuestionRepository:
    def __init__(self):
        self.filters = []

    def list_categories(self):
        return [SimpleNamespace(id=7, name="Python")]

    def list_questions(self, **filters):
        self.filters.append(filters)
        return []


class RecordingUserRepository:
    def __init__(self):
        self.updated_profile = None

    def update_profile(self, user_id, full_name=None, bio=None):
        self.updated_profile = (user_id, full_name, bio)


class ProfileUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def make_user(self):
        return User(
            "profile_user",
            "profile@example.com",
            User.hash_password("secret1"),
            id=5,
            full_name="Initial Name",
            bio="Initial bio",
        )

    def test_profile_dialog_accepts_bio_at_limit(self):
        dialog = main.ProfileDialog(self.make_user())
        dialog.bio_input.setPlainText("b" * 255)

        dialog.buttons.button(QDialogButtonBox.Save).click()

        self.assertEqual(dialog.result(), QDialog.Accepted)
        dialog.close()

    def test_profile_dialog_rejects_bio_over_limit(self):
        dialog = main.ProfileDialog(self.make_user())
        dialog.bio_input.setPlainText("b" * 256)

        with patch.object(main.QMessageBox, "warning") as warning:
            dialog.buttons.button(QDialogButtonBox.Save).click()

        self.assertEqual(dialog.result(), QDialog.Rejected)
        warning.assert_called_once()
        dialog.close()

    def test_forum_uses_social_feed_three_column_layout(self):
        question_repository = EmptyQuestionRepository()
        with (
            patch("ui.main_window.QuestionRepository", return_value=question_repository),
            patch("ui.main_window.AnswerRepository", return_value=object()),
            patch("ui.main_window.VoteRepository", return_value=object()),
            patch("ui.main_window.CommentRepository", return_value=object()),
            patch("ui.main_window.ReportRepository", return_value=object()),
            patch("ui.main_window.UserRepository", return_value=object()),
            patch("ui.main_window.AnalyticsRepository", return_value=object()),
        ):
            window = main.ForumWindow(self.make_user())

        splitter = window.findChild(QSplitter)
        self.assertIsNotNone(splitter)
        self.assertEqual(
            [splitter.widget(index).objectName() for index in range(splitter.count())],
            ["sidebarScroll", "feedScroll", "asideScroll"],
        )
        self.assertIsNotNone(window.findChild(QScrollArea, "storiesScroll"))
        window.show()
        self.application.processEvents()
        window.resize(1000, 680)
        self.application.processEvents()
        self.assertTrue(window.findChild(QScrollArea, "asideScroll").isHidden())
        window.resize(1360, 860)
        self.application.processEvents()
        self.assertFalse(window.findChild(QScrollArea, "asideScroll").isHidden())
        window.close()

    def test_sidebar_category_filter_is_visible_and_filters_the_feed(self):
        question_repository = RecordingCategoryQuestionRepository()
        with (
            patch(
                "ui.main_window.QuestionRepository",
                return_value=question_repository,
            ),
            patch("ui.main_window.AnswerRepository", return_value=object()),
            patch("ui.main_window.VoteRepository", return_value=object()),
            patch("ui.main_window.CommentRepository", return_value=object()),
            patch("ui.main_window.ReportRepository", return_value=object()),
            patch("ui.main_window.UserRepository", return_value=object()),
            patch("ui.main_window.AnalyticsRepository", return_value=object()),
        ):
            window = main.ForumWindow(self.make_user())

        self.assertFalse(window.category_filter.isHidden())
        self.assertEqual(
            window.category_filter.itemText(0),
            "Toutes les catégories",
        )
        self.assertEqual(window.category_filter.itemText(1), "Python")
        window.category_filter.setCurrentIndex(1)
        self.assertEqual(question_repository.filters[-1]["category_id"], 7)
        self.assertTrue(window.category_nav_buttons[7].isChecked())
        window.close()

    def test_csv_export_defaults_to_exports_directory(self):
        admin = User(
            "report_admin",
            "reports@example.com",
            User.hash_password("secret1"),
            role="admin",
            id=15,
        )
        dialog = main.ReportsDialog(admin, Mock())

        with patch(
            "ui.main_window.QFileDialog.getSaveFileName",
            return_value=("", ""),
        ) as get_save_file_name:
            dialog._export_report("questions.csv", lambda _admin: [], ())

        expected_path = (
            Path(main.__file__).resolve().parent.parent
            / "exports"
            / "questions.csv"
        )
        self.assertEqual(get_save_file_name.call_args.args[2], str(expected_path))
        dialog.close()

    def test_profile_save_updates_repository_and_current_user(self):
        user = self.make_user()
        user_repository = RecordingUserRepository()
        question_repository = EmptyQuestionRepository()
        with (
            patch("ui.main_window.QuestionRepository", return_value=question_repository),
            patch("ui.main_window.AnswerRepository", return_value=object()),
            patch("ui.main_window.VoteRepository", return_value=object()),
            patch("ui.main_window.CommentRepository", return_value=object()),
            patch("ui.main_window.ReportRepository", return_value=object()),
            patch("ui.main_window.UserRepository", return_value=user_repository),
            patch("ui.main_window.AnalyticsRepository", return_value=object()),
        ):
            window = main.ForumWindow(user)

        profile_dialog = Mock()
        profile_dialog.exec_.return_value = QDialog.Accepted
        profile_dialog.full_name_input.text.return_value = "  Ada Lovelace  "
        profile_dialog.bio_input.toPlainText.return_value = "  A short bio.  "
        profile_button = window.findChild(QPushButton, "profileButton")
        self.assertIsNotNone(profile_button)

        with (
            patch("ui.main_window.ProfileDialog", return_value=profile_dialog),
            patch.object(main.QMessageBox, "information"),
        ):
            profile_button.click()

        self.assertEqual(
            user_repository.updated_profile,
            (5, "Ada Lovelace", "A short bio."),
        )
        self.assertEqual(user.full_name, "Ada Lovelace")
        self.assertEqual(user.bio, "A short bio.")
        window.close()


if __name__ == "__main__":
    unittest.main()

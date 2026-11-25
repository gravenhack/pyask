import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QApplication, QPushButton

from ui import main_window as main
from models.user import User


class EmptyQuestionRepository:
    def list_categories(self):
        return []

    def list_questions(self, **_filters):
        return []


class AdminUserRepository:
    def __init__(self):
        self.changed_role = None

    def list_users(self, admin):
        return [
            {"id": admin.id, "username": admin.username, "role": admin.role},
            {"id": 12, "username": "member", "role": "user"},
        ]

    def change_role(self, user_id, role, admin):
        self.changed_role = (user_id, role, admin.id)


class FakeSignal:
    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in self.slots:
            slot(*args)


class AuthUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def make_user(self):
        return User(
            "auth_user",
            "auth@example.com",
            User.hash_password("secret1"),
            id=9,
        )

    def test_application_background_asset_is_loaded_behind_login(self):
        self.assertTrue(main.APP_BACKGROUND_PATH.is_file())
        self.assertNotIn("APP_BACKGROUND_URL", main.APP_STYLESHEET)

        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(main.APP_STYLESHEET)
        window = main.LoginWindow()
        try:
            window.resize(520, 600)
            window.show()
            self.application.processEvents()

            rendered = QImage(window.size(), QImage.Format_ARGB32)
            rendered.fill(Qt.transparent)
            painter = QPainter(rendered)
            window.render(painter)
            painter.end()

            corner = rendered.pixelColor(4, 4)
            self.assertNotEqual(corner, rendered.pixelColor(515, 4))
        finally:
            window.close()
            self.application.setStyleSheet(previous_stylesheet)

    def test_forum_window_keeps_solid_dark_background(self):
        question_repository = EmptyQuestionRepository()
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

        previous_stylesheet = self.application.styleSheet()
        self.application.setStyleSheet(main.APP_STYLESHEET)
        try:
            window.resize(1360, 860)
            window.show()
            self.application.processEvents()

            rendered = QImage(window.size(), QImage.Format_ARGB32)
            rendered.fill(Qt.transparent)
            painter = QPainter(rendered)
            window.render(painter)
            painter.end()

            self.assertEqual(
                rendered.pixelColor(1350, 850).name(),
                "#0c0d0f",
            )
        finally:
            window.close()
            self.application.setStyleSheet(previous_stylesheet)

    def test_reset_for_login_clears_credentials_and_exits_registration(self):
        window = main.LoginWindow()
        window._toggle_mode()
        window.username_input.setText("auth_user")
        window.email_input.setText("auth@example.com")
        window.password_input.setText("secret1")

        window.reset_for_login()

        self.assertFalse(window.is_registering)
        self.assertEqual(window.username_input.text(), "")
        self.assertEqual(window.email_input.text(), "")
        self.assertEqual(window.password_input.text(), "")
        self.assertTrue(window.email_input.isHidden())
        window.close()

    def test_logout_button_emits_logged_out_signal(self):
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

        logout_requests = []
        window.logged_out.connect(lambda: logout_requests.append(True))
        logout_button = window.findChild(QPushButton, "logoutButton")
        self.assertIsNotNone(logout_button)

        logout_button.click()

        self.assertEqual(logout_requests, [True])
        window.close()

    def test_admin_role_controls_are_disabled_for_the_current_admin(self):
        admin = User(
            "admin",
            "admin@example.com",
            User.hash_password("secret1"),
            role="admin",
            id=1,
        )
        user_repository = AdminUserRepository()
        dialog = main.AdministrationDialog(
            admin,
            user_repository,
            question_repository=object(),
        )

        self.assertEqual(dialog.user_input.currentData(), admin.id)
        self.assertFalse(dialog.role_input.isEnabled())
        self.assertFalse(dialog.role_button.isEnabled())
        self.assertIn("propre rôle", dialog.role_status.text())

        dialog.role_input.setCurrentText("user")
        dialog._change_role()
        self.assertIsNone(user_repository.changed_role)

        dialog.user_input.setCurrentIndex(1)
        self.assertTrue(dialog.role_input.isEnabled())
        self.assertTrue(dialog.role_button.isEnabled())
        dialog.close()

    def test_main_returns_to_login_after_logout(self):
        user = self.make_user()

        class FakeLoginWindow:
            def __init__(self):
                self.authenticated = FakeSignal()
                self.visible = False
                self.reset_called = False

            def show(self):
                self.visible = True

            def hide(self):
                self.visible = False

            def reset_for_login(self):
                self.reset_called = True

            def raise_(self):
                pass

            def activateWindow(self):
                pass

        class FakeForumWindow:
            def __init__(self, _user):
                self.logged_out = FakeSignal()
                self.closed = False
                self.deleted = False
                self.login_visible_when_closed = False

            def show(self):
                pass

            def close(self):
                self.closed = True
                self.login_visible_when_closed = login_window.visible

            def deleteLater(self):
                self.deleted = True

        login_window = FakeLoginWindow()
        forum_windows = []

        class FakeApplication:
            def __init__(self, _arguments):
                pass

            def setStyleSheet(self, _stylesheet):
                pass

            def exec_(self):
                login_window.authenticated.emit(user)
                forum_windows[0].logged_out.emit()
                return 0

        def create_forum_window(account):
            forum = FakeForumWindow(account)
            forum_windows.append(forum)
            return forum

        with (
            patch("ui.main_window.QApplication", FakeApplication),
            patch("ui.main_window.LoginWindow", return_value=login_window),
            patch("ui.main_window.ForumWindow", side_effect=create_forum_window),
        ):
            result = main.main()

        self.assertEqual(result, 0)
        self.assertTrue(login_window.visible)
        self.assertTrue(login_window.reset_called)
        self.assertTrue(forum_windows[0].closed)
        self.assertTrue(forum_windows[0].deleted)
        self.assertTrue(forum_windows[0].login_visible_when_closed)


if __name__ == "__main__":
    unittest.main()

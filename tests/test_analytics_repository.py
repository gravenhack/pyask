import unittest
from unittest.mock import Mock, patch

from database.analytics_repository import AnalyticsRepository
from models.user import User


class AnalyticsRepositoryTests(unittest.TestCase):
    def make_user(self, role):
        return User(
            f"{role}_user",
            f"{role}@example.com",
            User.hash_password("secret1"),
            role=role,
            id=5,
        )

    def test_both_reports_reject_non_admin_users(self):
        repository = AnalyticsRepository()
        user = self.make_user("user")

        for report_method in (
            repository.question_report,
            repository.answer_report,
        ):
            with self.subTest(report=report_method.__name__):
                connection = Mock()
                permission_cursor = connection.cursor.return_value
                with patch(
                    "database.analytics_repository.get_connection",
                    return_value=connection,
                ):
                    with self.assertRaises(PermissionError):
                        report_method(user)

                permission_cursor.execute.assert_not_called()
                permission_cursor.close.assert_called_once()
                connection.close.assert_called_once()

    def test_both_reports_check_active_admin_role_before_querying(self):
        repository = AnalyticsRepository()
        admin = self.make_user("admin")

        for report_method in (
            repository.question_report,
            repository.answer_report,
        ):
            with self.subTest(report=report_method.__name__):
                connection = Mock()
                permission_cursor = Mock()
                permission_cursor.fetchone.return_value = ("admin",)
                report_cursor = Mock()
                report_cursor.fetchall.return_value = [{"row": "result"}]
                connection.cursor.side_effect = [
                    permission_cursor,
                    report_cursor,
                ]

                with patch(
                    "database.analytics_repository.get_connection",
                    return_value=connection,
                ):
                    rows = report_method(admin)

                self.assertEqual(rows, [{"row": "result"}])
                permission_cursor.execute.assert_called_once_with(
                    "SELECT role FROM users WHERE id = %s",
                    (admin.id,),
                )
                report_cursor.execute.assert_called_once()
                permission_cursor.close.assert_called_once()
                report_cursor.close.assert_called_once()
                connection.close.assert_called_once()

    def test_selected_period_is_applied_to_question_and_answer_dates(self):
        repository = AnalyticsRepository()
        admin = self.make_user("admin")

        for report_method, expected_column in (
            (repository.question_report, "created_at"),
            (repository.answer_report, "a.created_at"),
        ):
            with self.subTest(report=report_method.__name__):
                connection = Mock()
                permission_cursor = Mock()
                permission_cursor.fetchone.return_value = ("admin",)
                report_cursor = Mock()
                report_cursor.fetchall.return_value = []
                connection.cursor.side_effect = [
                    permission_cursor,
                    report_cursor,
                ]

                with patch(
                    "database.analytics_repository.get_connection",
                    return_value=connection,
                ):
                    report_method(admin, period_days=30)

                query = report_cursor.execute.call_args.args[0]
                self.assertIn(
                    f"{expected_column} >= DATE_SUB(CURRENT_TIMESTAMP, "
                    "INTERVAL 30 DAY)",
                    query,
                )

    def test_reports_reject_unsupported_periods(self):
        repository = AnalyticsRepository()
        admin = self.make_user("admin")

        for report_method in (
            repository.question_report,
            repository.answer_report,
        ):
            with self.subTest(report=report_method.__name__):
                with patch(
                    "database.analytics_repository.get_connection"
                ) as get_connection:
                    with self.assertRaisesRegex(ValueError, "7, 30, or 90"):
                        report_method(admin, period_days=14)
                get_connection.assert_not_called()


if __name__ == "__main__":
    unittest.main()

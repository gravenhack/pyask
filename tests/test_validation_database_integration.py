import os
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from config import get_database_settings
from database.analytics_repository import (
    ANSWER_REPORT_FIELDS,
    QUESTION_REPORT_FIELDS,
    AnalyticsRepository,
)
from database.connection import get_connection
from database.question_repository import QuestionRepository
from database.report_repository import ReportRepository
from models.user import User
from reporting.csv_exporter import export_reports_zip


VALIDATION_DATABASE = "pyask_validation_20261124"
RUN_INTEGRATION_TESTS = (
    os.environ.get("PYASK_RUN_DB_INTEGRATION_TESTS") == "1"
)


@unittest.skipUnless(
    RUN_INTEGRATION_TESTS,
    "Set PYASK_RUN_DB_INTEGRATION_TESTS=1 to run read-only database checks.",
)
class ValidationDatabaseIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        configured_database = get_database_settings()["database"]
        if configured_database != VALIDATION_DATABASE:
            raise RuntimeError(
                "Integration tests are restricted to "
                f"{VALIDATION_DATABASE}; configured database is "
                f"{configured_database}."
            )

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT id FROM users WHERE role = %s ORDER BY id LIMIT 1",
                ("admin",),
            )
            admin_record = cursor.fetchone()
        finally:
            cursor.close()
            connection.close()

        if admin_record is None:
            raise RuntimeError(
                "The validation database must contain an admin account."
            )

        cls.admin = User(
            username="integration_test_admin",
            email="integration_test_admin@example.invalid",
            password_hash="unused",
            role="admin",
            id=admin_record[0],
        )
        cls.question_repository = QuestionRepository()
        cls.analytics_repository = AnalyticsRepository()
        cls.report_repository = ReportRepository()

    def test_question_count_and_pages_are_consistent(self):
        total = self.question_repository.count_questions()
        first_page = self.question_repository.list_questions(
            page_size=2,
            offset=0,
        )
        second_page = self.question_repository.list_questions(
            page_size=2,
            offset=2,
        )

        self.assertLessEqual(len(first_page), 2)
        self.assertLessEqual(len(second_page), 2)
        self.assertLessEqual(len(first_page) + len(second_page), total)
        self.assertFalse(
            {question.id for question in first_page}
            & {question.id for question in second_page}
        )

        if first_page:
            question = first_page[0]
            matching_questions = self.question_repository.list_questions(
                search_text=question.title,
                category_id=question.category.id,
                page_size=5,
            )
            self.assertIn(
                question.id,
                {matching_question.id for matching_question in matching_questions},
            )

    def test_reports_and_moderation_queue_are_readable(self):
        question_rows = self.analytics_repository.question_report(
            self.admin,
            period_days=30,
        )
        answer_rows = self.analytics_repository.answer_report(
            self.admin,
            period_days=30,
        )
        pending_reports = self.report_repository.list_pending(self.admin)

        self.assertIsInstance(question_rows, list)
        self.assertIsInstance(answer_rows, list)
        self.assertIsInstance(pending_reports, list)

        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "reports.zip"
            export_reports_zip(
                question_rows,
                answer_rows,
                archive_path,
                QUESTION_REPORT_FIELDS,
                ANSWER_REPORT_FIELDS,
            )

            with ZipFile(archive_path) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"questions.csv", "answers.csv"},
                )
                self.assertTrue(archive.testzip() is None)


if __name__ == "__main__":
    unittest.main()

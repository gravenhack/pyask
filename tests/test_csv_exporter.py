import csv
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from reporting.csv_exporter import export_csv, export_reports_zip


class CsvExporterTests(unittest.TestCase):
    def test_export_csv_writes_utf8_bom_and_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "questions.csv"

            export_csv(
                [{"id": 1, "title": "Une question"}],
                path,
                ("id", "title"),
            )

            content = path.read_bytes()
            self.assertTrue(content.startswith(b"\xef\xbb\xbf"))
            rows = list(csv.DictReader(content.decode("utf-8-sig").splitlines()))
            self.assertEqual(rows, [{"id": "1", "title": "Une question"}])

    def test_zip_contains_two_separate_utf8_csv_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reports.zip"

            export_reports_zip(
                [{"id": 1, "title": "Question"}],
                [{"id": 2, "body": "Réponse"}],
                path,
                ("id", "title"),
                ("id", "body"),
            )

            with ZipFile(path) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"questions.csv", "answers.csv"},
                )
                question_csv = archive.read("questions.csv")
                answer_csv = archive.read("answers.csv")

            self.assertTrue(question_csv.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(answer_csv.startswith(b"\xef\xbb\xbf"))
            self.assertIn("Question", question_csv.decode("utf-8-sig"))
            self.assertIn("Réponse", answer_csv.decode("utf-8-sig"))

    def test_invalid_rows_do_not_create_partial_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reports.zip"

            with self.assertRaises(ValueError):
                export_reports_zip(
                    [{"unexpected": "field"}],
                    [],
                    path,
                    ("id",),
                    ("id",),
                )

            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()

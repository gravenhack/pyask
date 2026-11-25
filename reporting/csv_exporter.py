import csv
import io
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def _csv_bytes(rows, fieldnames):
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return csv_buffer.getvalue().encode("utf-8-sig")


def export_csv(rows, file_path, fieldnames):
    Path(file_path).write_bytes(_csv_bytes(rows, fieldnames))


def export_reports_zip(
    question_rows,
    answer_rows,
    file_path,
    question_fields,
    answer_fields,
):
    question_csv = _csv_bytes(question_rows, question_fields)
    answer_csv = _csv_bytes(answer_rows, answer_fields)
    with ZipFile(file_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("questions.csv", question_csv)
        archive.writestr("answers.csv", answer_csv)

import csv
from pathlib import Path


def export_csv(rows, file_path, fieldnames):
    with Path(file_path).open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

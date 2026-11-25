from datetime import datetime

import mysql.connector

from database.connection import get_connection
from database.permissions import require_moderator


class ReportRepository:
    def list_pending(self, moderator):
        connection = get_connection()
        cursor = connection.cursor()
        try:
            require_moderator(cursor, moderator)
            cursor.execute(
                """
                SELECT
                    r.id,
                    r.reporter_id,
                    reporter.username AS reporter_username,
                    r.reason,
                    r.question_id,
                    r.answer_id,
                    r.comment_id,
                    r.created_at,
                    CASE
                        WHEN r.question_id IS NOT NULL THEN 'question'
                        WHEN r.answer_id IS NOT NULL THEN 'answer'
                        ELSE 'comment'
                    END AS target_type,
                    CASE
                        WHEN r.question_id IS NOT NULL THEN reported_question.title
                        WHEN r.answer_id IS NOT NULL THEN answer_question.title
                        ELSE COALESCE(
                            comment_question.title,
                            comment_answer_question.title,
                            ''
                        )
                    END AS target_context,
                    CASE
                        WHEN r.question_id IS NOT NULL THEN reported_question.body
                        WHEN r.answer_id IS NOT NULL THEN reported_answer.body
                        ELSE reported_comment.body
                    END AS target_content
                FROM reports r
                JOIN users reporter ON reporter.id = r.reporter_id
                LEFT JOIN questions reported_question
                    ON reported_question.id = r.question_id
                LEFT JOIN answers reported_answer
                    ON reported_answer.id = r.answer_id
                LEFT JOIN questions answer_question
                    ON answer_question.id = reported_answer.question_id
                LEFT JOIN comments reported_comment
                    ON reported_comment.id = r.comment_id
                LEFT JOIN questions comment_question
                    ON comment_question.id = reported_comment.question_id
                LEFT JOIN answers comment_answer
                    ON comment_answer.id = reported_comment.answer_id
                LEFT JOIN questions comment_answer_question
                    ON comment_answer_question.id = comment_answer.question_id
                WHERE r.status = 'pending'
                ORDER BY r.created_at, r.id
                """
            )
            columns = [column[0] for column in cursor.description]
            return [
                dict(zip(columns, row))
                for row in cursor.fetchall()
            ]
        finally:
            cursor.close()
            connection.close()

    def create(self, report):
        if report.reporter.id is None:
            raise ValueError("The reporter must be saved first.")

        target_column, target_id = self._target(report)
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT id FROM reports
                WHERE reporter_id = %s AND {target_column} = %s
                """,
                (report.reporter.id, target_id),
            )
            if cursor.fetchone() is not None:
                raise ValueError("This user has already reported this content.")

            cursor.execute(
                """
                INSERT INTO reports (
                    reporter_id, question_id, answer_id, comment_id,
                    reason, status, reviewed_by, reviewed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    report.reporter.id,
                    report.question_id,
                    report.answer_id,
                    report.comment_id,
                    report.reason,
                    report.status,
                    report.reviewed_by.id if report.reviewed_by else None,
                    report.reviewed_at,
                ),
            )
            report_id = cursor.lastrowid
            connection.commit()
        except mysql.connector.Error:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
        report.id = report_id
        return report

    def review(self, report, moderator, status="reviewed"):
        if report.id is None:
            raise ValueError("The report must be saved before review.")
        if status not in ("reviewed", "dismissed"):
            raise ValueError("A reviewed report must be 'reviewed' or 'dismissed'.")

        reviewed_at = datetime.now()
        connection = get_connection()
        cursor = connection.cursor()
        try:
            require_moderator(cursor, moderator)
            cursor.execute(
                """
                SELECT question_id, answer_id, comment_id, reason
                FROM reports
                WHERE id = %s
                """,
                (report.id,),
            )
            target = cursor.fetchone()
            if target is None:
                raise LookupError(f"Report {report.id} was not found.")

            if status == "reviewed":
                question_id, answer_id, comment_id, reason = target
                if sum(value is not None for value in (
                    question_id, answer_id, comment_id
                )) != 1:
                    raise ValueError(
                        "A report must target exactly one content item."
                    )
                cursor.execute(
                    """
                    INSERT IGNORE INTO hidden_content (
                        question_id, answer_id, comment_id,
                        report_id, moderator_id, reason
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        question_id,
                        answer_id,
                        comment_id,
                        report.id,
                        moderator.id,
                        reason,
                    ),
                )
            cursor.execute(
                """
                UPDATE reports
                SET status = %s, reviewed_by = %s, reviewed_at = %s
                WHERE id = %s
                """,
                (status, moderator.id, reviewed_at, report.id),
            )
            connection.commit()
        except (mysql.connector.Error, LookupError, ValueError):
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

        report.status = status
        report.reviewed_by = moderator
        report.reviewed_at = reviewed_at
        return report

    @staticmethod
    def _target(report):
        targets = (
            ("question_id", report.question_id),
            ("answer_id", report.answer_id),
            ("comment_id", report.comment_id),
        )
        if sum(target_id is not None for _, target_id in targets) != 1:
            raise ValueError("A report must target exactly one content item.")
        if report.question_id is not None:
            return "question_id", report.question_id
        if report.answer_id is not None:
            return "answer_id", report.answer_id
        if report.comment_id is not None:
            return "comment_id", report.comment_id
        raise ValueError("A report must target one content item.")

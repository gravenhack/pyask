from database.connection import get_connection
from database.permissions import require_admin

QUESTION_REPORT_FIELDS = (
    "question_id",
    "title",
    "body",
    "author",
    "category",
    "tags",
    "created_at",
    "answer_count",
    "vote_score",
)

ANSWER_REPORT_FIELDS = (
    "answer_id",
    "question_id",
    "question_title",
    "author",
    "body",
    "created_at",
    "vote_score",
)


class AnalyticsRepository:
    def question_report(self, admin):
        return self._report_rows(
            admin,
            """
            SELECT
                question_id,
                title,
                body,
                author_username AS author,
                category_name AS category,
                tags,
                created_at,
                answer_count,
                vote_score
            FROM question_statistics
            ORDER BY created_at DESC, question_id DESC
            """,
        )

    def answer_report(self, admin):
        return self._report_rows(
            admin,
            """
            SELECT
                a.id AS answer_id,
                a.question_id,
                q.title AS question_title,
                u.username AS author,
                a.body,
                a.created_at,
                (
                    SELECT COALESCE(SUM(v.vote_value), 0)
                    FROM answer_votes v
                    WHERE v.answer_id = a.id
                ) AS vote_score
            FROM answers a
            JOIN questions q ON q.id = a.question_id
            JOIN users u ON u.id = a.user_id
            ORDER BY a.created_at DESC, a.id DESC
            """,
        )

    def _report_rows(self, admin, query):
        connection = get_connection()
        try:
            permission_cursor = connection.cursor()
            try:
                require_admin(permission_cursor, admin)
            finally:
                permission_cursor.close()

            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute(query)
                return cursor.fetchall()
            finally:
                cursor.close()
        finally:
            connection.close()

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
    @staticmethod
    def _period_filter(column, period_days):
        if period_days is None:
            return ""
        if (
            isinstance(period_days, bool)
            or not isinstance(period_days, int)
            or period_days not in (7, 30, 90)
        ):
            raise ValueError("Report period must be 7, 30, or 90 days.")
        return (
            f"WHERE {column} >= "
            f"DATE_SUB(CURRENT_TIMESTAMP, INTERVAL {period_days} DAY)"
        )

    def question_report(self, admin, period_days=None):
        period_filter = self._period_filter("created_at", period_days)
        return self._report_rows(
            admin,
            f"""
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
            {period_filter}
            ORDER BY created_at DESC, question_id DESC
            """,
        )

    def answer_report(self, admin, period_days=None):
        period_filter = self._period_filter("a.created_at", period_days)
        return self._report_rows(
            admin,
            f"""
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
            {period_filter}
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

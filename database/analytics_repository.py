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
    "like_count",
    "dislike_count",
)

ANSWER_REPORT_FIELDS = (
    "answer_id",
    "question_id",
    "question_title",
    "author",
    "body",
    "created_at",
    "like_count",
    "dislike_count",
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
        period_filter = self._period_filter("qs.created_at", period_days)
        return self._report_rows(
            admin,
            f"""
            SELECT
                qs.question_id,
                qs.title,
                qs.body,
                qs.author_username AS author,
                qs.category_name AS category,
                qs.tags,
                qs.created_at,
                qs.answer_count,
                COALESCE(qvc.like_count, 0) AS like_count,
                COALESCE(qvc.dislike_count, 0) AS dislike_count
            FROM question_statistics qs
            LEFT JOIN (
                SELECT
                    a.question_id,
                    SUM(CASE WHEN v.vote_value = 1 THEN 1 ELSE 0 END)
                        AS like_count,
                    SUM(CASE WHEN v.vote_value = -1 THEN 1 ELSE 0 END)
                        AS dislike_count
                FROM answers a
                JOIN answer_votes v ON v.answer_id = a.id
                GROUP BY a.question_id
            ) qvc ON qvc.question_id = qs.question_id
            {period_filter}
            ORDER BY qs.created_at DESC, qs.question_id DESC
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
                    SELECT COUNT(*)
                    FROM answer_votes v
                    WHERE v.answer_id = a.id AND v.vote_value = 1
                ) AS like_count,
                (
                    SELECT COUNT(*)
                    FROM answer_votes v
                    WHERE v.answer_id = a.id AND v.vote_value = -1
                ) AS dislike_count
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

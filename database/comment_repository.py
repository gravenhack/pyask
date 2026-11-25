import mysql.connector

from database.connection import get_connection
from database.permissions import HIDDEN_CONTENT_MESSAGE, can_view_hidden_content
from models.comment import Comment
from models.user_summary import UserSummary


class CommentRepository:
    def list_for_question(self, question_id, viewer=None):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            can_view_originals = can_view_hidden_content(connection, viewer)
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.question_id,
                    c.answer_id,
                    c.body,
                    hc.id AS hidden_id,
                    c.created_at,
                    u.id AS author_id,
                    u.username AS author_username,
                    u.role AS author_role,
                    u.full_name AS author_full_name
                FROM comments c
                JOIN users u ON u.id = c.user_id
                LEFT JOIN hidden_content hc ON hc.comment_id = c.id
                LEFT JOIN answers a ON a.id = c.answer_id
                WHERE c.question_id = %s OR a.question_id = %s
                ORDER BY c.created_at, c.id
                """,
                (question_id, question_id),
            )
            return [
                Comment(
                    author=UserSummary(
                        username=record["author_username"],
                        id=record["author_id"],
                        role=record["author_role"],
                        full_name=record["author_full_name"],
                    ),
                    body=(
                        record["body"]
                        if can_view_originals or record["hidden_id"] is None
                        else HIDDEN_CONTENT_MESSAGE
                    ),
                    question_id=record["question_id"],
                    answer_id=record["answer_id"],
                    id=record["id"],
                    created_at=record["created_at"],
                    is_hidden=record["hidden_id"] is not None,
                )
                for record in cursor.fetchall()
            ]
        finally:
            cursor.close()
            connection.close()

    def create(self, comment):
        if comment.author.id is None:
            raise ValueError("The comment author must be saved first.")
        if (comment.question_id is None) == (comment.answer_id is None):
            raise ValueError("A comment must target exactly one question or answer.")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            if comment.question_id is not None:
                cursor.execute(
                    "SELECT 1 FROM hidden_content WHERE question_id = %s",
                    (comment.question_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT 1
                    FROM answers a
                    LEFT JOIN hidden_content hq ON hq.question_id = a.question_id
                    LEFT JOIN hidden_content ha ON ha.answer_id = a.id
                    WHERE a.id = %s AND (hq.id IS NOT NULL OR ha.id IS NOT NULL)
                    """,
                    (comment.answer_id,),
                )
            if cursor.fetchone() is not None:
                raise ValueError("Hidden content cannot receive comments.")
            cursor.execute(
                """
                INSERT INTO comments (user_id, question_id, answer_id, body)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    comment.author.id,
                    comment.question_id,
                    comment.answer_id,
                    comment.body,
                ),
            )
            comment_id = cursor.lastrowid
            connection.commit()
        except mysql.connector.Error:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
        comment.id = comment_id
        return comment

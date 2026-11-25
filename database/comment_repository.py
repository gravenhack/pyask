import mysql.connector

from database.connection import get_connection
from models.comment import Comment
from models.user_summary import UserSummary


class CommentRepository:
    def list_for_question(self, question_id):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    c.id,
                    c.question_id,
                    c.answer_id,
                    c.body,
                    c.created_at,
                    u.id AS author_id,
                    u.username AS author_username,
                    u.role AS author_role,
                    u.full_name AS author_full_name
                FROM comments c
                JOIN users u ON u.id = c.user_id
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
                    body=record["body"],
                    question_id=record["question_id"],
                    answer_id=record["answer_id"],
                    id=record["id"],
                    created_at=record["created_at"],
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

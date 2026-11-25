import mysql.connector

from database.connection import get_connection
from models.answer import Answer
from models.user_summary import UserSummary


class AnswerRepository:
    def list_for_question(self, question_id):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                """
                SELECT
                    a.id AS answer_id,
                    a.question_id,
                    a.body,
                    a.created_at,
                    a.updated_at,
                    u.id AS author_id,
                    u.username AS author_username,
                    u.role AS author_role,
                    u.full_name AS author_full_name,
                    v.user_id AS voter_id,
                    v.vote_value
                FROM answers a
                JOIN users u ON u.id = a.user_id
                LEFT JOIN answer_votes v ON v.answer_id = a.id
                WHERE a.question_id = %s
                ORDER BY a.created_at, a.id
                """,
                (question_id,),
            )
            records = {}
            votes = {}
            for record in cursor.fetchall():
                answer_id = record["answer_id"]
                if answer_id not in records:
                    records[answer_id] = record
                    votes[answer_id] = {}
                if record["voter_id"] is not None:
                    votes[answer_id][record["voter_id"]] = record["vote_value"]

            return [
                Answer(
                    author=UserSummary(
                        username=record["author_username"],
                        id=record["author_id"],
                        role=record["author_role"],
                        full_name=record["author_full_name"],
                    ),
                    body=record["body"],
                    question_id=record["question_id"],
                    votes=votes[answer_id],
                    id=answer_id,
                    created_at=record["created_at"],
                    updated_at=record["updated_at"],
                )
                for answer_id, record in records.items()
            ]
        finally:
            cursor.close()
            connection.close()

    def create(self, answer):
        if answer.author.id is None:
            raise ValueError("The answer author must be saved first.")
        if answer.question_id is None:
            raise ValueError("An answer must belong to a saved question.")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO answers (question_id, user_id, body)
                VALUES (%s, %s, %s)
                """,
                (answer.question_id, answer.author.id, answer.body),
            )
            answer_id = cursor.lastrowid
            connection.commit()
        except mysql.connector.Error:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
        answer.id = answer_id
        return answer

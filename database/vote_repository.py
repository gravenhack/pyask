import mysql.connector

from database.connection import get_connection


class VoteRepository:
    def cast_vote(self, answer, user, value):
        if answer.id is None:
            raise ValueError("The answer must be saved before voting.")
        if user.id is None:
            raise ValueError("The voter must be saved before voting.")
        if value not in (-1, 1):
            raise ValueError("A vote must be +1 or -1.")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT 1 FROM hidden_content WHERE answer_id = %s",
                (answer.id,),
            )
            if cursor.fetchone() is not None:
                raise ValueError("A hidden answer cannot receive votes.")
            cursor.execute(
                """
                INSERT INTO answer_votes (user_id, answer_id, vote_value)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE vote_value = %s
                """,
                (user.id, answer.id, value, value),
            )
            connection.commit()
        except mysql.connector.Error:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

        answer.vote(user, value)
        return answer

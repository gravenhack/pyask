import mysql.connector

from database.connection import get_connection
from database.permissions import require_admin
from models.category import Category
from models.question import Question
from models.tag import Tag
from models.user_summary import UserSummary


class QuestionRepository:
    def list_categories(self):
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, name, description FROM categories ORDER BY name"
            )
            return [
                Category(
                    name=record["name"],
                    description=record["description"],
                    id=record["id"],
                )
                for record in cursor.fetchall()
            ]
        finally:
            cursor.close()
            connection.close()

    def create_category(self, category, admin):
        connection = get_connection()
        cursor = connection.cursor()
        try:
            require_admin(cursor, admin)
            cursor.execute(
                "INSERT INTO categories (name, description) VALUES (%s, %s)",
                (category.name, category.description),
            )
            category.id = cursor.lastrowid
            connection.commit()
        except mysql.connector.Error:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()
        return category

    def list_questions(
        self, search_text=None, tag_name=None, category_id=None, sort="recent"
    ):
        sort_options = {
            "recent": "qs.created_at DESC, qs.question_id DESC",
            "most_answered": (
                "qs.answer_count DESC, qs.created_at DESC, qs.question_id DESC"
            ),
            "most_voted": (
                "qs.vote_score DESC, qs.created_at DESC, qs.question_id DESC"
            ),
        }
        if sort not in sort_options:
            raise ValueError(f"Unknown question sort order: {sort}")

        conditions = []
        parameters = []
        if search_text and search_text.strip():
            conditions.append("(qs.title LIKE %s OR qs.body LIKE %s)")
            search_pattern = f"%{search_text.strip()}%"
            parameters.extend((search_pattern, search_pattern))
        if tag_name and tag_name.strip():
            conditions.append(
                """
                EXISTS (
                    SELECT 1
                    FROM question_tags filter_qt
                    JOIN tags filter_tag ON filter_tag.id = filter_qt.tag_id
                    WHERE filter_qt.question_id = qs.question_id
                      AND filter_tag.name = %s
                )
                """
            )
            parameters.append(tag_name.strip().lower())
        if category_id is not None:
            conditions.append("qs.category_id = %s")
            parameters.append(category_id)

        where_clause = (
            "WHERE " + " AND ".join(conditions) if conditions else ""
        )
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f"""
                SELECT
                    qs.question_id,
                    qs.title,
                    qs.body,
                    qs.created_at,
                    qs.updated_at,
                    qs.answer_count,
                    qs.vote_score,
                    qs.author_id,
                    qs.author_username,
                    qs.author_role,
                    qs.author_full_name,
                    qs.category_id,
                    qs.category_name,
                    qs.category_description,
                    t.id AS tag_id,
                    t.name AS tag_name
                FROM question_statistics qs
                LEFT JOIN question_tags qt ON qt.question_id = qs.question_id
                LEFT JOIN tags t ON t.id = qt.tag_id
                {where_clause}
                ORDER BY {sort_options[sort]}
                """,
                tuple(parameters),
            )
            questions = {}
            for record in cursor.fetchall():
                question_id = record["question_id"]
                if question_id not in questions:
                    questions[question_id] = Question(
                        author=UserSummary(
                            username=record["author_username"],
                            id=record["author_id"],
                            role=record["author_role"],
                            full_name=record["author_full_name"],
                        ),
                        title=record["title"],
                        body=record["body"],
                        category=Category(
                            name=record["category_name"],
                            description=record["category_description"],
                            id=record["category_id"],
                        ),
                        id=question_id,
                        created_at=record["created_at"],
                        updated_at=record["updated_at"],
                        answer_count=record["answer_count"],
                        vote_score=record["vote_score"],
                    )
                if record["tag_id"] is not None:
                    questions[question_id].add_tag(
                        Tag(record["tag_name"], id=record["tag_id"])
                    )
            return list(questions.values())
        finally:
            cursor.close()
            connection.close()

    def create(self, question):
        question.validate()
        if question.author.id is None:
            raise ValueError("The question author must be saved first.")
        if question.category.id is None:
            raise ValueError("The question category must exist in the database.")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO questions (user_id, category_id, title, body)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    question.author.id,
                    question.category.id,
                    question.title,
                    question.body,
                ),
            )
            question_id = cursor.lastrowid
            tag_ids = []
            for tag in question.tags:
                cursor.execute(
                    """
                    INSERT INTO tags (name)
                    VALUES (%s)
                    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)
                    """,
                    (tag.name,),
                )
                tag_ids.append(cursor.lastrowid)
                cursor.execute(
                    """
                    INSERT INTO question_tags (question_id, tag_id)
                    VALUES (%s, %s)
                    """,
                    (question_id, tag_ids[-1]),
                )
            connection.commit()
        except mysql.connector.Error:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

        question.id = question_id
        for tag, tag_id in zip(question.tags, tag_ids):
            tag.id = tag_id
        return question

import mysql.connector

from database.connection import get_connection
from database.permissions import (
    HIDDEN_CONTENT_MESSAGE,
    can_view_hidden_content,
    require_admin,
)
from models.category import Category
from models.question import Question
from models.tag import Tag
from models.user_summary import UserSummary


QUESTION_SORT_OPTIONS = {
    "recent": "qs.created_at DESC, qs.question_id DESC",
    "most_answered": (
        "qs.answer_count DESC, qs.created_at DESC, qs.question_id DESC"
    ),
    "most_voted": (
        "qs.vote_score DESC, qs.created_at DESC, qs.question_id DESC"
    ),
}


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

    @staticmethod
    def _question_filters(search_text=None, tag_name=None, category_id=None):
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
        return where_clause, tuple(parameters)

    @staticmethod
    def _validate_limit(limit):
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("The question limit must be a positive integer.")

    def count_questions(self, search_text=None, tag_name=None, category_id=None):
        where_clause, parameters = self._question_filters(
            search_text,
            tag_name,
            category_id,
        )
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM question_statistics qs
                {where_clause}
                """,
                parameters,
            )
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            connection.close()

    def list_popular_questions(
        self, search_text=None, tag_name=None, category_id=None, limit=4,
        viewer=None,
    ):
        self._validate_limit(limit)
        where_clause, parameters = self._question_filters(
            search_text,
            tag_name,
            category_id,
        )
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            can_view_originals = can_view_hidden_content(connection, viewer)
            cursor.execute(
                f"""
                SELECT
                    qs.question_id,
                    CASE
                        WHEN hc.id IS NOT NULL AND {int(not can_view_originals)} = 1
                            THEN '{HIDDEN_CONTENT_MESSAGE}'
                        ELSE qs.title
                    END AS title,
                    qs.answer_count,
                    qs.vote_score
                FROM question_statistics qs
                LEFT JOIN hidden_content hc ON hc.question_id = qs.question_id
                {where_clause}
                ORDER BY
                    qs.answer_count DESC,
                    qs.vote_score DESC,
                    qs.created_at DESC,
                    qs.question_id DESC
                LIMIT %s
                """,
                (*parameters, limit),
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            connection.close()

    def list_trending_tags(
        self, search_text=None, tag_name=None, category_id=None, limit=6
    ):
        self._validate_limit(limit)
        where_clause, parameters = self._question_filters(
            search_text,
            tag_name,
            category_id,
        )
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f"""
                SELECT
                    t.name AS tag_name,
                    COUNT(DISTINCT qs.question_id) AS question_count
                FROM question_statistics qs
                JOIN question_tags qt ON qt.question_id = qs.question_id
                JOIN tags t ON t.id = qt.tag_id
                {where_clause}
                GROUP BY t.id, t.name
                ORDER BY question_count DESC, t.name
                LIMIT %s
                """,
                (*parameters, limit),
            )
            return cursor.fetchall()
        finally:
            cursor.close()
            connection.close()

    def question_offset(
        self,
        question_id,
        search_text=None,
        tag_name=None,
        category_id=None,
        sort="recent",
    ):
        preceding_rows = {
            "recent": """
                qs.created_at > target.created_at
                OR (
                    qs.created_at = target.created_at
                    AND qs.question_id > target.question_id
                )
            """,
            "most_answered": """
                qs.answer_count > target.answer_count
                OR (
                    qs.answer_count = target.answer_count
                    AND (
                        qs.created_at > target.created_at
                        OR (
                            qs.created_at = target.created_at
                            AND qs.question_id > target.question_id
                        )
                    )
                )
            """,
            "most_voted": """
                qs.vote_score > target.vote_score
                OR (
                    qs.vote_score = target.vote_score
                    AND (
                        qs.created_at > target.created_at
                        OR (
                            qs.created_at = target.created_at
                            AND qs.question_id > target.question_id
                        )
                    )
                )
            """,
        }
        if sort not in preceding_rows:
            raise ValueError(f"Unknown question sort order: {sort}")

        where_clause, parameters = self._question_filters(
            search_text,
            tag_name,
            category_id,
        )
        if where_clause:
            where_clause = (
                f"{where_clause} AND ({preceding_rows[sort]})"
            )
        else:
            where_clause = f"WHERE ({preceding_rows[sort]})"

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM question_statistics qs
                JOIN question_statistics target
                    ON target.question_id = %s
                {where_clause}
                """,
                (question_id, *parameters),
            )
            return cursor.fetchone()[0]
        finally:
            cursor.close()
            connection.close()

    def list_questions(
        self,
        search_text=None,
        tag_name=None,
        category_id=None,
        sort="recent",
        page_size=20,
        offset=0,
        viewer=None,
    ):
        if sort not in QUESTION_SORT_OPTIONS:
            raise ValueError(f"Unknown question sort order: {sort}")
        self._validate_limit(page_size)
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("The question offset must be a non-negative integer.")
        where_clause, parameters = self._question_filters(
            search_text,
            tag_name,
            category_id,
        )
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            can_view_originals = can_view_hidden_content(connection, viewer)
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
                    hc.id AS hidden_id,
                    t.id AS tag_id,
                    t.name AS tag_name
                FROM (
                    SELECT qs.question_id
                    FROM question_statistics qs
                    {where_clause}
                    ORDER BY {QUESTION_SORT_OPTIONS[sort]}
                    LIMIT %s OFFSET %s
                ) page
                JOIN question_statistics qs
                    ON qs.question_id = page.question_id
                LEFT JOIN hidden_content hc ON hc.question_id = qs.question_id
                LEFT JOIN question_tags qt ON qt.question_id = qs.question_id
                LEFT JOIN tags t ON t.id = qt.tag_id
                ORDER BY {QUESTION_SORT_OPTIONS[sort]}
                """,
                (*parameters, page_size, offset),
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
                        title=(
                            record["title"]
                            if can_view_originals or record["hidden_id"] is None
                            else HIDDEN_CONTENT_MESSAGE
                        ),
                        body=(
                            record["body"]
                            if can_view_originals or record["hidden_id"] is None
                            else HIDDEN_CONTENT_MESSAGE
                        ),
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
                        is_hidden=record["hidden_id"] is not None,
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

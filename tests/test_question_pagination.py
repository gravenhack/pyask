import unittest
from unittest.mock import Mock, patch

from database.question_repository import QuestionRepository


class QuestionPaginationTests(unittest.TestCase):
    def setUp(self):
        self.repository = QuestionRepository()

    def test_list_questions_limits_page_before_joining_tags(self):
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchall.return_value = []

        with patch(
            "database.question_repository.get_connection",
            return_value=connection,
        ):
            questions = self.repository.list_questions(
                search_text="python",
                tag_name="SQL",
                category_id=8,
                sort="most_voted",
                page_size=20,
                offset=40,
            )

        self.assertEqual(questions, [])
        query, parameters = cursor.execute.call_args.args
        self.assertIn("SELECT qs.question_id", query)
        self.assertIn("LIMIT %s OFFSET %s", query)
        self.assertLess(
            query.index("LIMIT %s OFFSET %s"),
            query.index("LEFT JOIN question_tags"),
        )
        self.assertEqual(
            parameters,
            ("%python%", "%python%", "sql", 8, 20, 40),
        )
        cursor.close.assert_called_once()
        connection.close.assert_called_once()

    def test_count_questions_uses_the_same_search_and_category_filters(self):
        connection = Mock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = (45,)

        with patch(
            "database.question_repository.get_connection",
            return_value=connection,
        ):
            count = self.repository.count_questions(
                search_text="python",
                category_id=8,
            )

        self.assertEqual(count, 45)
        query, parameters = cursor.execute.call_args.args
        self.assertIn("COUNT(*)", query)
        self.assertIn("qs.title LIKE %s OR qs.body LIKE %s", query)
        self.assertIn("qs.category_id = %s", query)
        self.assertEqual(parameters, ("%python%", "%python%", 8))
        cursor.close.assert_called_once()
        connection.close.assert_called_once()

    def test_invalid_page_size_and_offset_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            self.repository.list_questions(page_size=0)

        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            self.repository.list_questions(offset=-1)

    def test_question_offset_respects_selected_sort_and_filters(self):
        for sort, expected_order in (
            ("recent", "qs.created_at > target.created_at"),
            ("most_answered", "qs.answer_count > target.answer_count"),
            ("most_voted", "qs.vote_score > target.vote_score"),
        ):
            with self.subTest(sort=sort):
                connection = Mock()
                cursor = connection.cursor.return_value
                cursor.fetchone.return_value = (20,)

                with patch(
                    "database.question_repository.get_connection",
                    return_value=connection,
                ):
                    offset = self.repository.question_offset(
                        17,
                        category_id=8,
                        sort=sort,
                    )

                self.assertEqual(offset, 20)
                query, parameters = cursor.execute.call_args.args
                self.assertIn(expected_order, query)
                self.assertIn("qs.category_id = %s", query)
                self.assertEqual(parameters, (17, 8))
                cursor.close.assert_called_once()
                connection.close.assert_called_once()

    def test_sidebar_aggregates_remain_based_on_all_matching_questions(self):
        connection = Mock()
        cursor = Mock()
        connection.cursor.return_value = cursor
        cursor.fetchall.side_effect = [
            [{"question_id": 3, "title": "Popular", "answer_count": 4,
              "vote_score": 8}],
            [{"tag_name": "python", "question_count": 6}],
        ]

        with patch(
            "database.question_repository.get_connection",
            return_value=connection,
        ):
            popular = self.repository.list_popular_questions(category_id=8)
            trending = self.repository.list_trending_tags(category_id=8)

        self.assertEqual(popular[0]["question_id"], 3)
        self.assertEqual(trending[0]["question_count"], 6)
        self.assertIn("ORDER BY", cursor.execute.call_args_list[0].args[0])
        self.assertIn("COUNT(DISTINCT qs.question_id)", cursor.execute.call_args_list[1].args[0])
        self.assertEqual(
            [call.args[1] for call in cursor.execute.call_args_list],
            [(8, 4), (8, 6)],
        )
        self.assertEqual(cursor.close.call_count, 2)
        self.assertEqual(connection.close.call_count, 2)


if __name__ == "__main__":
    unittest.main()

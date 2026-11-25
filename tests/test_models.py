import unittest

from models import Answer, Category, Comment, Post, Question, Report, Tag, User


def make_user(username="alice", role="user", user_id=1):
    return User(
        username=username,
        email=f"{username}@example.com",
        password_hash=User.hash_password("secret1"),
        role=role,
        id=user_id,
    )


class UserTests(unittest.TestCase):
    def test_rejects_invalid_username_and_email(self):
        password_hash = User.hash_password("secret1")

        with self.assertRaises(ValueError):
            User("  ", "alice@example.com", password_hash)
        with self.assertRaises(ValueError):
            User("alice", "invalid-email", password_hash)

    def test_rejects_unknown_role(self):
        with self.assertRaises(ValueError):
            make_user(role="owner")

    def test_only_admin_can_change_roles(self):
        user = make_user(user_id=2)
        moderator = make_user("moderator", "moderator", user_id=3)
        admin = make_user("admin", "admin", user_id=1)

        with self.assertRaises(PermissionError):
            user.change_role("moderator", moderator)

        user.change_role("moderator", admin)
        self.assertEqual(user.role, "moderator")

    def test_admin_cannot_change_their_own_role(self):
        admin = make_user("admin", "admin", user_id=1)

        with self.assertRaises(PermissionError):
            admin.change_role("user", admin)

        self.assertEqual(admin.role, "admin")

    def test_password_hash_can_be_verified_and_changed(self):
        user = make_user()

        self.assertTrue(user.check_password("secret1"))
        self.assertFalse(user.check_password("wrong"))

        user.change_password("secret1", "newpass")

        self.assertTrue(user.check_password("newpass"))
        self.assertFalse(user.check_password("secret1"))

    def test_rejects_short_new_password(self):
        user = make_user()

        with self.assertRaises(ValueError):
            user.change_password("secret1", "123")


class CategoryTests(unittest.TestCase):
    def test_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            Category("   ")


class PostTests(unittest.TestCase):
    def test_rejects_empty_body(self):
        with self.assertRaises(ValueError):
            Post(make_user(), "   ")


class QuestionTests(unittest.TestCase):
    def setUp(self):
        self.author = make_user()
        self.category = Category("Python")

    def test_requires_at_least_one_tag_before_saving(self):
        question = Question(self.author, "Title", "Body", self.category)

        with self.assertRaises(ValueError):
            question.validate()

    def test_rejects_more_than_three_tags(self):
        question = Question(
            self.author,
            "Title",
            "Body",
            self.category,
            tags=[Tag("one"), Tag("two"), Tag("three")],
        )

        with self.assertRaises(ValueError):
            question.add_tag(Tag("four"))

    def test_does_not_add_duplicate_tags(self):
        question = Question(
            self.author,
            "Title",
            "Body",
            self.category,
            tags=[Tag("python")],
        )

        question.add_tag(Tag("PYTHON"))

        self.assertEqual(len(question.tags), 1)

    def test_requires_a_category(self):
        with self.assertRaises(ValueError):
            Question(self.author, "Title", "Body", None)

    def test_stores_question_statistics(self):
        question = Question(
            self.author,
            "Title",
            "Body",
            self.category,
            answer_count=3,
            vote_score=5,
        )

        self.assertEqual(question.answer_count, 3)
        self.assertEqual(question.vote_score, 5)


class AnswerTests(unittest.TestCase):
    def test_one_user_vote_replaces_the_previous_vote(self):
        answer = Answer(make_user(), "Answer", question_id=1)
        voter = make_user("bob")

        answer.vote(voter, 1)
        answer.vote(voter, -1)

        self.assertEqual(answer.score, -1)
        self.assertEqual(answer.votes, {voter.id: -1})

    def test_rejects_vote_values_other_than_plus_or_minus_one(self):
        answer = Answer(make_user(), "Answer", question_id=1)

        with self.assertRaises(ValueError):
            answer.vote(make_user("bob"), 0)

    def test_requires_saved_user_to_vote(self):
        answer = Answer(make_user(), "Answer", question_id=1)
        unsaved_user = User("bob", "bob@example.com", User.hash_password("secret1"))

        with self.assertRaises(ValueError):
            answer.vote(unsaved_user, 1)


class CommentTests(unittest.TestCase):
    def test_requires_exactly_one_target(self):
        author = make_user()

        with self.assertRaises(ValueError):
            Comment(author, "Comment")
        with self.assertRaises(ValueError):
            Comment(author, "Comment", question_id=1, answer_id=2)

    def test_accepts_a_single_target(self):
        comment = Comment(make_user(), "Comment", answer_id=2)

        self.assertEqual(comment.answer_id, 2)
        self.assertIsNone(comment.question_id)


class ReportTests(unittest.TestCase):
    def test_requires_exactly_one_target(self):
        reporter = make_user()

        with self.assertRaises(ValueError):
            Report(reporter, "Reason")
        with self.assertRaises(ValueError):
            Report(reporter, "Reason", question_id=1, answer_id=2)

    def test_rejects_unknown_status(self):
        with self.assertRaises(ValueError):
            Report(make_user(), "Reason", question_id=1, status="invalid")

    def test_only_moderators_can_review_reports(self):
        report = Report(make_user(), "Reason", question_id=1)

        with self.assertRaises(PermissionError):
            report.mark_reviewed(make_user("regular"), "reviewed")

        moderator = make_user("moderator", "moderator")
        report.mark_reviewed(moderator, "dismissed")

        self.assertEqual(report.status, "dismissed")
        self.assertIs(report.reviewed_by, moderator)
        self.assertIsNotNone(report.reviewed_at)


if __name__ == "__main__":
    unittest.main()

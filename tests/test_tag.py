import unittest

from models.tag import Tag


class TagTests(unittest.TestCase):
    def test_strips_whitespace_and_lowercases_name(self):
        tag = Tag("  PYTHON  ")

        self.assertEqual(tag.name, "python")

    def test_accepts_name_at_maximum_length(self):
        tag = Tag("a" * 30)

        self.assertEqual(len(tag.name), 30)

    def test_rejects_empty_name(self):
        with self.assertRaises(ValueError):
            Tag("   ")

    def test_rejects_name_longer_than_30_characters(self):
        with self.assertRaises(ValueError):
            Tag("a" * 31)


if __name__ == "__main__":
    unittest.main()

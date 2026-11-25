from .post import Post


class Comment(Post):
    def __init__(self, author, body, question_id=None, answer_id=None,
                 id=None, created_at=None, is_hidden=False):
        super().__init__(author, body, id, created_at)
        # exactement UN des deux liens
        if (question_id is None) == (answer_id is None):
            raise ValueError(
                "Un commentaire vise une question OU une réponse (un seul).")
        self.question_id = question_id
        self.answer_id = answer_id
        self.is_hidden = is_hidden
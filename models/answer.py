from .post import Post


class Answer(Post):
    def __init__(self, author, body, question_id, votes=None,
                 id=None, created_at=None, updated_at=None):
        super().__init__(author, body, id, created_at)
        self.question_id = question_id
        self.updated_at = updated_at
        self.__votes = dict(votes or {})   # {id_utilisateur: +1 ou -1}

    def vote(self, user, value):
        """Un seul vote par utilisateur : un nouveau vote remplace l'ancien."""
        if value not in (-1, 1):
            raise ValueError("Un vote vaut +1 ou -1.")
        if user.id is None:
            raise ValueError("L'utilisateur doit être enregistré pour voter.")
        self.__votes[user.id] = value

    @property
    def score(self):
        return sum(self.__votes.values())

    @property
    def votes(self):
        return dict(self.__votes)

    def __str__(self):
        return f"{super().__str__()} (score {self.score})"
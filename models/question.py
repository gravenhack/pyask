from .post import Post

MAX_TAGS = 3


class Question(Post):
    def __init__(self, author, title, body, category, tags=None,
                 id=None, created_at=None, updated_at=None,
                 answer_count=0, vote_score=0, is_hidden=False):
        if category is None:
            raise ValueError("Une question doit avoir une catégorie.")
        super().__init__(author, body, id, created_at)
        if not title or not title.strip():
            raise ValueError("Le titre est obligatoire.")
        self.title = title.strip()
        self.category = category      # objet Category (une seule, obligatoire)
        self.updated_at = updated_at
        self.answer_count = answer_count
        self.vote_score = vote_score
        self.is_hidden = is_hidden
        self.__tags = []
        for tag in (tags or []):
            self.add_tag(tag)

    @property
    def tags(self):
        return list(self.__tags)      # copie : on ne modifie que via add_tag

    def add_tag(self, tag):
        if tag in self.__tags:
            return
        if len(self.__tags) >= MAX_TAGS:
            raise ValueError(f"Maximum {MAX_TAGS} tags par question.")
        self.__tags.append(tag)

    def remove_tag(self, tag):
        if tag in self.__tags:
            self.__tags.remove(tag)

    def validate(self):
        """À appeler avant l'enregistrement en base."""
        if not self.__tags:
            raise ValueError("Une question doit avoir au moins 1 tag.")

    def __str__(self):
        tags = ", ".join(str(t) for t in self.__tags)
        return (f"[Question #{self.id}] {self.title} "
                f"({self.category}) par {self.author.username} [{tags}]")
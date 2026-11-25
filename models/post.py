class Post:
    """Classe parente de Question, Answer et Comment (pas de table en base)."""

    def __init__(self, author, body, id=None, created_at=None):
        self.id = id
        self.author = author          # objet User (composition)
        self.created_at = created_at
        self.body = body              # passe par le setter ci-dessous

    @property
    def body(self):
        return self.__body

    @body.setter
    def body(self, value):
        if not value or not value.strip():
            raise ValueError("Le texte ne peut pas être vide.")
        self.__body = value.strip()

    def __str__(self):
        return (f"[{self.__class__.__name__} #{self.id}] "
                f"par {self.author.username} : {self.body[:50]}")
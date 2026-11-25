class Tag:
    """Étiquette : toujours en minuscules, 30 caractères maximum."""

    def __init__(self, name, id=None):
        name = (name or "").strip().lower()
        if not name or len(name) > 30:
            raise ValueError("Un tag fait entre 1 et 30 caractères.")
        self.id = id
        self.name = name

    def __eq__(self, other):
        return isinstance(other, Tag) and self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return self.name
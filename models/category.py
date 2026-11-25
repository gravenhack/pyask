class Category:
    def __init__(self, name, description=None, id=None):
        if not name or not name.strip():
            raise ValueError("Le nom de la catégorie est obligatoire.")
        self.id = id
        self.name = name.strip()
        self.description = description

    def __str__(self):
        return self.name
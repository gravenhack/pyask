HIDDEN_CONTENT_MESSAGE = "Contenu masqué par la modération."


def _require_role(cursor, user, roles, message):
    # Vérifie en mémoire que l'utilisateur existe, a le bon rôle
    # et possède un identifiant.
    if user is None or user.role not in roles:
        raise PermissionError(message)

    if user.id is None:
        raise ValueError("The user must be saved before performing this action.")
    # Vérifie dans la base que le rôle de l'utilisateur est toujours autorisé.
    cursor.execute("SELECT role FROM users WHERE id = %s", (user.id,))
    record = cursor.fetchone()
    if record is None or record[0] not in roles:
        raise PermissionError("The user's role is no longer active.")


def require_admin(cursor, admin):
    """Refuse l'action si l'utilisateur n'est pas un administrateur actif."""
    _require_role(cursor, admin, ("admin",), "Only an admin can perform this action.")


def require_moderator(cursor, moderator):
    """Refuse l'action si l'utilisateur n'est ni modérateur ni administrateur."""
    _require_role(
        cursor,
        moderator,
        ("moderator", "admin"),
        "Only a moderator or admin can perform this action.",
    )


def can_view_hidden_content(connection, user):
    """Indique si l'utilisateur peut voir le contenu masqué."""
    if user is None or not user.is_moderator():
        return False

    cursor = connection.cursor()
    try:
        require_moderator(cursor, user)
    finally:
        cursor.close()
    return True

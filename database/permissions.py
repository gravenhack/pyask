def _require_role(cursor, user, roles, message):
    if user is None or user.role not in roles:
        raise PermissionError(message)
    if user.id is None:
        raise ValueError("The user must be saved before performing this action.")

    cursor.execute("SELECT role FROM users WHERE id = %s", (user.id,))
    record = cursor.fetchone()
    if record is None or record[0] not in roles:
        raise PermissionError("The user's role is no longer active.")


def require_admin(cursor, admin):
    _require_role(cursor, admin, ("admin",), "Only an admin can perform this action.")


def require_moderator(cursor, moderator):
    _require_role(
        cursor,
        moderator,
        ("moderator", "admin"),
        "Only a moderator or admin can perform this action.",
    )

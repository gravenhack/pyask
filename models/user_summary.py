class UserSummary:
    """Public user details for authors displayed with forum content."""

    def __init__(self, username, id=None, role="user", full_name=None):
        self.id = id
        self.username = username
        self.role = role
        self.full_name = full_name

    def __str__(self):
        return f"{self.username} ({self.role})"

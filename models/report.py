from datetime import datetime

STATUSES = ("pending", "reviewed", "dismissed")


class Report:
    """Signalement d'un contenu inapproprié."""

    def __init__(self, reporter, reason, question_id=None, answer_id=None,
                 comment_id=None, status="pending", reviewed_by=None,
                 reviewed_at=None, id=None, created_at=None):
        if not reason or not reason.strip():
            raise ValueError("La raison du signalement est obligatoire.")
        targets = [question_id, answer_id, comment_id]
        if sum(t is not None for t in targets) != 1:
            raise ValueError("Un signalement vise exactement un contenu.")
        if status not in STATUSES:
            raise ValueError(f"Statut invalide : {status}")
        self.id = id
        self.reporter = reporter
        self.reason = reason.strip()
        self.question_id = question_id
        self.answer_id = answer_id
        self.comment_id = comment_id
        self.status = status
        self.reviewed_by = reviewed_by
        self.reviewed_at = reviewed_at
        self.created_at = created_at

    def mark_reviewed(self, moderator, status="reviewed"):
        if not moderator.is_moderator():
            raise PermissionError("Seul un modérateur ou un admin peut traiter.")
        if status not in ("reviewed", "dismissed"):
            raise ValueError("Le statut final est 'reviewed' ou 'dismissed'.")
        self.status = status
        self.reviewed_by = moderator
        self.reviewed_at = datetime.now()

    def __str__(self):
        return f"[Report #{self.id}] {self.reason} ({self.status})"
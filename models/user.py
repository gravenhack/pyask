import hashlib
import os

ROLES = ("user", "moderator", "admin")


class User:
    """Utilisateur du forum. Le mot de passe et le rôle sont privés."""

    def __init__(self, username, email, password_hash, role="user",
                 full_name=None, bio=None, id=None, created_at=None):
        if not username or not username.strip():
            raise ValueError("Le nom d'utilisateur est obligatoire.")
        if not email or "@" not in email:
            raise ValueError("Email invalide.")
        self.id = id
        self.username = username.strip()
        self.email = email.strip()
        self.full_name = full_name
        self.bio = bio
        self.created_at = created_at
        self.__password_hash = password_hash
        self.__role = self.__check_role(role)

    # --- rôle (privé, modifiable seulement via change_role) ---
    @staticmethod
    def __check_role(role):
        if role not in ROLES:
            raise ValueError(f"Rôle invalide : {role}. Choix : {ROLES}")
        return role

    @property
    def role(self):
        return self.__role

    def is_admin(self):
        return self.__role == "admin"

    def is_moderator(self):
        return self.__role in ("moderator", "admin")

    def change_role(self, new_role, by_user):
        """Seul un admin peut changer le rôle d'un utilisateur."""
        if not by_user.is_admin():
            raise PermissionError("Seul un admin peut changer un rôle.")
        new_role = self.__check_role(new_role)
        is_self = self is by_user or (
            self.id is not None and self.id == by_user.id
        )
        if is_self and new_role != self.__role:
            raise PermissionError("Un admin ne peut pas changer son propre rôle.")
        self.__role = new_role

    # --- mot de passe (privé) ---
    @staticmethod
    def hash_password(password):
        """Retourne 'sel$empreinte' à stocker dans la colonne password_hash."""
        if not password or len(password) < 6:
            raise ValueError("Mot de passe trop court (6 caractères minimum).")
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
        return salt.hex() + "$" + digest.hex()

    @property
    def password_hash(self):
        """Lecture seule : sert au repository pour enregistrer en base."""
        return self.__password_hash

    def check_password(self, password):
        return User.verify_password(password, self.__password_hash)

    @staticmethod
    def verify_password(password, password_hash):
        try:
            salt_hex, digest_hex = password_hash.split("$")
            digest = hashlib.pbkdf2_hmac(
                "sha256", password.encode(), bytes.fromhex(salt_hex), 100_000)
        except ValueError:
            return False
        return digest.hex() == digest_hex

    def _set_password_hash(self, password_hash):
        self.__password_hash = password_hash

    def change_password(self, old_password, new_password):
        if not self.check_password(old_password):
            raise PermissionError("Ancien mot de passe incorrect.")
        self.__password_hash = User.hash_password(new_password)

    def __str__(self):
        return f"{self.username} ({self.role})"
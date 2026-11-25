import mysql.connector

from database.connection import get_connection
from database.permissions import require_admin
from models.user import ROLES, User


class UserRepository:
    """Persists user registration and authentication data."""

    def list_users(self, admin):
        connection = get_connection()
        cursor = connection.cursor()
        try:
            require_admin(cursor, admin)
            cursor.execute(
                "SELECT id, username, role FROM users ORDER BY username"
            )
            return [
                {"id": row[0], "username": row[1], "role": row[2]}
                for row in cursor.fetchall()
            ]
        finally:
            cursor.close()
            connection.close()

    def change_role(self, user_id, role, admin):
        if user_id is None:
            raise ValueError("A saved user is required.")
        if role not in ROLES:
            raise ValueError(f"Invalid role: {role}")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            require_admin(cursor, admin)
            cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
            user_record = cursor.fetchone()
            if user_record is None:
                raise LookupError(f"User {user_id} was not found.")
            if user_id == admin.id and user_record[0] != role:
                raise PermissionError(
                    "An administrator cannot change their own role."
                )
            if user_record[0] == "admin" and role != "admin":
                cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
                if cursor.fetchone()[0] <= 1:
                    raise ValueError("At least one administrator must remain.")

            cursor.execute(
                "UPDATE users SET role = %s WHERE id = %s",
                (role, user_id),
            )
            connection.commit()
        except mysql.connector.Error:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def register(self, username, email, password, full_name=None, bio=None):
        user = User(
            username=username,
            email=email,
            password_hash=User.hash_password(password),
            full_name=full_name,
            bio=bio,
        )
        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, full_name, bio)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    user.username,
                    user.email,
                    user.password_hash,
                    user.full_name,
                    user.bio,
                ),
            )
            connection.commit()
            user.id = cursor.lastrowid
            return user
        except mysql.connector.Error:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def update_profile(
        self,
        user_id,
        full_name=None,
        bio=None,
        username=None,
        current_password=None,
        new_password=None,
    ):
        if user_id is None:
            raise ValueError("The user must be saved before updating a profile.")
        if (current_password is None) != (new_password is None):
            raise ValueError(
                "Both the current and new passwords are required."
            )
        if username is not None:
            username = username.strip()
            if not username:
                raise ValueError("The username is required.")
            if len(username) > 50:
                raise ValueError("The username cannot exceed 50 characters.")

        connection = get_connection()
        cursor = connection.cursor()
        try:
            cursor.execute(
                "SELECT username, password_hash FROM users WHERE id = %s",
                (user_id,),
            )
            account = cursor.fetchone()
            if account is None:
                raise LookupError(f"User {user_id} was not found.")

            current_username, stored_password_hash = account
            username = username if username is not None else current_username
            cursor.execute(
                "SELECT 1 FROM users WHERE username = %s AND id <> %s",
                (username, user_id),
            )
            if cursor.fetchone() is not None:
                raise ValueError("This username is already in use.")

            assignments = ["username = %s", "full_name = %s", "bio = %s"]
            values = [username, full_name, bio]
            new_password_hash = None
            if new_password is not None:
                if not User.verify_password(
                    current_password,
                    stored_password_hash,
                ):
                    raise PermissionError("The current password is incorrect.")
                new_password_hash = User.hash_password(new_password)
                assignments.append("password_hash = %s")
                values.append(new_password_hash)

            cursor.execute(
                f"UPDATE users SET {', '.join(assignments)} WHERE id = %s",
                (*values, user_id),
            )
            connection.commit()
            return new_password_hash
        except mysql.connector.Error:
            connection.rollback()
            raise
        finally:
            cursor.close()
            connection.close()

    def authenticate(self, username, password):
        username = username.strip()
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.callproc("get_user_for_authentication", (username,))
            result_cursor = next(cursor.stored_results())
            try:
                record = result_cursor.fetchone()
            finally:
                result_cursor.close()
        finally:
            cursor.close()
            connection.close()

        if record is None:
            return None

        user = User(
            username=record["username"],
            email=record["email"],
            password_hash=record["password_hash"],
            role=record["role"],
            full_name=record["full_name"],
            bio=record["bio"],
            id=record["id"],
            created_at=record["created_at"],
        )
        if not user.check_password(password):
            return None
        return user

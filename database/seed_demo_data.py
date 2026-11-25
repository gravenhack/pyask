import os
import secrets

from models.user import User


VALIDATION_DATABASE = "pyask_validation_20261124"

DEMO_USERS = {
    "amina": {
        "username": "pyask_demo_amina",
        "email": "pyask_demo_amina@example.invalid",
        "full_name": "Amina Demo",
    },
    "youssef": {
        "username": "pyask_demo_youssef",
        "email": "pyask_demo_youssef@example.invalid",
        "full_name": "Youssef Demo",
    },
    "salma": {
        "username": "pyask_demo_salma",
        "email": "pyask_demo_salma@example.invalid",
        "full_name": "Salma Demo",
    },
}

DEMO_CATEGORIES = {
    "Python": "Questions liées au langage Python et ses bibliothèques",
    "Bases de données": "MySQL, SQL et conception de schémas",
    "Interfaces Graphiques": "PyQt et conception d'interfaces",
}

DEMO_QUESTIONS = (
    {
        "author": "amina",
        "category": "Python",
        "title": "Comment organiser un projet Python en couches ?",
        "body": (
            "Je construis une application avec des modèles, des dépôts MySQL "
            "et une interface PyQt. Comment séparer ces responsabilités "
            "pour garder le code facile à tester ?"
        ),
        "tags": ("python", "architecture"),
        "comments": (
            ("youssef", "Séparer les accès SQL de l'interface aide beaucoup."),
        ),
        "answers": (
            {
                "author": "youssef",
                "body": (
                    "Place les règles métier dans les modèles, les requêtes "
                    "dans les dépôts, et laisse l'interface appeler ces dépôts."
                ),
                "votes": {"amina": 1, "salma": 1},
                "comments": (
                    ("amina", "Donc l'interface ne lance pas de SQL directement ?"),
                ),
            },
            {
                "author": "salma",
                "body": (
                    "Une structure simple avec models/, database/ et une "
                    "interface principale suffit souvent pour commencer."
                ),
                "votes": {"youssef": 1},
                "comments": (),
            },
        ),
    },
    {
        "author": "youssef",
        "category": "Bases de données",
        "title": "Quand utiliser une vue plutôt qu'une requête SQL ?",
        "body": (
            "Plusieurs écrans ont besoin des mêmes statistiques de questions "
            "et de réponses. Est-ce qu'une vue MySQL est adaptée à ce cas ?"
        ),
        "tags": ("mysql", "sql"),
        "comments": (
            ("salma", "Une vue évite aussi de dupliquer la requête dans les dépôts."),
        ),
        "answers": (
            {
                "author": "amina",
                "body": (
                    "Une vue est utile quand la même projection est réutilisée. "
                    "Elle centralise la requête sans stocker les résultats."
                ),
                "votes": {"youssef": 1, "salma": 1},
                "comments": (
                    ("youssef", "C'est clair, les statistiques restent calculées."),
                ),
            },
            {
                "author": "salma",
                "body": (
                    "Garde une requête dans le dépôt si elle n'est utilisée "
                    "qu'une fois ou si elle dépend fortement de paramètres."
                ),
                "votes": {"amina": 1},
                "comments": (),
            },
        ),
    },
    {
        "author": "salma",
        "category": "Interfaces Graphiques",
        "title": "Comment garder une interface PyQt réactive ?",
        "body": (
            "Une opération de chargement prend parfois plusieurs secondes. "
            "Comment éviter que la fenêtre semble bloquée pendant ce temps ?"
        ),
        "tags": ("pyqt", "interface"),
        "comments": (
            ("amina", "L'utilisateur devrait aussi voir un état de chargement."),
        ),
        "answers": (
            {
                "author": "youssef",
                "body": (
                    "Pour une opération longue, déplace le travail hors du "
                    "thread graphique avec QThread ou un worker adapté."
                ),
                "votes": {"amina": 1, "salma": 1},
                "comments": (
                    ("salma", "Merci, je vais regarder les signaux du worker."),
                ),
            },
            {
                "author": "amina",
                "body": (
                    "Si l'opération est courte, affiche au minimum un état "
                    "clair et évite les appels bloquants dans les callbacks."
                ),
                "votes": {"youssef": 1},
                "comments": (),
            },
        ),
    },
    {
        "author": "amina",
        "category": "Bases de données",
        "title": "Comment tester un dépôt qui utilise MySQL ?",
        "body": (
            "Je veux vérifier les requêtes d'un repository sans risquer "
            "d'altérer les données de développement. Quelle approche choisir ?"
        ),
        "tags": ("tests", "mysql"),
        "comments": (
            ("youssef", "Une base dédiée aux tests évite les surprises."),
        ),
        "answers": (
            {
                "author": "salma",
                "body": (
                    "Utilise une base de test isolée, insère des données "
                    "connues, puis nettoie-les dans une transaction annulée."
                ),
                "votes": {"amina": 1, "youssef": 1},
                "comments": (
                    ("amina", "Je vais aussi tester les cas d'erreur."),
                ),
            },
            {
                "author": "youssef",
                "body": (
                    "Pour les tests unitaires, remplace la connexion par "
                    "un faux dépôt; garde quelques tests d'intégration MySQL."
                ),
                "votes": {"salma": 1},
                "comments": (),
            },
        ),
    },
)


def _ensure_user(cursor, user_data):
    cursor.execute(
        "SELECT id, username, email FROM users WHERE username = %s OR email = %s",
        (user_data["username"], user_data["email"]),
    )
    matches = cursor.fetchall()
    if matches:
        if (
            len(matches) != 1
            or matches[0]["username"] != user_data["username"]
            or matches[0]["email"] != user_data["email"]
        ):
            raise RuntimeError(
                "A demo username or email is already used by another account."
            )
        return matches[0]["id"], False

    cursor.execute(
        """
        INSERT INTO users (username, email, password_hash, full_name)
        VALUES (%s, %s, %s, %s)
        """,
        (
            user_data["username"],
            user_data["email"],
            User.hash_password(secrets.token_urlsafe(32)),
            user_data["full_name"],
        ),
    )
    return cursor.lastrowid, True


def _ensure_category(cursor, name, description):
    cursor.execute("SELECT id FROM categories WHERE name = %s", (name,))
    row = cursor.fetchone()
    if row:
        return row["id"], False

    cursor.execute(
        "INSERT INTO categories (name, description) VALUES (%s, %s)",
        (name, description),
    )
    return cursor.lastrowid, True


def _ensure_tag(cursor, name):
    cursor.execute("SELECT id FROM tags WHERE name = %s", (name,))
    row = cursor.fetchone()
    if row:
        return row["id"]

    cursor.execute("INSERT INTO tags (name) VALUES (%s)", (name,))
    return cursor.lastrowid


def _ensure_question(cursor, author_id, category_id, question_data):
    cursor.execute(
        "SELECT id FROM questions WHERE user_id = %s AND title = %s",
        (author_id, question_data["title"]),
    )
    row = cursor.fetchone()
    if row:
        question_id = row["id"]
        created = False
    else:
        cursor.execute(
            """
            INSERT INTO questions (user_id, category_id, title, body)
            VALUES (%s, %s, %s, %s)
            """,
            (
                author_id,
                category_id,
                question_data["title"],
                question_data["body"],
            ),
        )
        question_id = cursor.lastrowid
        created = True

    for tag_name in question_data["tags"]:
        tag_id = _ensure_tag(cursor, tag_name)
        cursor.execute(
            "SELECT 1 FROM question_tags WHERE question_id = %s AND tag_id = %s",
            (question_id, tag_id),
        )
        if not cursor.fetchone():
            cursor.execute(
                """
                INSERT INTO question_tags (question_id, tag_id)
                VALUES (%s, %s)
                """,
                (question_id, tag_id),
            )
    return question_id, created


def _ensure_answer(cursor, question_id, author_id, body):
    cursor.execute(
        """
        SELECT id FROM answers
        WHERE question_id = %s AND user_id = %s AND body = %s
        ORDER BY id
        LIMIT 1
        """,
        (question_id, author_id, body),
    )
    row = cursor.fetchone()
    if row:
        return row["id"], False

    cursor.execute(
        """
        INSERT INTO answers (question_id, user_id, body)
        VALUES (%s, %s, %s)
        """,
        (question_id, author_id, body),
    )
    return cursor.lastrowid, True


def _ensure_comment(cursor, author_id, body, question_id=None, answer_id=None):
    if (question_id is None) == (answer_id is None):
        raise ValueError("A demo comment must target one question or answer.")

    if question_id is not None:
        cursor.execute(
            """
            SELECT id FROM comments
            WHERE user_id = %s AND question_id = %s
              AND answer_id IS NULL AND body = %s
            LIMIT 1
            """,
            (author_id, question_id, body),
        )
    else:
        cursor.execute(
            """
            SELECT id FROM comments
            WHERE user_id = %s AND question_id IS NULL
              AND answer_id = %s AND body = %s
            LIMIT 1
            """,
            (author_id, answer_id, body),
        )
    if cursor.fetchone():
        return False

    cursor.execute(
        """
        INSERT INTO comments (user_id, question_id, answer_id, body)
        VALUES (%s, %s, %s, %s)
        """,
        (author_id, question_id, answer_id, body),
    )
    return True


def _ensure_vote(cursor, user_id, answer_id, vote_value):
    cursor.execute(
        "SELECT 1 FROM answer_votes WHERE user_id = %s AND answer_id = %s",
        (user_id, answer_id),
    )
    if cursor.fetchone():
        return False

    cursor.execute(
        """
        INSERT INTO answer_votes (user_id, answer_id, vote_value)
        VALUES (%s, %s, %s)
        """,
        (user_id, answer_id, vote_value),
    )
    return True


def seed_demo_data():
    if os.environ.get("PYASK_DB_NAME") != VALIDATION_DATABASE:
        raise RuntimeError(
            "Refusing to seed: set PYASK_DB_NAME=pyask_validation_20261124."
        )

    from database.connection import get_connection

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT DATABASE() AS database_name")
        if cursor.fetchone()["database_name"] != VALIDATION_DATABASE:
            raise RuntimeError("Connected to an unexpected database; no seed applied.")

        counts = {
            "users": 0,
            "categories": 0,
            "questions": 0,
            "answers": 0,
            "comments": 0,
            "votes": 0,
        }
        user_ids = {}
        category_ids = {}
        for key, user_data in DEMO_USERS.items():
            user_ids[key], created = _ensure_user(cursor, user_data)
            counts["users"] += int(created)
        for name, description in DEMO_CATEGORIES.items():
            category_ids[name], created = _ensure_category(
                cursor, name, description
            )
            counts["categories"] += int(created)

        for question_data in DEMO_QUESTIONS:
            question_id, created = _ensure_question(
                cursor,
                user_ids[question_data["author"]],
                category_ids[question_data["category"]],
                question_data,
            )
            counts["questions"] += int(created)
            for question_comment_author, body in question_data["comments"]:
                counts["comments"] += int(
                    _ensure_comment(
                        cursor,
                        user_ids[question_comment_author],
                        body,
                        question_id=question_id,
                    )
                )

            for answer_data in question_data["answers"]:
                answer_id, created = _ensure_answer(
                    cursor,
                    question_id,
                    user_ids[answer_data["author"]],
                    answer_data["body"],
                )
                counts["answers"] += int(created)
                for voter, vote_value in answer_data["votes"].items():
                    counts["votes"] += int(
                        _ensure_vote(
                            cursor,
                            user_ids[voter],
                            answer_id,
                            vote_value,
                        )
                    )
                for comment_author, body in answer_data["comments"]:
                    counts["comments"] += int(
                        _ensure_comment(
                            cursor,
                            user_ids[comment_author],
                            body,
                            answer_id=answer_id,
                        )
                    )

        connection.commit()
        return counts
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    print(f"Seeded {VALIDATION_DATABASE}: {seed_demo_data()}")

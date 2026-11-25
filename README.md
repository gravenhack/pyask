# PYASK

A desktop Question & Answer forum built with Python (OOP), PyQt5, and MySQL.

## Features

- Register and log in; passwords are stored as salted hashes.
- Log out and return to the sign-in screen with credentials cleared.
- Update a profile's full name and bio from the forum.
- Post questions with a category and up to three tags, and search, filter, and sort questions.
- Answer questions, vote on answers, and comment on questions or answers.
- Report questions, answers, and comments.
- Let moderators review or dismiss pending reports.
- Let admins assign user roles and create categories.
- Let admins export question and answer reports as separate CSV files from the
  Reports section.

Admins can manage user roles and add categories from the administration
screen. Categories cannot be deleted while questions use them. An admin
cannot change their own role from the administration screen.

## Interface

The desktop UI remains native PyQt5 and follows the shadcn kit's Social Media
page layout: a profile/search/navigation sidebar, a category-story strip above
the central question feed, and a right column for popular questions and tags.
Opening a feed card shows its answers and discussion actions in a dedicated
dialog. The supplied abstract wallpaper is used only on the login screen; the
forum keeps its dark background. The layout and neutral card styling are
implemented with Qt; no React components or kit files are copied into PYASK.

New accounts have the `user` role. To bootstrap the first administrator, first
register the account, then connect to the database selected in `.env` and
promote that trusted account once:

```sql
UPDATE users SET role = 'admin' WHERE username = 'your_admin_username';
```

The application prevents demoting the last administrator.

## Project structure

- `main.py`: desktop-app entry point.
- `config.py`: loads `.env` and validates MySQL settings.
- `models/`: domain objects and their business rules.
- `database/`: MySQL connection, repositories, `schema.sql`, and the demo seed.
- `ui/main_window.py`: current PyQt5 screens and interactions.
- `ui/styles.qss`: Qt stylesheet; `ui/background.png` is the optimized login wallpaper.
- `ui/fonts/`: bundled Agrave Pro font files and their SIL Open Font License.
- `reporting/`: CSV export.
- `exports/`: default destination for CSV reports; generated files are ignored by Git.
- `tests/`: unit and UI tests.
- `DIAGRAMMES.md`: class and use-case diagrams.
- `PYASK_DECISIONS.md`: project decisions and progress notes.

This is a progressive reorganization: the UI remains in one module for now,
and existing repositories continue to handle database access. This avoids
duplicating business logic in an empty `services/` layer.

## Database connection

Create a virtual environment and install the dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in the MySQL credentials once. The
application loads `.env` automatically; `.env` is ignored by Git.

- `PYASK_DB_USER` and `PYASK_DB_PASSWORD` are required.
- `PYASK_DB_HOST` defaults to `127.0.0.1`.
- `PYASK_DB_PORT` defaults to `3306`.
- `PYASK_DB_NAME` defaults to `pyask_db`.

The database name in `.env` selects the database used by the running
application; it does not change the target in `database/schema.sql`.
**Review `database/schema.sql` before importing it:** it starts by dropping
and recreating `pyask_db`. Do not run it against a database containing data
you need to keep.

Keep real credentials only in the ignored `.env`.

## Seed validation data

The demo-data script only targets the existing `pyask_validation_20261124`
database. It checks the configured and connected database before writing,
adds missing records without deleting or changing existing accounts or
content, and can be run repeatedly. It does not create or reset a database.

```bash
PYASK_DB_NAME=pyask_validation_20261124 .venv/bin/python -m database.seed_demo_data
```

Demo accounts receive randomly generated password hashes whose passwords are
not retained, so they are intended as sample-content authors rather than
accounts for signing in. To view the seeded content in the app, run it with
`PYASK_DB_NAME=pyask_validation_20261124` as well.

## Run the desktop app

```bash
.venv/bin/python main.py
```

Run the unit tests with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

See [DIAGRAMMES.md](./DIAGRAMMES.md) for the class and use-case diagrams.

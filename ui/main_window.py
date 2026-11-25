import csv
import sys
from pathlib import Path

import mysql.connector
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database.answer_repository import AnswerRepository
from database.analytics_repository import (
    ANSWER_REPORT_FIELDS,
    QUESTION_REPORT_FIELDS,
    AnalyticsRepository,
)
from database.comment_repository import CommentRepository
from database.question_repository import QuestionRepository
from database.report_repository import ReportRepository
from database.user_repository import UserRepository
from database.vote_repository import VoteRepository
from models.answer import Answer
from models.category import Category
from models.comment import Comment
from models.question import Question
from models.report import Report
from models.tag import Tag
from models.user import ROLES
from models.user_summary import UserSummary
from reporting.csv_exporter import export_csv

APP_BACKGROUND_PATH = Path(__file__).with_name("background.png")
APP_STYLESHEET = (
    Path(__file__).with_name("styles.qss")
    .read_text(encoding="utf-8")
    .replace("APP_BACKGROUND_URL", APP_BACKGROUND_PATH.as_posix())
)
APP_FONT_FILES = (
    "AgravePro-Regular.ttf",
    "AgravePro-SemiBold.ttf",
    "AgravePro-Bold.ttf",
)


def _load_application_fonts():
    font_directory = Path(__file__).with_name("fonts")
    for font_file in APP_FONT_FILES:
        font_path = font_directory / font_file
        font_id = QFontDatabase.addApplicationFont(str(font_path))
        if font_id < 0:
            raise RuntimeError(f"Unable to load application font: {font_path}")
        if "Agrave Pro" not in QFontDatabase.applicationFontFamilies(font_id):
            raise RuntimeError(f"Unexpected font family in {font_path}")


class LoginWindow(QWidget):
    authenticated = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("loginWindow")
        self.setWindowTitle("PYASK - Connexion")
        self.setMinimumSize(520, 600)
        self.resize(520, 640)
        self.is_registering = False

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nom d'utilisateur")
        self.username_input.setObjectName("loginInput")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Adresse e-mail")
        self.email_input.setObjectName("loginInput")
        self.email_label = QLabel("Adresse e-mail")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Mot de passe")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setObjectName("loginInput")

        self.login_title = QLabel("Bienvenue sur PYASK")
        self.login_title.setObjectName("loginTitle")
        self.login_hint = QLabel("Connecte-toi pour rejoindre les discussions.")
        self.login_hint.setObjectName("loginHint")
        self.submit_button = QPushButton("Se connecter")
        self.submit_button.setObjectName("loginPrimaryButton")
        self.submit_button.clicked.connect(self._submit)
        self.mode_button = QPushButton("Créer un compte")
        self.mode_button.setObjectName("linkButton")
        self.mode_button.setCursor(Qt.PointingHandCursor)
        self.mode_button.clicked.connect(self._toggle_mode)

        card = QFrame()
        card.setObjectName("loginCard")
        card.setFixedWidth(440)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 28, 28, 24)
        card_layout.setSpacing(12)
        card_layout.addWidget(self.login_title)
        card_layout.addWidget(self.login_hint)
        card_layout.addSpacing(8)
        card_layout.addWidget(QLabel("Nom d'utilisateur"))
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.email_label)
        card_layout.addWidget(self.email_input)
        card_layout.addWidget(QLabel("Mot de passe"))
        card_layout.addWidget(self.password_input)
        card_layout.addSpacing(8)
        card_layout.addWidget(self.submit_button)
        card_layout.addWidget(self.mode_button)

        content = QWidget()
        content.setFixedWidth(440)
        content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)
        brand_title = QLabel("PYASK")
        brand_title.setObjectName("brandTitle")
        brand_title.setAlignment(Qt.AlignCenter)
        brand_subtitle = QLabel("Pose une question. Partage tes réponses.")
        brand_subtitle.setObjectName("brandSubtitle")
        brand_subtitle.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(brand_title)
        content_layout.addWidget(brand_subtitle)
        content_layout.addWidget(card)

        layout = QGridLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.addWidget(content, 0, 0, Qt.AlignCenter)
        self.email_label.hide()
        self.email_input.hide()
        self.username_input.returnPressed.connect(self._submit)
        self.email_input.returnPressed.connect(self._submit)
        self.password_input.returnPressed.connect(self._submit)
        self.username_input.setFocus()

    def _submit(self):
        if self.is_registering:
            self._register()
        else:
            self._login()

    def _toggle_mode(self):
        self.is_registering = not self.is_registering
        self.email_label.setVisible(self.is_registering)
        self.email_input.setVisible(self.is_registering)
        if self.is_registering:
            self.setWindowTitle("PYASK - Inscription")
            self.login_title.setText("Créer un compte")
            self.login_hint.setText("Rejoins la communauté PYASK.")
            self.submit_button.setText("Créer mon compte")
            self.mode_button.setText("Déjà membre ? Se connecter")
        else:
            self.setWindowTitle("PYASK - Connexion")
            self.login_title.setText("Bienvenue sur PYASK")
            self.login_hint.setText("Connecte-toi pour rejoindre les discussions.")
            self.submit_button.setText("Se connecter")
            self.mode_button.setText("Créer un compte")

    def reset_for_login(self):
        if self.is_registering:
            self._toggle_mode()
        self.username_input.clear()
        self.email_input.clear()
        self.password_input.clear()
        self.username_input.setFocus()

    def _login(self):
        try:
            user = UserRepository().authenticate(
                self.username_input.text(),
                self.password_input.text(),
            )
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Erreur de connexion", str(error))
            return

        if user is None:
            QMessageBox.warning(
                self,
                "Connexion refusée",
                "Nom d'utilisateur ou mot de passe incorrect.",
            )
            return
        self.authenticated.emit(user)

    def _register(self):
        try:
            user = UserRepository().register(
                self.username_input.text(),
                self.email_input.text(),
                self.password_input.text(),
            )
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "Inscription impossible", str(error))
            return
        self.authenticated.emit(user)


class QuestionDialog(QDialog):
    def __init__(self, categories, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Poser une question")
        self.setMinimumWidth(480)

        self.title_input = QLineEdit()
        self.body_input = QPlainTextEdit()
        self.category_input = QComboBox()
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("python, mysql")

        for category in categories:
            self.category_input.addItem(category.name, category)

        form = QFormLayout()
        form.addRow("Titre", self.title_input)
        form.addRow("Détails", self.body_input)
        form.addRow("Catégorie", self.category_input)
        form.addRow("Tags (séparés par des virgules)", self.tags_input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)


class ProfileDialog(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mon profil")
        self.setMinimumWidth(440)

        self.full_name_input = QLineEdit(user.full_name or "")
        self.full_name_input.setMaxLength(100)
        self.full_name_input.setPlaceholderText("Ton nom complet")
        self.bio_input = QPlainTextEdit(user.bio or "")
        self.bio_input.setPlaceholderText("Quelques mots sur toi")
        self.bio_input.setMaximumHeight(120)

        form = QFormLayout()
        form.addRow("Nom complet", self.full_name_input)
        form.addRow("Bio (255 caractères maximum)", self.bio_input)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        self.buttons.button(QDialogButtonBox.Save).setText("Enregistrer")
        self.buttons.button(QDialogButtonBox.Cancel).setText("Annuler")
        self.buttons.accepted.connect(self._accept_if_valid)
        self.buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.buttons)

    def _accept_if_valid(self):
        if len(self.bio_input.toPlainText().strip()) > 255:
            QMessageBox.warning(
                self,
                "Profil invalide",
                "La bio ne peut pas dépasser 255 caractères.",
            )
            return
        self.accept()


class ModerationDialog(QDialog):
    def __init__(self, moderator, report_repository, parent=None):
        super().__init__(parent)
        if not moderator.is_moderator():
            raise PermissionError("Seul un modérateur ou un admin peut traiter.")

        self.setWindowTitle("Modération des signalements")
        self.resize(760, 520)
        self.moderator = moderator
        self.report_repository = report_repository
        self.report_list = QListWidget()
        self.report_list.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Fixed
        )
        self.report_list.currentItemChanged.connect(self._show_selected_report)
        self.report_details = QPlainTextEdit()
        self.report_details.setReadOnly(True)
        self.report_details.setMinimumHeight(140)
        self.report_details.setMaximumHeight(240)
        self.report_details.setPlainText("Sélectionne un signalement.")
        self.status_label = QLabel()

        self.review_button = QPushButton("Marquer comme traité")
        self.review_button.setEnabled(False)
        self.review_button.clicked.connect(
            lambda: self._review_selected("reviewed")
        )
        self.dismiss_button = QPushButton("Rejeter le signalement")
        self.dismiss_button.setEnabled(False)
        self.dismiss_button.clicked.connect(
            lambda: self._review_selected("dismissed")
        )
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)

        action_layout = QHBoxLayout()
        action_layout.addWidget(self.review_button)
        action_layout.addWidget(self.dismiss_button)
        action_layout.addWidget(close_button)

        reports_group = QGroupBox("Signalements en attente")
        reports_layout = QVBoxLayout(reports_group)
        reports_layout.addWidget(self.report_list)
        details_group = QGroupBox("Détails du contenu")
        details_layout = QVBoxLayout(details_group)
        details_layout.addWidget(self.report_details)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(reports_group, 1)
        layout.addWidget(details_group)
        layout.addWidget(self.status_label)
        layout.addLayout(action_layout)

        self._refresh_reports()

    def _refresh_reports(self):
        try:
            reports = self.report_repository.list_pending(self.moderator)
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.critical(
                self, "Signalements indisponibles", str(error)
            )
            return
        except PermissionError as error:
            QMessageBox.critical(self, "Accès refusé", str(error))
            self.reject()
            return

        self.report_list.clear()
        for report in reports:
            item = QListWidgetItem(
                f"#{report['id']} · {report['target_type']} · "
                f"{report['reporter_username']} : {report['reason']}"
            )
            item.setData(Qt.UserRole, report)
            self.report_list.addItem(item)

        has_reports = bool(reports)
        self.report_list.setFixedHeight(
            min(240, max(56, len(reports) * 38 + 18))
        )
        self.review_button.setEnabled(has_reports)
        self.dismiss_button.setEnabled(has_reports)
        if not has_reports:
            self.report_details.setPlainText("Aucun signalement en attente.")
        self._show_selected_report(self.report_list.currentItem(), None)

    def _show_selected_report(self, item, _previous):
        has_selection = item is not None
        self.review_button.setEnabled(has_selection)
        self.dismiss_button.setEnabled(has_selection)
        if not has_selection:
            if self.report_list.count():
                self.report_details.setPlainText("Sélectionne un signalement.")
            return

        report = item.data(Qt.UserRole)
        self.report_details.setPlainText(
            f"Signalement #{report['id']}\n"
            f"Envoyé par : {report['reporter_username']}\n"
            f"Motif : {report['reason']}\n\n"
            f"Contenu signalé ({report['target_type']}) :\n"
            f"{report['target_context'] or ''}\n"
            f"{report['target_content'] or ''}"
        )

    def _review_selected(self, status):
        item = self.report_list.currentItem()
        if item is None:
            return
        record = item.data(Qt.UserRole)
        report = Report(
            reporter=UserSummary(
                username=record["reporter_username"],
                id=record["reporter_id"],
            ),
            reason=record["reason"],
            question_id=record["question_id"],
            answer_id=record["answer_id"],
            comment_id=record["comment_id"],
            id=record["id"],
            created_at=record["created_at"],
        )
        try:
            self.report_repository.review(report, self.moderator, status)
        except (
            mysql.connector.Error,
            LookupError,
            PermissionError,
            RuntimeError,
            ValueError,
        ) as error:
            QMessageBox.warning(self, "Traitement impossible", str(error))
            return

        self.status_label.setText(
            "Signalement marqué comme traité."
            if status == "reviewed"
            else "Signalement rejeté."
        )
        self._refresh_reports()


class AdministrationDialog(QDialog):
    def __init__(
        self, admin, user_repository, question_repository, parent=None
    ):
        super().__init__(parent)
        if not admin.is_admin():
            raise PermissionError("Seul un admin peut accéder à l'administration.")

        self.admin = admin
        self.user_repository = user_repository
        self.question_repository = question_repository
        self.user_roles = {}

        self.setWindowTitle("Administration PYASK")
        self.resize(560, 500)

        self.user_input = QComboBox()
        self.user_input.currentIndexChanged.connect(self._sync_user_role)
        self.role_input = QComboBox()
        self.role_input.addItems(ROLES)
        self.role_button = QPushButton("Enregistrer le rôle")
        self.role_button.clicked.connect(self._change_role)
        self.role_status = QLabel()

        user_form = QFormLayout()
        user_form.addRow("Utilisateur", self.user_input)
        user_form.addRow("Rôle", self.role_input)

        self.category_name_input = QLineEdit()
        self.category_name_input.setPlaceholderText("Nom de la catégorie")
        self.category_description_input = QLineEdit()
        self.category_description_input.setPlaceholderText(
            "Description (facultative)"
        )
        self.category_button = QPushButton("Créer la catégorie")
        self.category_button.clicked.connect(self._create_category)
        self.category_status = QLabel()

        category_form = QFormLayout()
        category_form.addRow("Nom", self.category_name_input)
        category_form.addRow("Description", self.category_description_input)

        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)

        roles_group = QGroupBox("Gestion des rôles")
        roles_layout = QVBoxLayout(roles_group)
        roles_layout.addLayout(user_form)
        roles_layout.addWidget(self.role_button)
        roles_layout.addWidget(self.role_status)

        categories_group = QGroupBox("Création d'une catégorie")
        categories_layout = QVBoxLayout(categories_group)
        categories_layout.addLayout(category_form)
        categories_layout.addWidget(self.category_button)
        categories_layout.addWidget(self.category_status)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(roles_group)
        layout.addWidget(categories_group)
        layout.addWidget(close_button)

        self._refresh_users()

    def _refresh_users(self):
        try:
            users = self.user_repository.list_users(self.admin)
        except (
            mysql.connector.Error,
            PermissionError,
            RuntimeError,
            ValueError,
        ) as error:
            QMessageBox.critical(
                self, "Utilisateurs indisponibles", str(error)
            )
            return

        self.user_roles = {user["id"]: user["role"] for user in users}
        self.user_input.clear()
        for user in users:
            self.user_input.addItem(
                f"{user['username']} ({user['role']})", user["id"]
            )
        self._sync_user_role(self.user_input.currentIndex())

    def _sync_user_role(self, index):
        user_id = self.user_input.itemData(index) if index >= 0 else None
        role = self.user_roles.get(user_id)
        self.role_input.setCurrentText(role or "user")
        has_user = user_id is not None
        is_self = user_id == self.admin.id
        self.role_input.setEnabled(has_user and not is_self)
        self.role_button.setEnabled(has_user and not is_self)
        self.role_status.setText(
            "Tu ne peux pas modifier ton propre rôle." if is_self else ""
        )

    def _change_role(self):
        user_id = self.user_input.currentData()
        if user_id is None:
            return
        if user_id == self.admin.id:
            self.role_status.setText(
                "Tu ne peux pas modifier ton propre rôle."
            )
            return
        role = self.role_input.currentText()
        try:
            self.user_repository.change_role(user_id, role, self.admin)
        except (
            mysql.connector.Error,
            LookupError,
            PermissionError,
            RuntimeError,
            ValueError,
        ) as error:
            QMessageBox.warning(self, "Modification impossible", str(error))
            return

        self.role_status.setText(f"Rôle mis à jour : {role}.")
        self._refresh_users()

    def _create_category(self):
        try:
            category = Category(
                name=self.category_name_input.text(),
                description=self.category_description_input.text().strip()
                or None,
            )
            self.question_repository.create_category(category, self.admin)
        except (
            mysql.connector.Error,
            PermissionError,
            RuntimeError,
            ValueError,
        ) as error:
            QMessageBox.warning(self, "Création impossible", str(error))
            return

        self.category_status.setText(
            f"Catégorie « {category.name} » créée."
        )
        self.category_name_input.clear()
        self.category_description_input.clear()


class ReportsDialog(QDialog):
    def __init__(self, admin, analytics_repository, parent=None):
        super().__init__(parent)
        if not admin.is_admin():
            raise PermissionError("Seul un admin peut accéder aux rapports.")

        self.admin = admin
        self.analytics_repository = analytics_repository
        self.setWindowTitle("Rapports PYASK")
        self.setMinimumWidth(440)

        title = QLabel("Générer des rapports")
        title.setObjectName("questionTitle")
        description = QLabel(
            "Choisis le type de données à exporter au format CSV."
        )
        description.setWordWrap(True)

        self.questions_export_button = QPushButton("Exporter les questions (CSV)")
        self.questions_export_button.setObjectName("questionsExportButton")
        self.questions_export_button.clicked.connect(
            self._export_question_report
        )
        questions_group = QGroupBox("Questions")
        questions_layout = QVBoxLayout(questions_group)
        questions_layout.addWidget(
            QLabel("Questions, catégories, tags et statistiques.")
        )
        questions_layout.addWidget(self.questions_export_button)

        self.answers_export_button = QPushButton("Exporter les réponses (CSV)")
        self.answers_export_button.setObjectName("answersExportButton")
        self.answers_export_button.clicked.connect(self._export_answer_report)
        answers_group = QGroupBox("Réponses")
        answers_layout = QVBoxLayout(answers_group)
        answers_layout.addWidget(
            QLabel("Réponses, auteur, question associée et score des votes.")
        )
        answers_layout.addWidget(self.answers_export_button)

        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(questions_group)
        layout.addWidget(answers_group)
        layout.addWidget(close_button)

    def _export_question_report(self):
        self._export_report(
            "questions.csv",
            self.analytics_repository.question_report,
            QUESTION_REPORT_FIELDS,
        )

    def _export_answer_report(self):
        self._export_report(
            "answers.csv",
            self.analytics_repository.answer_report,
            ANSWER_REPORT_FIELDS,
        )

    def _export_report(self, default_name, load_rows, fieldnames):
        default_path = (
            Path(__file__).resolve().parent.parent / "exports" / default_name
        )
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Enregistrer le rapport CSV",
            str(default_path),
            "Fichiers CSV (*.csv)",
        )
        if not file_path:
            return
        try:
            export_csv(load_rows(self.admin), file_path, fieldnames)
        except PermissionError as error:
            QMessageBox.warning(self, "Accès refusé", str(error))
            return
        except (
            mysql.connector.Error,
            OSError,
            RuntimeError,
            ValueError,
            csv.Error,
        ) as error:
            QMessageBox.critical(self, "Export impossible", str(error))
            return
        QMessageBox.information(self, "Export CSV", "Le rapport a été exporté.")


class CategoryStory(QWidget):
    clicked = pyqtSignal()

    def __init__(self, title, avatar_text=None):
        super().__init__()
        self.setObjectName("categoryStory")
        self.avatar_button = QPushButton(
            avatar_text if avatar_text is not None else title[:1].upper()
        )
        self.avatar_button.setObjectName("storyAvatar")
        self.avatar_button.setCheckable(True)
        self.avatar_button.setFixedSize(52, 52)
        self.avatar_button.clicked.connect(self.clicked.emit)
        label = QLabel(title)
        label.setObjectName("storyLabel")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(5)
        layout.addWidget(self.avatar_button, 0, Qt.AlignCenter)
        layout.addWidget(label)
        self.setFixedWidth(76)

    def setChecked(self, checked):
        self.avatar_button.setChecked(checked)

    def isChecked(self):
        return self.avatar_button.isChecked()


class QuestionFeedCard(QFrame):
    clicked = pyqtSignal()

    def __init__(self, question):
        super().__init__()
        self.setObjectName("questionFeedCard")
        self.setCursor(Qt.PointingHandCursor)

        title = QLabel(question.title)
        title.setObjectName("feedCardTitle")
        title.setWordWrap(True)
        avatar = QLabel(question.author.username[:1].upper())
        avatar.setObjectName("feedAvatar")
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFixedSize(38, 38)
        author = QLabel(question.author.username)
        author.setObjectName("feedAuthor")
        meta = QLabel(question.category.name)
        meta.setObjectName("feedMeta")
        excerpt = QLabel(question.body)
        excerpt.setObjectName("feedExcerpt")
        excerpt.setWordWrap(True)
        tags = QLabel("  ".join(f"#{tag.name}" for tag in question.tags))
        tags.setObjectName("feedTags")
        stats = QLabel(
            f"{question.answer_count} réponse(s)  ·  "
            f"Score {question.vote_score}"
        )
        stats.setObjectName("feedStats")
        open_button = QPushButton("Répondre")
        open_button.setObjectName("feedOpenButton")
        open_button.setToolTip("Ouvrir la discussion")
        open_button.clicked.connect(self.clicked.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)
        author_layout = QVBoxLayout()
        author_layout.setSpacing(3)
        author_layout.addWidget(author)
        author_layout.addWidget(meta)
        card_header = QHBoxLayout()
        card_header.setSpacing(12)
        card_header.addWidget(avatar)
        card_header.addLayout(author_layout)
        card_header.addStretch(1)
        layout.addLayout(card_header)
        layout.addWidget(title)
        layout.addWidget(excerpt)
        layout.addWidget(tags)
        footer = QHBoxLayout()
        footer.setSpacing(8)
        footer.addStretch(1)
        footer.addWidget(stats)
        footer.addWidget(open_button)
        layout.addLayout(footer)

        for label in (avatar, author, meta, title, excerpt, tags, stats):
            label.setAttribute(Qt.WA_TransparentForMouseEvents)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class ForumWindow(QMainWindow):
    logged_out = pyqtSignal()

    def __init__(self, user):
        super().__init__()
        self.user = user
        self.question_repository = QuestionRepository()
        self.answer_repository = AnswerRepository()
        self.vote_repository = VoteRepository()
        self.comment_repository = CommentRepository()
        self.report_repository = ReportRepository()
        self.user_repository = UserRepository()
        self.analytics_repository = AnalyticsRepository()
        self.questions_by_id = {}
        self.question_cards_by_id = {}
        self.answers_by_id = {}
        self.comments_by_id = {}
        self.current_question = None
        self.category_nav_buttons = {}

        self.setWindowTitle(f"PYASK - {user.username}")
        self.resize(1360, 860)
        self.setMinimumSize(1000, 680)

        self.question_list = QListWidget()
        self.question_list.setObjectName("questionFeed")
        self.question_list.setSpacing(9)
        self.question_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.question_list.currentItemChanged.connect(self._show_question)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Que souhaites-tu apprendre ?")
        self.search_input.setObjectName("sidebarSearch")
        self.tag_filter_input = QLineEdit()
        self.tag_filter_input.setPlaceholderText("Filtrer par tag")
        self.category_filter = QComboBox()
        self.category_filter.setObjectName("categoryFilter")
        self.category_filter.addItem("Toutes les catégories", None)
        self.sort_filter = QComboBox()
        self.sort_filter.addItem("Plus récentes", "recent")
        self.sort_filter.addItem("Plus répondues", "most_answered")
        self.sort_filter.addItem("Plus votées", "most_voted")
        self.category_nav_layout = QHBoxLayout()
        self.category_nav_layout.setSpacing(8)
        self.popular_questions = QListWidget()
        self.popular_questions.setObjectName("popularQuestions")
        self.popular_questions.setWordWrap(True)
        self.popular_questions.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.popular_questions.itemClicked.connect(
            self._open_question_from_item
        )
        self.trending_tags = QListWidget()
        self.trending_tags.setObjectName("trendingTags")
        self.trending_tags.setWordWrap(True)
        self.trending_tags.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.trending_tags.itemClicked.connect(
            self._select_trending_tag
        )

        self.question_comment_list = QListWidget()
        self.question_comment_list.setSpacing(2)
        self.question_comment_list.setSizePolicy(
            QSizePolicy.Preferred, QSizePolicy.Fixed
        )
        self.question_comment_list.currentItemChanged.connect(
            self._clear_answer_selection
        )
        self.answer_tree = QTreeWidget()
        self.answer_tree.setHeaderHidden(True)
        self.answer_tree.setWordWrap(True)
        self.answer_tree.setMinimumHeight(180)
        self.answer_tree.currentItemChanged.connect(
            self._clear_question_comment_selection
        )

        self.question_title = QLabel("Choisis une question")
        self.question_title.setObjectName("questionTitle")
        self.question_title.setWordWrap(True)
        self.question_meta = QLabel()
        self.question_meta.setObjectName("questionMeta")
        self.question_body = QPlainTextEdit()
        self.question_body.setObjectName("questionContent")
        self.question_body.setReadOnly(True)
        self.question_body.setFixedHeight(64)
        self.question_tags = QLabel()
        self.question_tags.setObjectName("questionTags")
        self.question_tags.setWordWrap(True)
        self.question_comments_empty = QLabel(
            "Aucun commentaire pour cette question."
        )
        self.question_comments_empty.setObjectName("emptyState")
        self.answers_empty = QLabel("Aucune réponse pour le moment.")
        self.answers_empty.setObjectName("emptyState")
        self.answer_input = QLineEdit()
        self.answer_input.setPlaceholderText("Écris ta réponse")
        self.question_empty_label = QLabel(
            "Aucune question trouvée. Modifie les filtres ou pose une question."
        )
        self.question_empty_label.setObjectName("emptyState")
        self.question_empty_label.setWordWrap(True)
        self.question_empty_label.hide()
        self.feed_count = QLabel()
        self.feed_count.setObjectName("feedCount")

        new_question_button = QPushButton("Poser une question")
        new_question_button.setObjectName("primaryButton")
        new_question_button.clicked.connect(self._create_question)
        clear_filters_button = QPushButton("Effacer les filtres")
        clear_filters_button.clicked.connect(self._clear_filters)
        refresh_button = QPushButton("Actualiser")
        refresh_button.clicked.connect(self._refresh_questions)
        answer_button = QPushButton("Répondre")
        answer_button.setObjectName("primaryButton")
        answer_button.clicked.connect(self._create_answer)
        upvote_button = QPushButton("Voter +1")
        upvote_button.clicked.connect(lambda: self._vote(1))
        downvote_button = QPushButton("Voter -1")
        downvote_button.clicked.connect(lambda: self._vote(-1))
        comment_button = QPushButton("Commenter")
        comment_button.clicked.connect(self._create_comment)
        report_button = QPushButton("Signaler")
        report_button.clicked.connect(self._create_report)

        header = QFrame()
        header.setObjectName("forumHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 10, 24, 10)
        header_layout.setSpacing(12)
        logo = QLabel("PYASK")
        logo.setObjectName("forumLogo")
        header_layout.addWidget(logo)
        header_layout.addStretch(1)

        logout_button = QPushButton("Déconnexion")
        logout_button.setObjectName("logoutButton")
        logout_button.clicked.connect(self._logout)
        header_layout.addWidget(logout_button)

        sidebar_content = QWidget()
        sidebar_content.setObjectName("sidebarContent")
        sidebar_layout = QVBoxLayout(sidebar_content)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(16)

        profile_card = QFrame()
        profile_card.setObjectName("sidebarCard")
        profile_card_layout = QVBoxLayout(profile_card)
        profile_card_layout.setContentsMargins(16, 16, 16, 16)
        profile_card_layout.setSpacing(16)
        profile_identity = QHBoxLayout()
        profile_identity.setSpacing(12)
        profile_avatar = QLabel(user.username[:1].upper())
        profile_avatar.setObjectName("profileAvatar")
        profile_avatar.setAlignment(Qt.AlignCenter)
        profile_avatar.setFixedSize(44, 44)
        profile_text = QVBoxLayout()
        profile_text.setSpacing(3)
        profile_name = QLabel(user.full_name or user.username)
        profile_name.setObjectName("feedAuthor")
        profile_name.setWordWrap(True)
        profile_handle = QLabel(f"@{user.username}")
        profile_handle.setObjectName("profileRole")
        profile_text.addWidget(profile_name)
        profile_text.addWidget(profile_handle)
        profile_identity.addWidget(profile_avatar)
        profile_identity.addLayout(profile_text, 1)
        profile_button = QPushButton("Profil")
        profile_button.setObjectName("profileButton")
        profile_button.setToolTip("Modifier le profil")
        profile_button.clicked.connect(self._open_profile)
        profile_identity.addWidget(profile_button)
        profile_card_layout.addLayout(profile_identity)
        sidebar_layout.addWidget(profile_card)

        navigation_card = QFrame()
        navigation_card.setObjectName("sidebarCard")
        navigation_card_layout = QVBoxLayout(navigation_card)
        navigation_card_layout.setContentsMargins(16, 16, 16, 16)
        navigation_card_layout.setSpacing(10)
        navigation_title = QLabel("NAVIGATION")
        navigation_title.setObjectName("sidebarSectionTitle")
        navigation_card_layout.addWidget(navigation_title)
        self.all_questions_button = QPushButton("Accueil")
        self.all_questions_button.setObjectName("navButton")
        self.all_questions_button.setCheckable(True)
        self.all_questions_button.setChecked(True)
        self.all_questions_button.clicked.connect(self._clear_filters)
        navigation_card_layout.addWidget(self.all_questions_button)

        participation_title = QLabel("PARTICIPER")
        participation_title.setObjectName("sidebarSectionTitle")
        navigation_card_layout.addWidget(participation_title)
        navigation_card_layout.addWidget(new_question_button)

        if user.is_moderator():
            management_title = QLabel("GESTION")
            management_title.setObjectName("sidebarSectionTitle")
            navigation_card_layout.addWidget(management_title)
            moderation_button = QPushButton("Signalements")
            moderation_button.setObjectName("navButton")
            moderation_button.clicked.connect(self._open_moderation)
            navigation_card_layout.addWidget(moderation_button)
        if user.is_admin():
            administration_button = QPushButton("Administration")
            administration_button.setObjectName("navButton")
            administration_button.clicked.connect(self._open_administration)
            navigation_card_layout.addWidget(administration_button)
            reports_button = QPushButton("Rapports")
            reports_button.setObjectName("reportsNavButton")
            reports_button.clicked.connect(self._open_reports)
            navigation_card_layout.addWidget(reports_button)
        sidebar_layout.addWidget(navigation_card)

        tools_card = QFrame()
        tools_card.setObjectName("sidebarCard")
        tools_layout = QVBoxLayout(tools_card)
        tools_layout.setContentsMargins(16, 16, 16, 16)
        tools_layout.setSpacing(8)
        tools_title = QLabel("EXPLORER")
        tools_title.setObjectName("sidebarSectionTitle")
        tools_layout.addWidget(tools_title)
        search_label = QLabel("RECHERCHE")
        search_label.setObjectName("filterFieldLabel")
        tools_layout.addWidget(search_label)
        tools_layout.addWidget(self.search_input)
        category_label = QLabel("CATÉGORIE")
        category_label.setObjectName("filterFieldLabel")
        tools_layout.addWidget(category_label)
        tools_layout.addWidget(self.category_filter)
        tag_label = QLabel("TAG")
        tag_label.setObjectName("filterFieldLabel")
        tools_layout.addWidget(tag_label)
        tools_layout.addWidget(self.tag_filter_input)
        sort_label = QLabel("TRIER PAR")
        sort_label.setObjectName("filterFieldLabel")
        tools_layout.addWidget(sort_label)
        tools_layout.addWidget(self.sort_filter)
        self.search_input.returnPressed.connect(self._refresh_questions)
        self.tag_filter_input.returnPressed.connect(self._refresh_questions)
        self.sort_filter.currentIndexChanged.connect(self._refresh_questions)
        self.category_filter.currentIndexChanged.connect(
            self._category_filter_changed
        )
        tools_layout.addWidget(clear_filters_button)
        tools_layout.addWidget(refresh_button)
        sidebar_layout.addWidget(tools_card)
        sidebar_layout.addStretch(1)

        left_scroll = QScrollArea()
        left_scroll.setObjectName("sidebarScroll")
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setFixedWidth(280)
        left_scroll.setWidget(sidebar_content)

        feed_panel = QWidget()
        feed_panel.setObjectName("timelineContent")
        feed_panel.setMinimumWidth(360)
        feed_panel.setMaximumWidth(576)
        feed_layout = QVBoxLayout(feed_panel)
        feed_layout.setContentsMargins(0, 2, 0, 16)
        feed_layout.setSpacing(16)

        stories_scroll = QScrollArea()
        stories_scroll.setObjectName("storiesScroll")
        stories_scroll.setWidgetResizable(True)
        stories_scroll.setFixedHeight(104)
        stories_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        stories_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        stories_content = QWidget()
        stories_content.setObjectName("storiesContent")
        stories_layout = QHBoxLayout(stories_content)
        stories_layout.setContentsMargins(2, 2, 2, 2)
        stories_layout.setSpacing(8)
        self.create_question_story = CategoryStory("Poser", "+")
        self.create_question_story.clicked.connect(self._create_question)
        stories_layout.addWidget(self.create_question_story)
        self.all_questions_story = CategoryStory("Tout")
        self.all_questions_story.setChecked(True)
        self.all_questions_story.clicked.connect(self._clear_filters)
        stories_layout.addWidget(self.all_questions_story)
        stories_layout.addLayout(self.category_nav_layout)
        stories_scroll.setWidget(stories_content)
        feed_layout.addWidget(stories_scroll)

        feed_heading = QHBoxLayout()
        feed_title = QLabel("Fil d'actualité")
        feed_title.setObjectName("questionTitle")
        feed_heading.addWidget(feed_title)
        feed_heading.addStretch(1)
        feed_heading.addWidget(self.feed_count)
        feed_layout.addLayout(feed_heading)
        self.question_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        feed_layout.addWidget(self.question_list, 1)
        feed_layout.addWidget(self.question_empty_label)

        self.feed_scroll = QScrollArea()
        self.feed_scroll.setObjectName("feedScroll")
        self.feed_scroll.setWidgetResizable(True)
        self.feed_scroll.setAlignment(Qt.AlignHCenter)
        self.feed_scroll.setFrameShape(QFrame.NoFrame)
        self.feed_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.feed_scroll.setWidget(feed_panel)

        aside_content = QWidget()
        aside_content.setObjectName("asideContent")
        aside_layout = QVBoxLayout(aside_content)
        aside_layout.setContentsMargins(0, 0, 0, 0)
        aside_layout.setSpacing(16)
        popular_card = QFrame()
        popular_card.setObjectName("asideCard")
        popular_layout = QVBoxLayout(popular_card)
        popular_layout.setContentsMargins(16, 16, 16, 16)
        popular_layout.setSpacing(10)
        popular_title = QLabel("Questions populaires")
        popular_title.setObjectName("asideTitle")
        popular_layout.addWidget(popular_title)
        popular_layout.addWidget(self.popular_questions)
        trending_card = QFrame()
        trending_card.setObjectName("asideCard")
        trending_layout = QVBoxLayout(trending_card)
        trending_layout.setContentsMargins(16, 16, 16, 16)
        trending_layout.setSpacing(10)
        trending_title = QLabel("Tags populaires")
        trending_title.setObjectName("asideTitle")
        trending_layout.addWidget(trending_title)
        trending_layout.addWidget(self.trending_tags)
        aside_layout.addWidget(popular_card)
        aside_layout.addWidget(trending_card)
        aside_layout.addStretch(1)
        aside_content.setFixedWidth(280)

        self.aside_scroll = QScrollArea()
        self.aside_scroll.setObjectName("asideScroll")
        self.aside_scroll.setWidgetResizable(True)
        self.aside_scroll.setFrameShape(QFrame.NoFrame)
        self.aside_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.aside_scroll.setFixedWidth(280)
        self.aside_scroll.setWidget(aside_content)

        self.discussion_dialog = QDialog(self)
        self.discussion_dialog.setWindowTitle("Discussion")
        self.discussion_dialog.setMinimumSize(620, 560)
        self.discussion_dialog.resize(720, 760)
        discussion_layout = QVBoxLayout(self.discussion_dialog)
        discussion_layout.setContentsMargins(20, 20, 20, 20)
        discussion_layout.setSpacing(12)
        discussion_content = QWidget()
        discussion_content.setObjectName("discussionContent")
        discussion_content_layout = QVBoxLayout(discussion_content)
        discussion_content_layout.setContentsMargins(0, 0, 0, 0)
        discussion_content_layout.setSpacing(12)
        question_card = QFrame()
        question_card.setObjectName("discussionQuestionCard")
        question_card_layout = QVBoxLayout(question_card)
        question_card_layout.setSpacing(7)
        question_card_layout.addWidget(self.question_title)
        question_card_layout.addWidget(self.question_meta)
        question_card_layout.addWidget(self.question_body)
        question_card_layout.addWidget(self.question_tags)
        discussion_content_layout.addWidget(question_card)

        question_comments_group = QGroupBox("Commentaires sur la question")
        question_comments_layout = QVBoxLayout(question_comments_group)
        question_comments_layout.addWidget(self.question_comments_empty)
        question_comments_layout.addWidget(self.question_comment_list)
        discussion_content_layout.addWidget(question_comments_group)

        answers_group = QGroupBox("Réponses et commentaires")
        answers_layout = QVBoxLayout(answers_group)
        answers_layout.addWidget(self.answers_empty)
        answers_layout.addWidget(self.answer_tree, 1)
        discussion_content_layout.addWidget(answers_group)
        discussion_content_layout.addStretch(1)

        discussion_scroll = QScrollArea()
        discussion_scroll.setObjectName("discussionScroll")
        discussion_scroll.setWidgetResizable(True)
        discussion_scroll.setFrameShape(QFrame.NoFrame)
        discussion_scroll.setWidget(discussion_content)
        discussion_layout.addWidget(discussion_scroll, 1)

        answer_entry_layout = QHBoxLayout()
        answer_entry_layout.addWidget(self.answer_input, 1)
        answer_entry_layout.addWidget(answer_button)
        discussion_layout.addLayout(answer_entry_layout)

        discussion_actions = QHBoxLayout()
        discussion_actions.addWidget(upvote_button)
        discussion_actions.addWidget(downvote_button)
        discussion_actions.addWidget(comment_button)
        discussion_actions.addWidget(report_button)
        discussion_layout.addLayout(discussion_actions)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setHandleWidth(1)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.addWidget(left_scroll)
        self.splitter.addWidget(self.feed_scroll)
        self.splitter.addWidget(self.aside_scroll)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)
        self.splitter.setSizes([280, 760, 280])

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 12, 18, 12)
        content_layout.addWidget(self.splitter)
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)
        page_layout.addWidget(header)
        page_layout.addWidget(content, 1)
        self.setCentralWidget(page)
        self._update_responsive_layout()
        self._refresh_category_filter()
        self._refresh_questions()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "aside_scroll"):
            self._update_responsive_layout()

    def _update_responsive_layout(self):
        show_aside = self.width() >= 1060
        if self.aside_scroll.isHidden() == show_aside:
            self.aside_scroll.setVisible(show_aside)
            center_width = self.splitter.width() - 561 if show_aside else (
                self.splitter.width() - 281
            )
            self.splitter.setSizes(
                [280, max(360, center_width), 280 if show_aside else 0]
            )

    def _open_moderation(self):
        dialog = ModerationDialog(self.user, self.report_repository, self)
        dialog.exec_()

    def _open_profile(self):
        dialog = ProfileDialog(self.user, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        self._save_profile(
            dialog.full_name_input.text(),
            dialog.bio_input.toPlainText(),
        )

    def _logout(self):
        self.logged_out.emit()

    def _save_profile(self, full_name, bio):
        full_name = full_name.strip() or None
        bio = bio.strip() or None
        if full_name is not None and len(full_name) > 100:
            QMessageBox.warning(
                self, "Profil invalide", "Le nom complet est trop long."
            )
            return
        if bio is not None and len(bio) > 255:
            QMessageBox.warning(
                self,
                "Profil invalide",
                "La bio ne peut pas dépasser 255 caractères.",
            )
            return

        try:
            self.user_repository.update_profile(
                self.user.id,
                full_name=full_name,
                bio=bio,
            )
        except (
            mysql.connector.Error,
            LookupError,
            RuntimeError,
            ValueError,
        ) as error:
            QMessageBox.warning(self, "Profil non enregistré", str(error))
            return

        self.user.full_name = full_name
        self.user.bio = bio
        QMessageBox.information(self, "Mon profil", "Profil mis à jour.")

    def _open_administration(self):
        dialog = AdministrationDialog(
            self.user,
            self.user_repository,
            self.question_repository,
            self,
        )
        dialog.exec_()
        self._refresh_category_filter()

    def _open_reports(self):
        dialog = ReportsDialog(self.user, self.analytics_repository, self)
        dialog.exec_()

    def _refresh_category_filter(self):
        selected_category_id = self.category_filter.currentData()
        try:
            categories = self.question_repository.list_categories()
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Catégories indisponibles", str(error))
            return

        self.category_filter.blockSignals(True)
        self.category_filter.clear()
        self.category_filter.addItem("Toutes les catégories", None)
        for category in categories:
            self.category_filter.addItem(category.name, category.id)
        if selected_category_id is not None:
            index = self.category_filter.findData(selected_category_id)
            if index >= 0:
                self.category_filter.setCurrentIndex(index)
        self.category_filter.blockSignals(False)

        while self.category_nav_layout.count():
            item = self.category_nav_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self.category_nav_buttons.clear()
        for category in categories:
            story = CategoryStory(category.name)
            story.clicked.connect(
                lambda _checked=False, category_id=category.id:
                    self._select_category(category_id)
            )
            self.category_nav_layout.addWidget(story)
            self.category_nav_buttons[category.id] = story
        self._update_category_nav_selection()

    def _update_category_nav_selection(self):
        selected_category_id = self.category_filter.currentData()
        self.all_questions_button.setChecked(selected_category_id is None)
        self.all_questions_story.setChecked(selected_category_id is None)
        for category_id, button in self.category_nav_buttons.items():
            button.setChecked(category_id == selected_category_id)

    def _select_category(self, category_id):
        index = self.category_filter.findData(category_id)
        if index < 0:
            return
        self.category_filter.setCurrentIndex(index)

    def _category_filter_changed(self, _index):
        self._update_category_nav_selection()
        self._refresh_questions()

    def _select_question(self, question_id):
        for index in range(self.question_list.count()):
            item = self.question_list.item(index)
            if item.data(Qt.UserRole) == question_id:
                self.question_list.setCurrentItem(item)
                self.question_list.scrollToItem(item)
                self.feed_scroll.ensureWidgetVisible(
                    self.question_cards_by_id[question_id]
                )
                return

    def _open_question_from_item(self, item):
        self._open_question_discussion(item.data(Qt.UserRole))

    def _open_question_discussion(self, question_id):
        self._select_question(question_id)
        if (
            self.current_question is not None
            and self.current_question.id == question_id
        ):
            self.discussion_dialog.exec_()

    def _select_trending_tag(self, item):
        self.tag_filter_input.setText(item.data(Qt.UserRole))
        self._refresh_questions()

    def _set_selected_feed_card(self, question_id):
        for card_id, card in self.question_cards_by_id.items():
            selected = card_id == question_id
            if card.property("selected") == selected:
                continue
            card.setProperty("selected", selected)
            card.style().unpolish(card)
            card.style().polish(card)

    def _refresh_questions(self):
        selected_id = (
            self.current_question.id if self.current_question is not None else None
        )
        try:
            questions = self.question_repository.list_questions(
                search_text=self.search_input.text(),
                tag_name=self.tag_filter_input.text(),
                category_id=self.category_filter.currentData(),
                sort=self.sort_filter.currentData(),
            )
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Chargement impossible", str(error))
            return

        self.questions_by_id = {question.id: question for question in questions}
        self.question_list.clear()
        self.question_cards_by_id = {}
        self.popular_questions.clear()
        for question in questions:
            item = QListWidgetItem()
            item.setToolTip(
                f"{question.title}\n{question.category.name} · "
                f"{question.author.username}"
            )
            item.setData(Qt.UserRole, question.id)
            card = QuestionFeedCard(question)
            item.setSizeHint(card.sizeHint())
            self.question_list.addItem(item)
            self.question_list.setItemWidget(item, card)
            self.question_cards_by_id[question.id] = card
            card.clicked.connect(
                lambda question_id=question.id:
                    self._open_question_discussion(question_id)
            )

        popular = sorted(
            questions,
            key=lambda question: (
                question.answer_count,
                question.vote_score,
            ),
            reverse=True,
        )[:4]
        for question in popular:
            popular_item = QListWidgetItem(
                f"{question.title}\n"
                f"{question.answer_count} réponse(s) · score {question.vote_score}"
            )
            popular_item.setData(Qt.UserRole, question.id)
            self.popular_questions.addItem(popular_item)
        if not popular:
            empty_item = QListWidgetItem("Aucune question à afficher.")
            empty_item.setFlags(Qt.NoItemFlags)
            self.popular_questions.addItem(empty_item)

        self.trending_tags.clear()
        tag_counts = {}
        for question in questions:
            for tag in question.tags:
                tag_counts[tag.name] = tag_counts.get(tag.name, 0) + 1
        trending_tags = sorted(
            tag_counts.items(), key=lambda item: (-item[1], item[0])
        )[:6]
        for tag_name, question_count in trending_tags:
            tag_item = QListWidgetItem(
                f"#{tag_name}  ·  {question_count} question(s)"
            )
            tag_item.setData(Qt.UserRole, tag_name)
            self.trending_tags.addItem(tag_item)
        if not trending_tags:
            empty_item = QListWidgetItem("Aucun tag à afficher.")
            empty_item.setFlags(Qt.NoItemFlags)
            self.trending_tags.addItem(empty_item)

        has_questions = bool(questions)
        self.question_list.setVisible(has_questions)
        self.question_empty_label.setVisible(not has_questions)
        self.feed_count.setText(
            f"{len(questions)} question(s)" if has_questions else "0 question"
        )

        if selected_id is not None:
            previous_item = next(
                (
                    self.question_list.item(index)
                    for index in range(self.question_list.count())
                    if self.question_list.item(index).data(Qt.UserRole)
                    == selected_id
                ),
                None,
            )
            if previous_item is not None:
                self.question_list.setCurrentItem(previous_item)
                return
        if self.question_list.count():
            self.question_list.setCurrentRow(0)
        else:
            self._show_question(None, None)

    def _clear_filters(self):
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self.tag_filter_input.clear()
        self.category_filter.blockSignals(True)
        self.category_filter.setCurrentIndex(0)
        self.category_filter.blockSignals(False)
        self.sort_filter.blockSignals(True)
        self.sort_filter.setCurrentIndex(0)
        self.sort_filter.blockSignals(False)
        self._update_category_nav_selection()
        self._refresh_questions()

    def _show_question(self, item, _previous):
        self.answers_by_id = {}
        self.comments_by_id = {}
        self.question_comment_list.clear()
        self.answer_tree.clear()
        if item is None:
            self.current_question = None
            self._set_selected_feed_card(None)
            self.question_title.setText("Aucune question")
            self.question_meta.clear()
            self.question_body.clear()
            self.question_tags.clear()
            self.question_comments_empty.setText(
                "Sélectionne une question pour voir ses commentaires."
            )
            self.question_comments_empty.show()
            self.question_comment_list.hide()
            self.answers_empty.setText(
                "Sélectionne une question pour voir les réponses."
            )
            self.answers_empty.show()
            self.answer_tree.hide()
            return

        question_id = item.data(Qt.UserRole)
        self.current_question = self.questions_by_id.get(question_id)
        if self.current_question is None:
            return

        self._set_selected_feed_card(question_id)
        question = self.current_question
        self.question_title.setText(question.title)
        self.question_meta.setText(
            f"{question.category.name} · {question.author.username} · "
            f"{question.answer_count} réponse(s) · score {question.vote_score}"
        )
        self.question_body.setPlainText(question.body)
        self.question_tags.setText(
            "Tags : " + ", ".join(tag.name for tag in question.tags)
        )
        try:
            answers = self.answer_repository.list_for_question(question.id)
            comments = self.comment_repository.list_for_question(question.id)
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Chargement impossible", str(error))
            return

        self.answers_by_id = {answer.id: answer for answer in answers}
        self.comments_by_id = {comment.id: comment for comment in comments}
        question_comments = [
            comment for comment in comments if comment.question_id == question.id
        ]
        if not question_comments:
            self.question_comments_empty.setText(
                "Aucun commentaire pour cette question."
            )
        self.question_comment_list.setVisible(bool(question_comments))
        self.question_comments_empty.setVisible(not question_comments)
        for comment in comments:
            if comment.question_id == question.id:
                comment_item = QListWidgetItem(
                    f"{comment.author.username} : {comment.body}"
                )
                comment_item.setData(Qt.UserRole, comment.id)
                self.question_comment_list.addItem(comment_item)
        if question_comments:
            comment_height = min(
                120, max(52, self.question_comment_list.count() * 34 + 16)
            )
            self.question_comment_list.setFixedHeight(comment_height)

        if not answers:
            self.answers_empty.setText("Aucune réponse pour le moment.")
        self.answer_tree.setVisible(bool(answers))
        self.answers_empty.setVisible(not answers)
        for answer in answers:
            answer_item = QTreeWidgetItem(
                self.answer_tree,
                [
                    f"{answer.author.username} · score {answer.score}\n"
                    f"{answer.body}"
                ],
            )
            answer_item.setData(0, Qt.UserRole, ("answer", answer.id))
            for comment in comments:
                if comment.answer_id == answer.id:
                    comment_item = QTreeWidgetItem(
                        answer_item,
                        [f"{comment.author.username} : {comment.body}"],
                    )
                    comment_item.setData(0, Qt.UserRole, ("comment", comment.id))
        self.answer_tree.expandAll()

    def _selected_answer(self):
        item = self.answer_tree.currentItem()
        if item is None or item.parent() is not None:
            return None
        item_type, answer_id = item.data(0, Qt.UserRole)
        if item_type != "answer":
            return None
        return self.answers_by_id.get(answer_id)

    def _selected_comment(self):
        question_comment = self.question_comment_list.currentItem()
        if question_comment is not None:
            return self.comments_by_id.get(question_comment.data(Qt.UserRole))

        item = self.answer_tree.currentItem()
        if item is None or item.parent() is None:
            return None
        item_type, comment_id = item.data(0, Qt.UserRole)
        if item_type != "comment":
            return None
        return self.comments_by_id.get(comment_id)

    def _clear_answer_selection(self, item, _previous):
        if item is not None:
            self.answer_tree.setCurrentItem(None)

    def _clear_question_comment_selection(self, item, _previous):
        if item is not None:
            self.question_comment_list.setCurrentItem(None)

    def _comment_target(self):
        comment = self._selected_comment()
        if comment is not None:
            return comment.question_id, comment.answer_id
        answer = self._selected_answer()
        if answer is not None:
            return None, answer.id
        return self.current_question.id, None

    def _create_question(self):
        try:
            categories = self.question_repository.list_categories()
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Chargement impossible", str(error))
            return

        dialog = QuestionDialog(categories, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        try:
            tags = [
                Tag(name)
                for name in dialog.tags_input.text().split(",")
                if name.strip()
            ]
            question = Question(
                author=self.user,
                title=dialog.title_input.text(),
                body=dialog.body_input.toPlainText(),
                category=dialog.category_input.currentData(),
                tags=tags,
            )
            self.question_repository.create(question)
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "Question non enregistrée", str(error))
            return
        self._refresh_questions()

    def _create_answer(self):
        if self.current_question is None:
            QMessageBox.information(self, "Réponse", "Choisis d'abord une question.")
            return
        try:
            answer = Answer(
                author=self.user,
                body=self.answer_input.text(),
                question_id=self.current_question.id,
            )
            self.answer_repository.create(answer)
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "Réponse non enregistrée", str(error))
            return
        self.answer_input.clear()
        self._show_question(self.question_list.currentItem(), None)

    def _vote(self, value):
        answer = self._selected_answer()
        if answer is None:
            QMessageBox.information(self, "Vote", "Choisis d'abord une réponse.")
            return
        try:
            self.vote_repository.cast_vote(answer, self.user, value)
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "Vote non enregistré", str(error))
            return
        self._show_question(self.question_list.currentItem(), None)

    def _create_comment(self):
        if self.current_question is None:
            QMessageBox.information(
                self, "Commentaire", "Choisis d'abord une question."
            )
            return
        body, accepted = QInputDialog.getMultiLineText(
            self, "Ajouter un commentaire", "Commentaire :"
        )
        if not accepted:
            return
        question_id, answer_id = self._comment_target()
        try:
            comment = Comment(
                author=self.user,
                body=body,
                question_id=question_id,
                answer_id=answer_id,
            )
            self.comment_repository.create(comment)
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "Commentaire non enregistré", str(error))
            return
        self._show_question(self.question_list.currentItem(), None)

    def _create_report(self):
        if self.current_question is None:
            QMessageBox.information(
                self, "Signalement", "Choisis d'abord une question."
            )
            return
        reason, accepted = QInputDialog.getText(
            self, "Signaler un contenu", "Motif :"
        )
        if not accepted:
            return
        comment = self._selected_comment()
        answer = self._selected_answer()
        question_id = None
        answer_id = None
        comment_id = None
        if comment is not None:
            comment_id = comment.id
        elif answer is not None:
            answer_id = answer.id
        else:
            question_id = self.current_question.id
        try:
            report = Report(
                reporter=self.user,
                reason=reason,
                question_id=question_id,
                answer_id=answer_id,
                comment_id=comment_id,
            )
            self.report_repository.create(report)
        except (mysql.connector.Error, RuntimeError, ValueError) as error:
            QMessageBox.warning(self, "Signalement non enregistré", str(error))
            return
        QMessageBox.information(self, "Signalement", "Signalement enregistré.")


def main():
    application = QApplication(sys.argv)
    _load_application_fonts()
    application.setStyleSheet(APP_STYLESHEET)
    login_window = LoginWindow()
    forum_windows = []

    def return_to_login(forum_window):
        login_window.reset_for_login()
        login_window.show()
        login_window.raise_()
        login_window.activateWindow()
        forum_window.close()
        forum_window.deleteLater()
        forum_windows.remove(forum_window)

    def open_forum(user):
        forum_window = ForumWindow(user)
        forum_windows.append(forum_window)
        forum_window.logged_out.connect(
            lambda window=forum_window: return_to_login(window)
        )
        forum_window.show()
        login_window.hide()

    login_window.authenticated.connect(open_forum)
    login_window.show()
    return application.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

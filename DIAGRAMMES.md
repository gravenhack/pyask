# Diagrammes PYASK

Ces diagrammes décrivent les classes du modèle et les fonctionnalités
actuellement accessibles dans l'interface PyQt5.

## Diagramme de classes

```mermaid
classDiagram
    direction TB

    class User {
        +id
        +username
        +email
        -password_hash
        -role
        +hash_password(password)
        +check_password(password)
        +verify_password(password, password_hash)
        +change_password(old_password, new_password)
        +change_role(new_role, by_user)
        +is_admin()
        +is_moderator()
    }

    class UserSummary {
        +id
        +username
        +role
        +full_name
    }

    class Category {
        +id
        +name
        +description
    }

    class Tag {
        +id
        +name
        +__eq__(other)
        +__hash__()
    }

    class Post {
        +id
        +author
        +body
        +created_at
    }

    class Question {
        +title
        +category
        +tags
        +updated_at
        +add_tag(tag)
        +remove_tag(tag)
        +validate()
    }

    class Answer {
        +question_id
        -votes
        +score
        +vote(user, value)
    }

    class Comment {
        +question_id
        +answer_id
    }

    class Report {
        +id
        +reporter
        +reason
        +question_id
        +answer_id
        +comment_id
        +status
        +reviewed_by
        +reviewed_at
        +mark_reviewed(moderator, status)
    }

    Post <|-- Question
    Post <|-- Answer
    Post <|-- Comment

    User "1" --> "0..*" Post : auteur lors de la création
    UserSummary "1" --> "0..*" Post : auteur affiché après lecture
    Category "1" <-- "0..*" Question : catégorie obligatoire
    Question "0..*" -- "0..*" Tag : tags (1 à 3 à l'enregistrement)
    Question "1" <-- "0..*" Answer : question_id
    Question "0..1" <-- "0..*" Comment : cible possible
    Answer "0..1" <-- "0..*" Comment : cible possible
    User "1" <-- "0..*" Report : reporter
    User "0..1" <-- "0..*" Report : reviewed_by
    Question "0..1" <-- "0..*" Report : cible possible
    Answer "0..1" <-- "0..*" Report : cible possible
    Comment "0..1" <-- "0..*" Report : cible possible
```

Chaque commentaire et chaque signalement vise exactement une cible parmi les
liens indiqués. Les votes sont conservés comme associations utilisateur/valeur
dans `Answer` et dans la table SQL `answer_votes`; il n'existe pas de classe
Python `Vote`.

## Diagramme de cas d'utilisation

```mermaid
flowchart LR
    visitor[Visiteur]
    member[Utilisateur connecté]
    moderator[Modérateur ou admin]
    admin[Administrateur]

    subgraph app[Application PYASK]
        register((Créer un compte))
        login((Se connecter))
        profile((Modifier son profil))
        password((Changer son mot de passe))
        theme((Basculer clair/sombre))
        browse((Consulter les questions))
        filter((Rechercher, filtrer et trier))
        ask((Poser une question))
        answer((Répondre))
        vote((Voter sur une réponse))
        comment((Commenter une question ou réponse))
        report((Signaler un contenu))
        export((Exporter les rapports en CSV ou ZIP))
        review((Masquer ou rejeter un signalement))
        manage_roles((Gérer les rôles utilisateurs))
        create_category((Créer une catégorie))
    end

    visitor --> register
    visitor --> login
    member --> profile
    member --> password
    member --> theme
    member --> browse
    member --> filter
    member --> ask
    member --> answer
    member --> vote
    member --> comment
    member --> report
    admin --> export
    moderator --> review
    admin --> manage_roles
    admin --> create_category
```

Les catégories ne peuvent pas être supprimées lorsqu'elles sont utilisées par
des questions. Traiter un signalement masque sa cible sans la supprimer et
conserve la trace du modérateur, du motif et de la date. Les utilisateurs
ordinaires voient un remplacement; les modérateurs et admins peuvent consulter
le contenu original. Rejeter le signalement laisse le contenu visible.

Le profil permet de modifier le nom d'utilisateur, le nom complet et la bio.
Le changement de mot de passe exige le mot de passe actuel et la confirmation
du nouveau. Le thème clair/sombre est mémorisé localement par l'application.

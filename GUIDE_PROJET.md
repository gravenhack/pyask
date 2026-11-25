# Guide de réalisation de PYASK, de A à Z

Ce guide présente un ordre de travail logique pour comprendre, construire,
tester et présenter PYASK. Il s'appuie sur le projet existant, pas sur une
architecture théorique différente de celle du dépôt.

## 1. Comprendre le sujet et fixer le périmètre

Avant de coder, reformuler le besoin en fonctionnalités vérifiables :

1. Les utilisateurs peuvent s'inscrire, se connecter, se déconnecter et
   modifier leur profil.
2. Ils peuvent publier des questions classées par catégorie et accompagnées
   de tags.
3. Ils peuvent répondre, voter sur les réponses et commenter une question ou
   une réponse.
4. Ils peuvent rechercher et filtrer les questions.
5. Ils peuvent signaler du contenu ; les modérateurs et administrateurs
   traitent les signalements.
6. Les administrateurs peuvent gérer les rôles et les catégories.
7. Les rapports de questions et de réponses peuvent être exportés en CSV.

Pour chaque fonctionnalité, écrire un scénario simple : qui agit, sur quoi,
et quel résultat est attendu. Cela évite de commencer l'interface avant de
savoir quelles données et quelles règles elle doit respecter.

## 2. Décider les règles métier

Établir les règles avant de créer les tables ou les écrans. Pour PYASK, les
principales décisions sont :

- Une question a un auteur et une catégorie obligatoire.
- Une question a de 1 à 3 tags.
- Une réponse appartient à une question.
- Un vote porte sur une réponse : un seul vote par utilisateur et par
  réponse, avec une valeur positive ou négative.
- Un commentaire cible exactement une question ou une réponse.
- Un signalement cible exactement un contenu ; un modérateur ou un
  administrateur le traite ou le rejette.
- Un compte ne peut pas se donner lui-même un autre rôle ; le dernier
  administrateur ne peut pas être rétrogradé.

Consigner les décisions et les cas limites dans
[PYASK_DECISIONS.md](./PYASK_DECISIONS.md). Cette étape sert de référence aux
modèles, à la base de données et aux tests.

## 3. Concevoir les données et les classes

### Base de données

1. Identifier les entités : utilisateurs, catégories, questions, tags,
   réponses, votes, commentaires et signalements.
2. Définir les clés primaires et étrangères, les contraintes d'unicité et le
   comportement des suppressions.
3. Repérer les règles qui ne peuvent pas être garanties simplement par une
   contrainte SQL et les faire respecter dans le code.
4. Dessiner le schéma relationnel avant de l'implémenter.

Le schéma SQL du dépôt est dans [database/schema.sql](./database/schema.sql).
**Attention : il contient une commande qui supprime puis recrée `pyask_db`.**
Ne l'exécuter que dans un environnement jetable ou après avoir vérifié la
cible et sauvegardé les données à préserver. Le nom configuré dans `.env` ne
change pas automatiquement la base ciblée par ce script.

### Modèles Python

Construire les objets du domaine et leurs règles avant de les relier à
l'interface. Les classes principales se trouvent dans [models/](./models/) :
`User`, `Post`, `Question`, `Answer`, `Comment`, `Category`, `Tag` et
`Report`. `Question`, `Answer` et `Comment` partagent les éléments communs
de `Post`.

Vérifier leurs validations avec les tests de modèles avant de passer à MySQL.

## 4. Préparer l'environnement et la base

Depuis la racine du dépôt :

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Configurer MySQL dans `.env` à partir de `.env.example`. Le fichier `.env`
est ignoré par Git : ne jamais y mettre des identifiants dans un fichier
suivi par Git, un rapport ou une capture d'écran. `PYASK_DB_USER` et
`PYASK_DB_PASSWORD` sont requis ; l'hôte, le port et le nom de la base ont
des valeurs par défaut. Le chargement et la validation de cette configuration
sont dans [config.py](./config.py).

Avant d'initialiser une base, vérifier les points suivants :

- le serveur MySQL fonctionne ;
- le compte configuré a les droits nécessaires ;
- la base ciblée est bien celle prévue ;
- le schéma SQL ne va pas effacer de données utiles.

Dans le dépôt actuel, `database/schema.sql` vise `pyask_db`, tandis que les
données de démonstration sont réservées à `pyask_validation_20261124`.
Conserver ces deux usages distincts et ne jamais lancer le seed contre une
base contenant des données à préserver.

## 5. Organiser l'accès à la base

La connexion est centralisée dans
[database/connection.py](./database/connection.py). Les dépôts de
[database/](./database/) regroupent les requêtes MySQL, par exemple :

- `UserRepository` pour les comptes et les profils ;
- `QuestionRepository` pour les catégories et les questions ;
- des dépôts dédiés aux réponses, votes, commentaires, signalements et
  rapports.

Garder les requêtes SQL dans les dépôts, et non dans les widgets Qt. Les
opérations sensibles doivent aussi vérifier les permissions dans les dépôts :
masquer un bouton dans l'interface ne suffit pas à protéger une action.

Dans l'organisation actuelle, les dépôts sont la couche d'accès aux données ;
il n'y a pas de paquet `services/` séparé. L'interface principale est encore
regroupée dans `ui/main_window.py`, conformément à la réorganisation
progressive du projet.

## 6. Implémenter les fonctionnalités dans l'ordre

Avancer par petits flux complets : modèle, dépôt, interface, test.

1. **Comptes** : inscription, hachage des mots de passe, authentification,
   profil et déconnexion.
2. **Catégories et questions** : lister les catégories, créer une question,
   lui associer ses tags, puis afficher et rechercher les questions.
3. **Réponses** : enregistrer et afficher les réponses d'une question.
4. **Votes et commentaires** : appliquer les règles d'unicité et de cible.
5. **Signalements** : créer un signalement sans doublon et permettre son
   traitement par un modérateur ou un administrateur.
6. **Administration** : gérer les rôles et créer les catégories, tout en
   protégeant le dernier administrateur et le rôle de l'administrateur
   connecté.
7. **Statistiques et export** : calculer les rapports et exporter les lignes
   au format CSV.

Après chaque étape, vérifier le cas normal, un cas invalide et les permissions
concernées. Ne pas attendre la fin du projet pour découvrir que les règles
métier ou le schéma ne correspondent pas aux écrans.

## 7. Construire l'interface

Une fois les opérations principales disponibles dans les modèles et les
dépôts, les relier à l'interface PyQt5 :

1. écran d'inscription et de connexion ;
2. fenêtre principale et fil des questions ;
3. écran ou dialogue de discussion avec réponses et commentaires ;
4. profil ;
5. administration et modération ;
6. recherche, filtres, tris et export CSV.

L'interface se trouve actuellement dans [ui/main_window.py](./ui/main_window.py)
et son style Qt dans [ui/styles.qss](./ui/styles.qss). Le lancement se fait
depuis [main.py](./main.py). Conserver le même modèle de données et les mêmes
règles métier, que l'action soit déclenchée par un bouton ou par un test.

## 8. Tester au fur et à mesure

Pour chaque règle métier, écrire un test ciblé. Tester séparément :

- les modèles et leurs validations ;
- les dépôts et les opérations MySQL ;
- les écrans PyQt et les interactions importantes ;
- les cas de permission et les erreurs ;
- les rapports et le contenu du CSV.

Lancer toute la suite depuis la racine du dépôt :

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Ne pas considérer un écran qui s'ouvre comme une preuve suffisante : vérifier
aussi que les données affichées, les changements enregistrés et les erreurs
correspondent au résultat attendu.

## 9. Ajouter les données de démonstration

Le seed existant est additif et réexécutable, mais il est explicitement
verrouillé sur `pyask_validation_20261124`. Il ajoute les données manquantes
et refuse d'écrire si la base configurée ou la base réellement connectée ne
correspond pas.

Pour remplir la base de validation :

```bash
PYASK_DB_NAME=pyask_validation_20261124 \
  .venv/bin/python -m database.seed_demo_data
```

Pour voir ces données dans l'application, lancer celle-ci avec le même nom
de base :

```bash
PYASK_DB_NAME=pyask_validation_20261124 .venv/bin/python main.py
```

Le seed crée des mots de passe aléatoires dont les valeurs ne sont pas
conservées. Les comptes de démo servent donc d'auteurs aux publications, pas
de comptes de connexion. Le script est dans
[database/seed_demo_data.py](./database/seed_demo_data.py).

## 10. Vérifier le projet avant la remise

Faire une validation fonctionnelle avec un compte utilisateur, puis avec un
compte modérateur ou administrateur :

- inscription, connexion, modification du profil et déconnexion ;
- publication, consultation, réponse, vote et commentaires ;
- recherche par texte, filtres par tag/catégorie et tris ;
- signalement puis traitement par un rôle autorisé ;
- gestion des rôles et création de catégories ;
- export de rapports CSV dans `exports/` ;
- affichage correct après actualisation et après redémarrage.

Vérifier aussi les éléments de livraison :

- `README.md` explique l'installation, la configuration et le lancement ;
- [DIAGRAMMES.md](./DIAGRAMMES.md) contient les diagrammes attendus ;
- `.env` et les exports générés ne sont pas ajoutés à Git ;
- les tests passent et aucun changement non voulu n'est inclus.

## 11. Préparer la démonstration orale

Un ordre de présentation simple :

1. expliquer le besoin et les rôles ;
2. montrer brièvement le modèle de données et les relations ;
3. expliquer la séparation modèles, dépôts et interface ;
4. démontrer le parcours d'un utilisateur : question, réponse, vote et
   commentaire ;
5. montrer les filtres, la modération, l'administration et l'export ;
6. présenter les tests et les choix de sécurité ;
7. terminer par les limites connues et les améliorations futures.

Utiliser des comptes de démonstration dont les identifiants sont connus et
autorisés pour la présentation ; les comptes créés par le seed ne sont pas
destinés à la connexion.

## État actuel du dépôt

L'application, ses dépôts, modèles, interface, seed et tests sont déjà
présents. La dernière vérification de la suite a réussi avec 38 tests.
La vérification visuelle complète sur le bureau reste une étape utile avant
la remise. Pour l'historique des décisions et des étapes réalisées, consulter
[PYASK_DECISIONS.md](./PYASK_DECISIONS.md).

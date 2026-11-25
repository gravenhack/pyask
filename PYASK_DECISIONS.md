# PYASK : décisions et avancement

Projet 6 : Question/Answer Forum Management System (Python + MySQL), en binôme.
Dernière mise à jour : 25/11/2026

---

## 1. Ce qui est demandé (cahier des charges)

1. **Utilisateurs** : inscription, connexion, gestion du profil. L'admin gère les rôles (utilisateur, modérateur, admin).
2. **Questions et réponses** : poster une question avec catégories et tags, répondre, voter pour ou contre une réponse.
3. **Commentaires** sur les questions et sur les réponses.
4. **Recherche et filtres** : par mots-clés, tags, catégories. Tri par plus récentes, plus répondues, plus votées.
5. **Modération** : signaler un contenu inapproprié.
6. **Rapports** : sur les questions et réponses, avec export CSV.

Le cahier des charges **ne demande pas** la suppression de compte.

---

## 2. Règles métier décidées

| Sujet | Décision |
|---|---|
| Auteur | Toute question, réponse et commentaire a un auteur (un utilisateur) |
| Réponse | On répond à une question |
| Vote | Uniquement sur les réponses (+1 ou -1), **un vote par utilisateur et par réponse**. Pas de vote sur une question ni un commentaire |
| Commentaire | Attaché à **une question OU une réponse**, jamais à un autre commentaire |
| Catégorie | **Une seule par question, obligatoire**. Créée par l'**admin** seulement |
| Tags | **De 1 à 3 par question**. Créés par les utilisateurs, en minuscules, sans doublon |
| Recherche par mot-clé | Cherche le mot dans le titre et le texte des questions (sans lien avec les tags) |
| Plus répondu / plus voté | **Calculés à la demande** (on compte les réponses et les votes), pas de compteur stocké |
| Signalement ("report" = contenu signalé) | **Stocké en base** : qui signale, quel contenu, pourquoi, statut (en attente, traité, rejeté); exactement une cible est vérifiée en Python et par triggers SQL |
| Traitement d'un signalement | Modérateur/admin le marque comme traité ou le rejette; le contenu signalé n'est pas supprimé automatiquement |
| Rapport ("report" = résumé calculé) | **Réservé aux admins**, calculé à la demande; questions et réponses exportées en CSV séparés |
| Interface des rapports | Une section « Rapports » visible uniquement par les admins, avec une action d'export par type de données |
| Filtre catégorie | Disponible dans la barre latérale et synchronisé avec les raccourcis de catégories du fil |
| Fond d'écran | L'image fournie est utilisée uniquement sur l'écran de connexion; le forum conserve son fond sombre uni |
| Suppression d'un utilisateur | **Option A : tout est supprimé avec lui** (questions, réponses, commentaires, votes, signalements) |

Conséquence à connaître : supprimer un utilisateur supprime ses questions, donc aussi toutes les réponses des autres à ces questions.

---

## 3. Base de données

Nom de la base : `pyask_db`. Script de schéma : `database/schema.sql`.

9 tables : `users`, `categories`, `questions`, `tags`, `question_tags` (liaison), `answers`, `answer_votes`, `comments`, `reports`.

Comportement des suppressions :
- Lien vers `users` : `CASCADE`, sauf `reports.reviewed_by` en `SET NULL`.
- `questions.category_id` : `RESTRICT` (on ne supprime pas une catégorie utilisée).
- Liens vers `questions` et `answers` : `CASCADE`.

**Règles vérifiées en Python (pas dans la base) :**
- 1 à 3 tags par question
- un commentaire est lié à exactement une question OU une réponse
- un signalement est lié à exactement un contenu
- pas de signalement en double du même contenu par le même utilisateur

---

## 4. Étapes

- [x] Nom du projet : PYASK
- [x] Repo GitHub créé et cloné
- [x] Compréhension du sujet
- [x] Règles métier décidées
- [x] Schéma de la base défini
- [x] Script SQL écrit
- [x] Copie du script exécutée sans erreur sur `pyask_validation_20261124` (9 tables créées; `pyask_db` non modifiée)
- [x] Test des suppressions en chaîne sur la base de validation : tous les compteurs sont à 0 après suppression; transaction annulée
- [x] **Classes Python (POO)**
  - [x] Classes du modèle créées dans `models/`
  - [x] Ajouter des tests unitaires ciblés pour les règles métier des modèles
    - [x] Tests initiaux de `Tag` : normalisation, longueur maximale et nom vide
    - [x] Tests pour `User`, `Category`, `Post`, `Question`, `Answer`, `Comment` et `Report`
    - [x] Exécution des 23 tests réussie avec `python3 -m unittest discover -s tests -v`
  - [x] Corriger le problème trouvé : une question acceptait une catégorie absente
  - [x] Valider la suite de tests avant de passer à la suite (23 tests passés)
- [x] Connexion Python vers MySQL
  - [x] Ajouter un connecteur configurable par variables d'environnement, sans identifiants en dur
  - [x] Charger les paramètres depuis `.env` (ignoré par Git)
  - [x] Vérifier le chargement de `.env` sans afficher les identifiants
  - [x] Tester la configuration de connexion et les règles existantes : 26 tests réussis dans `.venv`
  - [x] Vérifier une vraie connexion à `pyask_validation_20261124`
- [x] Gestion de base des utilisateurs avec MySQL
  - [x] Ajouter `UserRepository.register` et `UserRepository.authenticate`
  - [x] Vérifier inscription et connexion sur la base de validation
  - [x] Ajouter la modification du nom complet et de la bio
  - [x] Vérifier la modification du profil sur la base de validation
- [x] Enregistrer des questions et réponses dans MySQL
  - [x] Lister les catégories disponibles et enregistrer une question avec 1 à 3 tags
  - [x] Enregistrer une réponse liée à une question
  - [x] Vérifier le flux complet sur la base de validation; supprimer les données temporaires
- [x] Lire les questions et réponses depuis MySQL, avec tags et score des votes
- [x] Gérer les votes, commentaires et signalements avec MySQL
  - [x] Enregistrer/remplacer un vote et créer un commentaire
  - [x] Créer un signalement sans doublon et le traiter comme modérateur
  - [x] Vérifier le flux sur la base de validation; supprimer les données temporaires
- [x] Administration
  - [x] Permettre aux admins de consulter les utilisateurs et modifier leurs rôles
  - [x] Empêcher un admin de modifier son propre rôle
  - [x] Permettre aux admins de créer des catégories
  - [x] Vérifier les permissions côté dépôt et interface
- [ ] Interface graphique PyQt5
  - [x] Première interface : inscription/connexion, questions, réponses, votes, commentaires et signalements
  - [x] Afficher les commentaires de question sous la question et ceux d'une réponse sous cette réponse
  - [x] Vérifier la construction de la fenêtre de connexion en mode sans écran
  - [x] Vérifier la hiérarchie question/réponse/commentaire avec MySQL
  - [x] Ajouter recherche par mot-clé, filtre tag/catégorie et tris dans l'interface
  - [x] Ajouter l'écran de modération des signalements pour les modérateurs/admins
  - [x] Ajouter l'écran d'administration des rôles et catégories
  - [x] Clarifier la hiérarchie visuelle, regrouper les filtres et réduire les zones vides
  - [x] Centrer la page de connexion et séparer visuellement connexion/inscription
  - [x] Adapter la page du forum à la maquette : navigation, recherche, fil de questions et questions populaires
  - [x] Ajouter l'écran « Mon profil » pour modifier le nom complet et la bio
  - [x] Vérifier l'écran de profil, ses limites de saisie et la sauvegarde en mode offscreen
  - [x] Ajouter la déconnexion et réinitialiser les champs d'authentification
  - [x] Vérifier le retour connexion et l'émission de la demande de déconnexion
  - [x] Vérifier le rendu du forum, de l'administration et de la modération avec des données synthétiques en mode offscreen
  - [x] Vérifier le rendu connexion/inscription à taille maximale et le basculement des champs
  - [x] Vérifier la sélection des questions, le filtre par catégorie et la remise à zéro avec des données synthétiques
  - [x] Restaurer le filtre catégorie dans la barre latérale et le synchroniser avec les catégories du fil
  - [x] Reprendre la grille Social Media : profil/recherche à gauche, catégories et fil au centre, recommandations à droite
  - [x] Ouvrir réponses et commentaires dans un panneau de discussion dédié sans encombrer la colonne de recommandations
  - [x] Vérifier le nouvel agencement et ses interactions avec des données synthétiques en mode offscreen
  - [x] Utiliser l'image fournie comme fond de connexion, sans l'appliquer à la fenêtre du forum
  - [ ] Vérifier visuellement le flux complet sur le bureau
- [x] Recherche et filtres
  - [x] Recherche dans le titre/texte et filtres par tag/catégorie
  - [x] Tri par récence, nombre de réponses et score des votes
  - [x] Vérifier les filtres et tris avec MySQL
- [x] Rapports calculés et export CSV
  - [x] Générer les rapports questions/réponses à la demande
  - [x] Ajouter une section d'export CSV réservée aux admins, avec des fichiers séparés pour questions et réponses
  - [x] Vérifier le contenu CSV et les statistiques sur la base de validation
- [x] Vues, triggers, procédures stockées (cours de base de données)
  - [x] Créer et utiliser la vue `question_statistics`
  - [x] Ajouter et vérifier les triggers de cible des signalements (INSERT/UPDATE)
  - [x] Ajouter et vérifier `get_user_for_authentication`
- [x] Diagramme de classes et diagramme de cas d'utilisation
- [x] Documenter l'installation, la structure, les fonctionnalités et les limites dans le README

---

## 5. Points ouverts

À vérifier ou à confirmer avec le prof :
- Date de rendu, format (code seul, rapport, soutenance) et barème
- Interface graphique obligatoire, ou console acceptée
- Déploiement en ligne (Render) et maquette de design : non demandés dans le sujet, à valider avant d'y passer du temps

À compléter dans l'application :
- Vérification visuelle complète de l'interface sur le bureau.

À vérifier par nous :
- Une hypothèse non testée : MySQL refuserait un `CHECK` sur une colonne qui a aussi un `ON DELETE CASCADE`. On a retiré ce `CHECK` de `comments` par précaution et on le remplace par une vérification en Python.
- Validation effectuée manuellement sur `pyask_validation_20261124` : le script a créé les 9 tables sans erreur, la suppression en chaîne a fonctionné et la transaction a été annulée. La base originale `pyask_db` n'a pas été modifiée.

---

## 6. Méthode de travail

On avance **lentement, une étape à la fois, dans l'ordre**. On écrit le code soi-même pour bien le maîtriser, on ne passe à l'étape suivante que quand la précédente est comprise.

### Étape suivante : validation visuelle et bilan final

Les admins peuvent attribuer les rôles utilisateur/modérateur/admin et créer des catégories depuis l'écran d'administration. Les permissions sont contrôlées dans l'interface et les dépôts; les catégories utilisées par des questions ne peuvent pas être supprimées. La prochaine étape est de vérifier visuellement l'interface complète puis faire le bilan du projet.

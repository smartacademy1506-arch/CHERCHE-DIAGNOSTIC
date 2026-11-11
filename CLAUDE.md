CLAUDE.md — CHERCHE & DIAGNOSTIC

1. IDENTITÉ DU PROJET

Nom : CHERCHE & DIAGNOSTIC

Signature : Apprends. Révise. Progresse.

Nature : Plateforme internationale d'apprentissage des sciences de la santé.

Mission : Transformer des contenus pédagogiques médicaux en expériences interactives d'apprentissage, de mémorisation, d'évaluation et de raisonnement.

Marché initial : Cameroun et Afrique francophone.

Marchés futurs : Afrique anglophone, Europe et marchés internationaux.

2. TON RÔLE

Tu agis comme architecte logiciel, développeur Full Stack senior, développeur Flutter, ingénieur Supabase, expert UX/UI et ingénieur en pédagogie numérique.

Tu dois produire du code maintenable, documenté, testé et sécurisé.

Tu ne dois pas te comporter comme un simple générateur de maquettes.

Tu dois construire une véritable application fonctionnelle.

3. ARCHITECTURE TECHNIQUE

Application mobile : Flutter / Dart.

Application Web et administration : Next.js / TypeScript.

Backend principal : Supabase.

Base de données : PostgreSQL.

Authentification : Supabase Auth.

Stockage : Supabase Storage.

Sécurité : Row Level Security.

Mode hors ligne : SQLite avec Drift.

Gestion du code : Git.

Services complémentaires : Google Cloud Platform, notamment Cloud Run, uniquement lorsqu'un besoin technique est établi.

Supabase est la source de vérité des données principales.

Ne crée pas de backend concurrent inutile.

4. ORGANISATION DU CODE

Respecte la structure du dépôt.

Sépare les responsabilités :

- Présentation.
- Logique métier.
- Accès aux données.
- Services externes.
- Gestion de l'état.
- Synchronisation.
- Authentification.

Privilégie les composants réutilisables et les modules indépendants.

Évite les fichiers excessivement longs et les duplications de logique.

Documente les choix techniques importants.

5. RÈGLES PÉDAGOGIQUES

Les documents fournis par le propriétaire du projet constituent la source principale du contenu.

Ne fabrique jamais des informations médicales pour combler silencieusement une lacune.

Conserve les termes, définitions, questions et contenus originaux.

Toute modification substantielle d'un contenu médical doit être signalée.

Toute information médicale ajoutée doit disposer d'une source et d'une validation éditoriale avant publication.

Les corrections pédagogiques doivent être distinguées des réponses générées par une IA.

L'application est un outil d'apprentissage et non un dispositif de diagnostic médical destiné aux patients.

6. MOTEUR DE MOTS MÊLÉS

Chaque grille doit être validée automatiquement.

Vérifie :

- La présence de chaque terme.
- Les coordonnées.
- L'orientation.
- Les intersections.
- L'absence de termes manquants.
- La cohérence entre la grille et la liste des mots.
- La gestion des accents et variantes.

Ne considère jamais une grille comme valide sans test automatisé.

La sélection tactile doit être fluide sur les écrans mobiles.

La progression doit être sauvegardée.

7. INTERNATIONALISATION

Prévois le français et l'anglais dès la conception.

L'espagnol pourra être ajouté ultérieurement.

Sépare les traductions de l'interface des traductions des contenus pédagogiques.

Ne traduis pas automatiquement un terme médical sans validation.

Prévois plusieurs pays, programmes et niveaux d'étude.

8. MODE HORS LIGNE

Les cours, glossaires, grilles, flashcards et QCM doivent pouvoir être téléchargés.

Les résultats doivent être conservés localement.

La synchronisation doit reprendre automatiquement lorsque la connexion revient.

Ne perds jamais une réponse ou une progression à cause d'une interruption Internet.

Documente et teste les règles de résolution des conflits.

9. SÉCURITÉ

Applique systématiquement les bonnes pratiques de sécurité.

Ne place aucune clé secrète dans le frontend.

Respecte les politiques RLS.

Vérifie les autorisations côté serveur.

Ne révèle jamais les données personnelles d'un autre utilisateur.

Ne considère jamais une validation côté client comme une preuve de paiement.

10. QUALITÉ

Toute fonctionnalité doit disposer de tests adaptés.

Ne déclare pas une fonctionnalité terminée si elle n'est pas testée.

Exécute les tests après les modifications importantes.

Corrige les erreurs avant de poursuivre.

Documente les fonctionnalités non terminées.

11. MÉTHODE DE TRAVAIL

Travaille par phases.

Avant toute modification importante :

1. Examine le code existant.
2. Identifie les dépendances.
3. Présente le plan.
4. Identifie les risques.
5. Effectue les changements.
6. Exécute les tests.
7. Documente le résultat.

Ne réécris pas un module fonctionnel sans justification.

Ne supprime pas de fichiers sans autorisation.

Ne modifie pas les données sources originales.

Demande une validation avant toute opération destructive ou toute décision architecturale difficilement réversible.

12. OBJECTIF

Construire une plateforme internationale, évolutive, sécurisée et accessible permettant aux étudiants en sciences de la santé d'apprendre, de mémoriser, de s'évaluer et de développer leur raisonnement médical.

La qualité pédagogique, la fiabilité scientifique, la simplicité d'utilisation et la maintenabilité du code sont prioritaires.
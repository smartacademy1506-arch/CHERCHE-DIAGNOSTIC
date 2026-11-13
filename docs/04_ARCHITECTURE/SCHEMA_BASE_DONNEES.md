# Schéma de la base de données

Référence : `supabase/migrations/` (appliquées dans l'ordre au projet Supabase `cherche-diagnostic`).

| Migration | Contenu |
|---|---|
| `…000100_schema.sql` | Tables, clés étrangères, index, contraintes |
| `…000200_security.sql` | Fonctions d'autorisation (schéma `app`), déclencheurs, politiques RLS |
| `…000300_functions.sql` | Fonctions appelées par l'application (RPC) |
| `…000400_seed_reference.sql` | Langues, devises, pays, rôles, offres, disciplines |

## Familles de tables

- **Référentiels** : `languages`, `currencies`, `countries`, `curricula`, `app_settings`.
- **Comptes** : `profiles` (1–1 avec `auth.users`), `roles`, `permissions`, `role_permissions`, `user_roles`.
- **Catalogue** : `disciplines` → `chapters` (sous-chapitres par `parent_id`) → `lessons`, `learning_objectives`,
  `medical_terms` → `glossary_entries`.
- **Mots mêlés** : `word_search_puzzles` (une par chapitre et par langue) → `puzzle_words` ; `puzzle_sessions`.
- **Évaluation** : `quiz_questions` → `quiz_options`, `quiz_answer_keys` ; `quiz_attempts` → `quiz_answers` ;
  `open_questions` → `open_question_submissions`.
- **Révision** : `flashcards` → `flashcard_states`, `flashcard_reviews`.
- **Suivi** : `user_progress`, `learning_sessions`, `bookmarks`, `notifications`.
- **Offres** : `plans`, `plan_prices`, `payments`, `subscriptions`.
- **Transverse** : `media_assets`, `content_versions`, `audit_logs`, `clinical_cases`, `clinical_case_questions`.

## Choix de conception

- **Textes traduisibles en `jsonb`** (`{"fr": …, "en": …}`) plutôt qu'une table de traduction par entité : ajouter une
  langue de contenu ne demande aucune migration, et un chapitre se charge en une requête par table.
- **Statut éditorial** sur chaque contenu (`draft`, `in_review`, `published`, `archived`).
- **Identifiants des résultats créés sur l'appareil** (`quiz_attempts.id`, `puzzle_sessions.id`…) : la synchronisation
  peut être rejouée sans doublon.
- **`chapters.content_version`** augmente à chaque modification du contenu : l'application sait quand rafraîchir sa copie locale.
- **Règles de suppression** : supprimer un compte supprime ses résultats (`cascade`) mais conserve ses paiements,
  anonymisés (`set null`) ; une discipline qui a des chapitres ne peut pas être supprimée (`restrict`).

## Qui peut lire et écrire

| Données | Visiteur | Étudiant | Équipe éditoriale | Administrateur |
|---|---|---|---|---|
| Référentiels, offres actives | lecture | lecture | lecture | écriture |
| Liste des disciplines et chapitres | lecture | lecture | écriture | écriture |
| Contenu d'un chapitre gratuit | lecture | lecture | écriture | écriture |
| Contenu d'un chapitre premium | — | lecture si abonné | écriture | écriture |
| Bonnes réponses des QCM | — | après soumission (RPC) | lecture / écriture | lecture / écriture |
| Ses propres résultats, profil, paiements | — | lecture / écriture (paiements : lecture) | idem | idem |
| Données des autres utilisateurs | — | — | — | profils, paiements, abonnements |
| Rôles | — | les siens (lecture) | — | écriture (`admin` : super administrateur seulement) |
| Journal d'audit | — | — | — | lecture |

## Fonctions (RPC)

`get_pricing`, `create_payment_intent`, `admin_confirm_payment`, `admin_grant_subscription`, `submit_quiz_attempt`,
`get_offline_keys`, `my_access`, `admin_list_users`, `admin_set_role`, `admin_stats`, `admin_import_chapter`,
`export_my_data`, `delete_my_account`.

L'analyseur de sécurité de Supabase signale ces fonctions comme « SECURITY DEFINER appelables » : c'est voulu, chacune
contrôle elle-même l'appelant. Il ne signale aucune table sans RLS.

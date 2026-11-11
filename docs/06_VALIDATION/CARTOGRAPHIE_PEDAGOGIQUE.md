# Cartographie pédagogique

## Des documents aux modules de l'application

| Élément d'un chapitre (gabarit des livres) | Fichier d'import (`content/SPEC.md`) | Tables | Écran |
|---|---|---|---|
| Titre, introduction | `title`, `description` | `chapters` | Liste des chapitres, sommaire du chapitre |
| Objectifs | `objectives` | `learning_objectives` | Sommaire du chapitre |
| Résumé théorique | `summary`, `key_points`, `references` | `lessons` | Cours |
| Liste de mots | `terms[].fr / .en` | `medical_terms` | Mots mêlés, glossaire, flashcards |
| Glossaire | `terms[].definition` | `glossary_entries` | Glossaire ; définition affichée quand un mot est trouvé |
| Grille | générée et vérifiée à l'import | `word_search_puzzles`, `puzzle_words` | Mots mêlés |
| Flashcards | dérivées des termes | `flashcards`, `flashcard_states`, `flashcard_reviews` | Flashcards, révisions du jour |
| Vignettes et QCM | `quiz` | `quiz_questions`, `quiz_options`, `quiz_answer_keys` | QCM et correction |
| Questions d'évaluation | `open_questions` | `open_questions`, `open_question_submissions` | Questions ouvertes, auto-évaluation |
| Fiche d'évaluation | calculée | `quiz_attempts`, `puzzle_sessions`, `user_progress`, `learning_sessions` | Tableau de bord, Progrès |
| Planche illustrée | non importée | `media_assets` (prête) | à faire |
| Cas cliniques | non importés | `clinical_cases`, `clinical_case_questions` (prêtes) | à faire, après validation |

## Structure publiée dans le MVP

- **Physiologie** (4 chapitres, statut `in_review`)
  1. Physiologie cellulaire et membranaire — gratuit
  2. Physiologie cardiovasculaire — premium
  3. Physiologie respiratoire — premium
  4. Physiologie rénale — premium
- Anatomie, Histologie et embryologie, Biochimie, Biologie cellulaire, Microbiologie, Parasitologie, Immunologie,
  Pharmacologie, Sémiologie médicale, Médecine interne, Chirurgie, Gynécologie-obstétrique, Pédiatrie, Santé publique :
  disciplines créées, sans chapitre.

## Circuit éditorial

`draft` → `in_review` → `published` → `archived`

- L'import place toujours le contenu en `in_review`.
- Tant que le réglage `show_in_review_content` est actif (mode pilote), le contenu `in_review` est visible avec le bandeau
  « Contenu en cours de validation pédagogique ». Le désactiver ne laisse visible que le contenu `published`.
- Seuls un responsable pédagogique ou un administrateur peuvent publier.
- Chaque modification d'un contenu conserve la version précédente (`content_versions`).

## Indicateur de maîtrise d'un chapitre

Cours lu 15 % + part de la grille trouvée 25 % + meilleur QCM 40 % + cartes apprises 20 %. C'est un repère de révision,
pas une évaluation de compétence clinique. En dessous de 70 %, l'application propose l'étape suivante : relire le cours,
refaire la grille, réviser les cartes, puis refaire un QCM.

# Spécification du contenu pédagogique (format d'import)

Un fichier JSON par chapitre : `content/<discipline>/<NN>-<slug>.json`.
Chaque texte est bilingue : `{ "fr": "...", "en": "..." }`.
Tout contenu importé entre en base avec le statut éditorial `in_review`
(à valider par un responsable pédagogique avant le statut `published`).

```jsonc
{
  "slug": "physiologie-cardiovasculaire",      // kebab-case, ASCII
  "order": 2,
  "title": { "fr": "", "en": "" },
  "description": { "fr": "", "en": "" },        // 1 à 2 phrases
  "objectives": [ { "fr": "", "en": "" } ],     // exactement 5
  "summary": { "fr": "", "en": "" },            // 350 à 500 mots par langue, Markdown simple :
                                                 // titres "## ", paragraphes, listes "- ", **gras**
  "key_points": [ { "fr": "", "en": "" } ],     // exactement 6
  "terms": [                                     // exactement 40
    {
      "fr": "DÉBIT CARDIAQUE",                   // terme tel qu'affiché (MAJUSCULES, accents conservés)
      "en": "CARDIAC OUTPUT",
      "definition": { "fr": "", "en": "" }      // 1 à 2 phrases, 15 à 45 mots, exacte et actuelle
    }
  ],
  "quiz": [                                      // exactement 12 (au moins 3 de type "multiple", au moins 4 vignettes cliniques)
    {
      "type": "single",                          // "single" = 1 seule bonne réponse ; "multiple" = 2 ou 3 bonnes réponses
      "difficulty": 2,                           // 1 facile, 2 moyen, 3 difficile
      "stem": { "fr": "", "en": "" },
      "options": [ { "fr": "", "en": "", "correct": false } ],   // 4 ou 5 options
      "explanation": { "fr": "", "en": "" }     // pourquoi la bonne réponse est juste, 2 à 4 phrases
    }
  ],
  "open_questions": [                            // exactement 5
    { "question": { "fr": "", "en": "" }, "model_answer": { "fr": "", "en": "" } }   // éléments de réponse attendus, 40 à 90 mots
  ],
  "references": [ { "citation": "", "url": "" } ]   // 3 à 6 sources réellement consultées ou ouvrages de référence ; url facultative ("" si aucune)
}
```

## Règles sur les termes (contraintes du moteur de mots mêlés)

La « forme grille » d'un terme = majuscules, accents retirés (É→E, Ç→C, Œ→OE, Æ→AE),
espaces, traits d'union et apostrophes retirés. Exemple : « DÉBIT CARDIAQUE » → `DEBITCARDIAQUE`.

Pour CHAQUE langue séparément, dans un même chapitre :

1. Forme grille de 4 à 14 lettres, lettres A–Z uniquement (pas de chiffres, pas de symboles).
2. Aucun doublon, et aucune forme grille contenue dans une autre (ex. `SODIUM` et `HYPERSODIUM` interdits ensemble).
3. Aucune forme grille palindrome.
4. Préférer les termes d'un seul mot ; deux mots courts acceptés si la forme grille reste ≤ 14 lettres.
5. Le terme anglais est l'équivalent médical consacré du terme français (pas une traduction mot à mot).
6. Terminologie actuelle ; pas d'éponymes désuets ni de termes abandonnés.

## Règles de fond

- Contenu factuel, fondé sur les ouvrages de référence (Guyton & Hall, Boron & Boulpaep, Costanzo,
  Ganong, Sherwood, Marieb, OpenStax Anatomy & Physiology 2e) et vérifié sur des sources en ligne fiables
  (OpenStax, NCBI Bookshelf/StatPearls, sociétés savantes).
- Texte original : ne recopier aucun passage d'un ouvrage ou d'un site.
- Valeurs chiffrées avec unités SI (et unités usuelles entre parenthèses si utile).
- Les vignettes cliniques sont de type USMLE, avec un contexte clinique plausible ; quelques-unes en contexte africain.
- Une seule réponse défendable pour les questions "single" ; pas de « toutes les réponses » ni « aucune réponse ».
- Le français et l'anglais doivent dire la même chose.

## Validation obligatoire

```
node tools/validate-content.mjs content/<discipline>/<fichier>.json
```
Le fichier n'est accepté que si la commande affiche `OK`.

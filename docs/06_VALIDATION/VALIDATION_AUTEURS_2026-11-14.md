# Validation des définitions par les auteurs — 14 novembre 2026

## Origine

À l'import des livres, 138 mots des grilles posaient problème : 38 n'avaient pas de définition (le livre ne
reliait le mot à aucune entrée de son glossaire) et 100 avaient été reliés automatiquement à une entrée de façon
approximative. Une recherche documentaire (IA, sources : Académie nationale de médecine, HAS, EMA, SFAR, OMS,
Manuel MSD, Terminologia Anatomica, revues indexées) a proposé pour chaque mot une entrée, une définition et un
verdict. Les auteurs ont lu et approuvé ce rapport le 14 novembre 2026 (message du propriétaire du projet).

Le fichier appliqué est chiffré : `supabase/seed/books/corrections-2026-11-14.asc` ; le script est
`supabase/seed/books/apply_corrections.sql`. Les textes des définitions ne figurent pas ici en clair.

## Ce qui a été appliqué

### 38 mots sans définition : rattachement à l'entrée du glossaire

Pour chaque mot, la recherche a désigné une entrée du glossaire du même chapitre. Toutes ces entrées ont une
définition dans le livre : c'est elle qui est affichée, sans reformulation (règle « conserver les définitions
originales »). Les reformulations proposées par la recherche n'ont donc pas servi.

| Livre | Mots |
|---|---|
| Anatomie — Vascularisation | NASAL, CARDIAQUE, NODALE, NITRIQUE |
| Anatomie — Organes | STRESS, FOLATE, NIGRA |
| Pharmacologie | FOIE, MOELLE, NEZ, TOF, NUIT, RYTHME, CALME, PSG, LATENCE, MAINTIEN, SPORT, CHAUD, HOPITAL, SOLEIL, SUCRE, PROPHYLAXIE, SCP, IRA, MRC, AIGU, GENCIVE, PILOSITE, POLYPILULE, ACHILLE, GRAS, TENDON, VIANDE, DENTISTE, VUE, ANUS, ECOLE |

Ces 38 mots ont aussi reçu leur fiche de révision, qui avait été retirée faute de définition.

### 100 rattachements approximatifs : 89 corrects, 11 définitions corrigées

Aucun rattachement n'a été changé. Onze définitions du livre ont été remplacées par la version corrigée approuvée ;
la définition d'origine reste dans `public.content_versions`.

| N° | Mot | Entrée | Ce qui a été corrigé | Sources principales |
|---|---|---|---|---|
| 43 | OESOPHAGE | Varices œsophagiennes | La définition décrivait l'anastomose, pas les varices ni l'hypertension portale | Manuel MSD |
| 46 | RETINIENNE | Artère centrale de la rétine | Présentée comme branche terminale de l'ophtalmique : c'est une collatérale | Académie de médecine ; Terminologia Anatomica |
| 54 | HOMME | Sexe masculin | Le ratio fixe « 4 à 6 fois » remplacé par la fourchette des sources | Manuel MSD ; HAS |
| 55 | BILE | Voies biliaires | « Uniquement par l'artère hépatique » trop absolu ; le point clé est l'absence d'apport portal | Manuel MSD |
| 79 | NEPHROTOXIQUE | Néphrotoxicité | Une liste de médicaments sans définition du terme | Académie de médecine |
| 86 | SPINALE | Rachianesthésie | Technique de référence de la césarienne **programmée** seulement | SFAR 2007 |
| 93 | MOIS | Injection mensuelle | Palipéridone : forme semestrielle (Byannli) ajoutée | EMA (RCP) ; HAS |
| 112 | ABANDON | Perdu de vue | Critère OMS ajouté : interruption d'au moins 2 mois consécutifs | OMS 2013 (rév. 2020) |
| 124 | AMARILE | Fièvre jaune | « Obligatoire » précisé : PEV à 9 mois au Cameroun, certificat exigé dès 1 an | OMS ; Wiysonge 2008 ; Institut Pasteur |
| 125 | ANKYLOSTOME | Ankylostomose | La définition décrivait le ver, pas la maladie | OMS |
| 136 | KERNICTERE | Ictère nucléaire | Prévention complétée : surveillance, photothérapie intensive, exsanguinotransfusion | Revue du Praticien ; CNRHP |

Chaque définition corrigée porte dans `glossary_entries.source_refs` la citation du livre, ses sources (avec lien)
et la mention de validation ; `last_verified_at` vaut 2026-11-14.

## Ce qui n'a pas été appliqué

- Précisions facultatives du rapport, sans changement de verdict : n° 85 (objectif FeO₂ > 90 % de la
  préoxygénation), n° 135 (convulsion fébrile simple : moins de 15 minutes), n° 138 (sensibilité faible du TUG).
- Sources marquées « à confirmer » dans le rapport : elles sont citées, mais leur lien précis reste à vérifier
  avant toute mise en avant des sources dans l'application.

## Contrôle

Après application, aucun mot des grilles n'est sans définition, chaque mot a une fiche de révision, et la
version des chapitres concernés a été incrémentée pour les appareils hors ligne (migration
`20261114000100_glossary_versioning.sql`).

# Audit documentaire et technique — 11 novembre 2026

## 1. Ce qui a été trouvé

| Élément | État constaté |
|---|---|
| Dépôt GitHub `CHERCHE-DIAGNOSTIC` | Un seul fichier, `README.md` (2 lignes). Aucun code, aucun document pédagogique. |
| Projet Claude « CHERCHE & DIAGNOSTIC » | Un document : `gabarit-go-dr-katoume.md` (gabarit des volumes de gynécologie-obstétrique et structure d'un chapitre). |
| Livres de la collection (Physiologie générale, Anatomie, Sémiologie gynécologique, Sénologie, Chirurgie gynécologique…) | **Non disponibles dans cet environnement.** Les PDF sont sur l'ordinateur de l'auteur (`C:\Users\USER\Desktop\katoume_cherche\…`). Aucun n'a pu être ouvert ni analysé. |
| Supabase | Un projet sans rapport (`onlineprep-test`). Projet `cherche-diagnostic` créé pour l'occasion (région Paris). |
| Vercel | Un projet sans rapport (`onlineprep`). Intégration GitHub de Vercel non installée sur ce dépôt. |
| Hostinger | Connecteur reconnecté en cours de session ; non utilisé (voir Architecture). |
| Outils de l'environnement de travail | Node 22, TypeScript, esbuild, React 19, Playwright + Chromium. **Flutter, Next.js et le client Supabase ne sont pas installés et l'installation de paquets est désactivée.** |

## 2. Conséquence sur le contenu

Les prompts demandent d'exploiter les documents existants et de ne rien inventer. Les documents n'étant pas
accessibles, et la consigne du 11/11 autorisant des agents de recherche, le contenu du MVP a été **rédigé à neuf**
à partir d'ouvrages de référence et de sources en ligne vérifiées, puis importé avec le statut `in_review`.
**Ce contenu n'est pas celui des livres** et n'a pas été validé par un enseignant.

| Chapitre (Physiologie) | Termes | Définitions | QCM | Questions ouvertes | Grilles (fr / en) | Illustrations |
|---|---|---|---|---|---|---|
| 1. Physiologie cellulaire et membranaire | 40 | 40 | 12 | 5 | 22×22 / 22×22 | 0 |
| 2. Physiologie cardiovasculaire | 40 | 40 | 12 | 5 | 23×23 / 22×22 | 0 |
| 3. Physiologie respiratoire | 40 | 40 | 12 | 5 | 23×23 / 23×23 | 0 |
| 4. Physiologie rénale | 40 | 40 | 12 | 5 | 23×23 / 23×23 | 0 |

Toutes les données sont bilingues (français et anglais). Les 14 autres disciplines du catalogue sont créées mais vides
(affichées « Bientôt disponible »).

## 3. Écarts avec le gabarit des livres

- Les livres comptent 60 mots par grille 20×20 ; le MVP en compte 40 (le moteur accepte jusqu'à 70).
- Vignettes de type USMLE : présentes sous forme de QCM (au moins 4 par chapitre), pas comme rubrique séparée.
- Pas de planche d'ouverture, de drapeaux rouges, de pièges ni d'illustrations.
- Cas cliniques : tables prêtes, module non activé (validation scientifique préalable exigée).

## 4. Problèmes et points à faire relire

- Les numéros de chapitres des ouvrages cités (Guyton, Boron, Costanzo, West) ont été donnés de mémoire par les agents : à vérifier ou retirer.
- Valeurs qui varient selon les ouvrages (K⁺ intracellulaire 140 ou 150 mmol/L, seuil d'hyperkaliémie 5 ou 5,5 mmol/L, part du CO₂ transportée en bicarbonate 70 ou 90 %, pression intrapleurale).
- Chapitres 2 et 4 : l'agent rédacteur s'est interrompu avant sa relecture finale ; une relecture indépendante a été lancée (résultat dans le compte rendu de session).
- Grilles de 22 à 23 cases de côté : lisibles sur ordinateur et tablette, serrées sur un téléphone de 360 px (mode « agrandir » fourni). Décision à prendre : garder une grille par chapitre ou la scinder en deux sur mobile.
- Doublons : aucun terme en double dans un même chapitre (contrôle automatique) ; quelques termes reviennent d'un chapitre à l'autre (RÉNINE, ALDOSTÉRONE, COMPLIANCE), ce qui est attendu.

## 5. Recommandations

1. Fournir les fichiers sources des livres (Word ou données, pas seulement PDF) pour remplacer le contenu provisoire par le contenu d'auteur.
2. Désigner un responsable pédagogique qui valide chaque chapitre avant passage au statut `published`.
3. Décider du prestataire de paiement (voir Architecture) avant d'ouvrir les abonnements.

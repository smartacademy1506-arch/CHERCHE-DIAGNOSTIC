# Revues indépendantes — 11 novembre 2026

Deux relectures ont été faites par des agents distincts de ceux qui ont écrit le code et le contenu.

## 1. Relecture médicale (chapitres 2 et 4)

Les chapitres 1 et 3 ont été relus par leur rédacteur ; les chapitres 2 et 4 l'ont été par un relecteur indépendant,
leur rédacteur s'étant interrompu.

| Chapitre | Correction | Source |
|---|---|---|
| 2. Cardiovasculaire | Volume télédiastolique « 120 à 130 mL » → « 120 mL » (130 mL et 70 mL éjectés donnaient une fraction d'éjection de 54 %, contraire au « au moins 55 % » de la même phrase) | OpenStax A&P 2e, 19.4 |
| 4. Rénal | Référence StatPearls « Anion Gap » : noms d'auteurs non vérifiables retirés | StatPearls |

Aucune erreur trouvée dans les 80 définitions, les 24 QCM (bonne réponse unique, explications) ni dans la cohérence
français/anglais de ces deux chapitres.

### À trancher par un enseignant (les 4 chapitres)

- Forces de Starling : modèle classique (réabsorption veineuse) ; le modèle révisé (glycocalyx) n'est pas mentionné.
- QCM « syndrome néphrotique » : la baisse de la pression oncotique est attendue ; la théorie « overfill » est discutée.
- Limites : QRS < 120 ms (certains ouvrages : 100 ms) ; autorégulation rénale 80–180 mmHg ; hyperkaliémie > 5,0 ou > 5,5 mmol/L ;
  K⁺ intracellulaire 140 ou 150 mmol/L ; part du CO₂ en bicarbonate 70 ou 90 % ; pression intrapleurale.
- Terme anglais « PARATHORMONE » : l'usage anglais est « parathyroid hormone (PTH) », trop long pour la grille.
- Orthographe anglaise mélangée (britannique dans les textes, américaine dans certains termes) : choisir une convention.
- QCM « surdosage en tramadol » (chap. 3) : myosis moins constant qu'avec la morphine.
- Numéros de chapitres des ouvrages de référence cités de mémoire dans les chapitres 1 et 3 : à vérifier ou retirer.

## 2. Revue de sécurité (base de données et application)

Aucune faille critique : aucun chemin trouvé permettant à un visiteur ou à un étudiant de lire les données d'un autre,
de s'attribuer un rôle, d'activer un abonnement, de confirmer un paiement ou de modifier les prix.

| Constat | Gravité | État |
|---|---|---|
| E1. La suppression de son propre compte échouait (garde des rôles, journal d'audit) | Élevé | Corrigé dans `…000500_security_fixes.sql` — **à appliquer** |
| M1. Une nouvelle demande de paiement annulait une demande peut-être déjà réglée | Moyen | Corrigé (même migration) — **à appliquer** |
| M2. Les corrigés d'un chapitre **gratuit** sont renvoyés après soumission, y compris sans compte | Moyen | Accepté : c'est la correction attendue en mode entraînement. À revoir si un mode examen noté est ouvert. |
| M3. Objectifs et cas cliniques d'un chapitre payant lisibles sans abonnement | Moyen | Corrigé (même migration) — **à appliquer** |
| M4. Un contributeur pouvait remplacer un chapitre, changer l'accès gratuit/payant ou modifier un contenu publié | Moyen | Corrigé (même migration) — **à appliquer** |
| M5. Amorçage du super administrateur dépendant de la confirmation d'e-mail | Moyen | À vérifier : la confirmation d'e-mail doit rester active dans Supabase Auth ; vider `app.bootstrap_admins` après la première connexion |
| M6. Un résultat de QCM pouvait être perdu si la session expirait pendant la synchronisation | Moyen | Corrigé (`store.ts`) |
| F1. CSP trop large (`*.supabase.co`) | Faible | Corrigé (`vercel.json`) |
| F2. Jeton laissé dans l'historique après un lien de connexion | Faible | Corrigé (`supabase.ts`) |
| F3. Chapitres payants et corrigés conservés sur l'appareil après déconnexion | Faible | Corrigé (purge à la déconnexion) |
| F4. `consent_at`, `created_at` et le texte des notifications modifiables par leur propriétaire | Faible | Corrigé (droits par colonne) — **à appliquer** |
| F6. Demandes de paiement illimitées, référence courte | Faible | Corrigé (5 en attente maximum, référence de 40 bits) — **à appliquer** |
| F7. Normalisation des accents plus stricte en SQL que dans l'application | Faible | Ouvert (échec sans risque à l'import d'un terme hors alphabet latin courant) |
| F8. Mode pilote actif par défaut | Faible | Voulu pour la phase de validation ; **à désactiver avant l'ouverture au public** |
| F9. Résultats déclarés par l'appareil (grilles, durées) | Faible | Accepté tant qu'il n'y a ni classement ni certificat |
| F10. Export des données personnelles incomplet | Faible | Corrigé (même migration) — **à appliquer** |
| F11. Un lien de référence mal formé faisait planter l'écran du cours | Faible | Corrigé (`Chapter.tsx`) |
| F12. Privilèges par défaut des futures tables | Faible | Règle : toute nouvelle table doit activer le RLS dans sa migration |

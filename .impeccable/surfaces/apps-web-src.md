---
version: 1
slug: "apps-web-src"
primary_target: "apps/web/src"
related_targets: []
---

# Application CHERCHE & DIAGNOSTIC (apps/web)

Scope : toute l'application (shell, catalogue, chapitre, mots mêlés, QCM, flashcards, progrès, offres, administration).
Visitor mode : Operate (la page Offres reste un écran de l'app, au ton plus persuasif).
Audience : étudiants en santé, surtout sur téléphone Android d'entrée de gamme, réseau lent ou coupé.
Job : résoudre la grille du chapitre, relier chaque mot à sa définition, réviser chaque jour.
Contraintes : logo fourni (loupe-C, croix, livre) et ses couleurs marine #003562, rouge #CD1A1C, ciel #30A8E0 ; blanc pour lire ; contenu d'auteur restitué tel quel ; hors ligne.

## Direction contract

THESIS: L'application applique le design system « Cherche & Diagnostic » du propriétaire (artefact claude.ai c8bd9b69, tokens.json v1) : application de jeux pour apprendre la médecine, marine pour l'interface, ciel pour mettre en avant, rouge pour le geste médical. Ce brief remplace la direction « page de jeux au stylo rouge » (12–13/11/2026).

OWN-WORLD: Tokens sémantiques du design system (fond, surface, surface-2, bordure, texte, primaire, accent, diagnostic, succes, danger, alerte, focus, surlignage-*), thèmes clair et sombre ; Poppins 400/500/700 seule ; pas de 4 px ; cartes en surface avec filet et ombre-1 ; rayons 6/10/16/24/pastille ; aplats, aucun dégradé.

STORY: L'étudiant ouvre l'app, retrouve la grille du chapitre, surligne les mots, lit leur définition, puis passe au cours, aux vignettes et aux cartes ; il revient le lendemain.

FIRST VIEWPORT: Écran grille sur téléphone : titre du chapitre, compteur et chronomètre, définition dans une zone fixe, grille 20 × 20 en carte arrondie avec les mots trouvés surlignés en pastilles (ciel, rouge, ambre, marine), liste des mots à puces colorées, un seul bouton « Diagnostic » rouge pour terminer.

FORM: design system fourni par le propriétaire ; voir DESIGN.md.

FINISH: tests de bout en bout clair et sombre, captures relues, DESIGN.md à jour.

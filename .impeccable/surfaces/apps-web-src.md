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

THESIS: L'application est la page de jeux qu'on résout au stylo rouge : une grille nette sur papier blanc, des listes de mots en colonnes, et le geste d'entourer. Elle refuse le tableau de bord ludique à cartes arrondies et badges de la catégorie.

OWN-WORLD: Papier blanc sur fond gris-bleu pâle, encre marine #003562, manchette blanche portant le logo au-dessus d'un double filet marine, stylo rouge #CD1A1C réservé aux mots entourés, aux corrections et aux alertes, bleu ciel #30A8E0 pour la sélection en cours, filets fins à l'encre diluée au lieu de cartes, titres en Poppins grasse (le lettrage du logo), texte courant en police système, chiffres tabulaires, listes numérotées en colonnes.

STORY: L'étudiant ouvre l'app, voit la grille du jour et ce qu'il doit revoir ; il entoure les mots, lit la définition qui apparaît, puis passe au cours, aux vignettes et aux cartes ; il revient le lendemain.

FIRST VIEWPORT: Écran grille sur téléphone : en-tête blanc sous filet marine avec le numéro et le titre du chapitre, le compteur 12/60 et le chronomètre ; la grille occupe toute la largeur dans un cadre d'encre épais ; les mots trouvés sont entourés d'un trait rouge ; sous la grille, la liste numérotée en trois colonnes, mots barrés au stylo ; la définition du dernier mot glisse en bas comme une coupure de journal. L'action principale est la grille elle-même.

FORM: page de jeux du journal, position 7 sur ma liste ordonnée ; seed:23bb425c6efcae90. Signature : le trait de stylo rouge qui entoure chaque mot trouvé et le tampon « RÉSOLU » en fin de grille.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

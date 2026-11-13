---
name: CHERCHE & DIAGNOSTIC
description: "Apprends. Révise. Progresse. — la page de jeux médicale résolue au stylo rouge"
colors:
  ink: "#0e2238"
  ink-2: "#4a5c70"
  navy: "#003562"
  navy-deep: "#00213f"
  navy-tint: "#e8eef5"
  paper: "#ffffff"
  ground: "#f1f4f8"
  rule: "#d5dde7"
  rule-field: "#c3cfdc"
  rule-mid: "#9fb0c3"
  pen: "#cd1a1c"
  pen-deep: "#9e1416"
  pen-wash: "#fbeaea"
  pen-rule: "#efb3b3"
  pen-on-navy: "#ff8a8b"
  sky: "#30a8e0"
  sky-ink: "#0b5f86"
  sky-wash: "#e3f3fb"
  ok: "#17734a"
  ok-wash: "#e5f3ec"
  ok-rule: "#a9d6bf"
  warn: "#8a5a00"
  warn-wash: "#fdf2dc"
  warn-rule: "#ecd193"
typography:
  display:
    fontFamily: "Poppins, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "clamp(1.45rem, 4.6vw, 2rem)"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.01em"
  headline:
    fontFamily: "Poppins, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.01em"
  figure:
    fontFamily: "Poppins, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "2.1rem"
    fontWeight: 700
    lineHeight: 1.05
    fontFeature: "tnum"
  grid-letter:
    fontFamily: "Poppins, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "clamp(10px, calc(78vw / var(--n, 20)), 21px)"
    fontWeight: 500
    lineHeight: 1
  title:
    fontFamily: "Poppins, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 500
    lineHeight: 1.3
  body:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', 'Noto Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "lnum"
  prose:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', 'Noto Sans', 'PingFang SC', 'Microsoft YaHei', sans-serif"
    fontSize: "1.04rem"
    fontWeight: 400
    lineHeight: 1.72
  label:
    fontFamily: "system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', 'Noto Sans', sans-serif"
    fontSize: "0.72rem"
    fontWeight: 600
    letterSpacing: "0.02em"
rounded:
  hairline: "3px"
  r: "6px"
spacing:
  space: "clamp(1rem, 3.5vw, 1.5rem)"
  stack: "0.75rem"
  section: "1.5rem"
  touch: "44px"
  control: "46px"
components:
  button-primary:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.paper}"
    typography: "{typography.title}"
    rounded: "{rounded.r}"
    padding: "0.6rem 1.15rem"
    height: "46px"
  button-primary-hover:
    backgroundColor: "{colors.navy-deep}"
    textColor: "{colors.paper}"
  button-soft:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.navy}"
    rounded: "{rounded.r}"
    padding: "0.6rem 1.15rem"
    height: "46px"
  button-soft-hover:
    backgroundColor: "{colors.navy-tint}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.navy}"
    rounded: "{rounded.r}"
    padding: "0.6rem 1.15rem"
  button-danger:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.pen}"
    rounded: "{rounded.r}"
    padding: "0.6rem 1.15rem"
  input:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.r}"
    padding: "0.55rem 0.75rem"
    height: "46px"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.r}"
    padding: "0.3rem 0.7rem"
    height: "36px"
  chip-on:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.paper}"
  tag:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    rounded: "{rounded.hairline}"
    padding: "0.12rem 0.5rem"
  nav-item-active:
    backgroundColor: "{colors.navy-tint}"
    textColor: "{colors.navy}"
    rounded: "{rounded.r}"
  ws-sheet:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.grid-letter}"
    rounded: "{rounded.hairline}"
    padding: "11px"
  plan-featured:
    backgroundColor: "{colors.navy}"
    textColor: "{colors.paper}"
    padding: "1.4rem 1.2rem"
  notice-error:
    backgroundColor: "{colors.pen-wash}"
    textColor: "{colors.pen-deep}"
    rounded: "{rounded.r}"
    padding: "0.8rem 1rem"
---

# Design System: CHERCHE & DIAGNOSTIC

## Overview

**Creative North Star: "La page de jeux résolue au stylo"**

L'application est la page de jeux du journal qu'un étudiant résout au stylo rouge : une grille nette sur papier blanc, des listes de mots numérotées en colonnes séparées par des filets, et un seul geste qui compte, entourer. Tout le reste de l'interface (cours, glossaire, QCM, flashcards, progrès, offres) est composé avec le même matériel : papier blanc posé sur un fond gris-bleu pâle, encre marine, filets d'imprimerie, chiffres alignés. Elle refuse le tableau de bord ludique à cartes arrondies, badges et anneaux de la catégorie.

La densité est celle d'un imprimé lu sur un petit écran Android : des corps lisibles, des zones tactiles de 44 px au moins, peu de couleur. Trois couleurs viennent du logo et chacune a un rôle unique : la marine écrit et guide, le rouge entoure et corrige, le bleu ciel montre ce qu'on est en train de sélectionner. La profondeur ne vient presque jamais de l'ombre ; elle vient des filets, du double filet de la manchette et du cadre d'encre de la grille.

Le mouvement est celui du stylo : le trait qui s'enroule autour d'un mot trouvé, le tampon « RÉSOLU » qui tombe en fin de grille, la coupure de définition qui glisse. Tout s'arrête si l'utilisateur demande moins d'animation.

**Key Characteristics:**
- Papier blanc sur fond gris-bleu pâle, encre marine, aucun dégradé.
- Filets fins et doubles filets à la place des cartes et des ombres.
- Rouge stylo réservé aux mots entourés, aux corrections et aux alertes.
- Bleu ciel réservé à la sélection en cours.
- Poppins grasse pour les titres et les chiffres, police système pour lire.
- Chiffres tabulaires partout où un nombre change ou s'aligne.

### Provenance des images et des polices

- **Logo et icônes** : les PNG de `apps/web/public/brand/` (logo horizontal, logo seul, favicon, icônes PWA 192, 512 et masquable, icône Apple) dérivent du logo fourni par le propriétaire le 12/11/2026, dont les originaux sont conservés dans `assets/brand/*-source.png`. Ils sont détourés et redimensionnés par `tools/brand/build_assets.py`, et employés tels quels, sans être redessinés ni recolorés.
- **Poppins** (500 et 700) : police sous licence SIL Open Font License, auto-hébergée en sous-ensembles WOFF (`apps/web/public/fonts/`) générés par le même script (crénage, ligatures, chiffres tabulaires et alignés conservés).
- Aucune autre image matricielle n'est livrée. Les icônes d'interface sont des tracés SVG à trait de 1,8 dessinés dans le code ; le trait de stylo, la sélection et l'entourage des économies sont aussi des SVG.

## Colors

Une palette d'imprimé à trois encres tirées du logo, sur papier blanc ; chaque encre a un rôle et un seul.

### Primary
- **Marine du logo** (navy) : l'encre de la structure. Titres, filets forts, double filet de la manchette, cadre de la grille, boutons principaux, onglet et rubrique de navigation actifs, barre de progression, marqueurs de liste, lettres des mots trouvés. Sa version profonde (navy-deep) sert au survol des boutons, au toast et aux lettres en cours de sélection ; sa teinte (navy-tint) aux fonds d'état actif et à l'encadré des points clés.

### Secondary
- **Rouge stylo** (pen) : le trait qui entoure chaque mot trouvé (capsule SVG, remplissage à 6 % d'opacité), le trait qui barre le mot dans la liste, le tampon « RÉSOLU », le filet supérieur de la coupure de définition, le chronomètre en retard, la réponse fausse d'un QCM, le titre de la réponse modèle, le bouton de suppression, l'encadré des alertes cliniques et l'entourage de l'économie sur la page des offres. Son texte foncé (pen-deep) porte les messages d'erreur et le bandeau hors ligne sur le lavis rouge (pen-wash). Sur fond marine, il devient pen-on-navy, plus clair, pour garder le contraste.

### Tertiary
- **Bleu ciel du logo** (sky) : la sélection en cours. La capsule bleue qui suit le doigt sur la grille (22 % d'opacité), l'anneau de focus clavier, le surlignage de texte (sky-wash). Il n'est jamais employé comme texte sur blanc ; quand il doit être lu, il passe à sky-ink (5,9:1), qui affiche les lettres sélectionnées en direct au-dessus de la grille.

### Neutral
- **Encre** (ink, 15:1 sur blanc) : texte courant et lettres de la grille.
- **Encre diluée** (ink-2, 6,6:1) : texte secondaire, libellés, numéros de liste, mots déjà barrés.
- **Papier** (paper) : surfaces de lecture, manchette, navigation, grille, offres.
- **Fond** (ground) : le fond gris-bleu pâle sur lequel le papier est posé.
- **Filet** (rule) : filets fins, séparateurs de liste et de colonnes. rule-field borde les champs de saisie ; rule-mid sert aux cases à cocher, au survol des options et à l'ascenseur.
- **États** : ok et ok-wash pour la bonne réponse et l'offre gratuite ; warn et warn-wash pour les pièges et le contenu en cours de validation. Leurs bordures pâles (ok-rule, warn-rule, pen-rule) dessinent les encadrés.

### Named Rules
**La règle des trois encres.** La marine écrit, le rouge entoure, le bleu ciel sélectionne. Une encre n'emprunte jamais le rôle d'une autre.

**La règle du stylo rouge.** Le rouge n'apparaît que sur un mot trouvé, une correction ou une alerte. Si un élément rouge n'est ni entouré, ni corrigé, ni dangereux, il est en trop.

**La règle du ciel fugace.** Le bleu ciel montre ce qui est en cours et disparaît dès que le geste se termine : la capsule de sélection devient un trait rouge ou s'efface.

## Typography

**Display Font:** Poppins 500 et 700, auto-hébergée (repli : system-ui, -apple-system, Segoe UI, Roboto)
**Body Font:** police système (system-ui, -apple-system, Segoe UI, Roboto, Helvetica Neue, Noto Sans, PingFang SC, Microsoft YaHei)

**Character:** Poppins grasse reprend le lettrage géométrique du logo et porte tout ce qui se lit d'un coup d'œil (titres, lettres de la grille, chiffres, boutons) ; la police système porte tout ce qui se lit longtemps, sans téléchargement supplémentaire et dans toutes les écritures de l'interface, chinois compris.

### Hierarchy
- **Display** (Poppins 700, clamp 1,45 à 2 rem, interligne 1,15, approche -0,01 em) : titre de page, sous la manchette, équilibré sur deux lignes au plus. L'accueil monte à clamp 1,6 à 2,3 rem.
- **Headline** (Poppins 700, 1,05 rem, interligne 1,3) : titre de rubrique, toujours posé sous un filet marine de 2 px.
- **Figure** (Poppins 700, 2,1 rem, interligne 1,05, chiffres tabulaires) : prix des offres ; le score de fin de grille monte à 2,6 rem, le compteur de mots à 1,15 rem, les relevés de progrès à 1,45 rem.
- **Grid letter** (Poppins 500, proportionnelle à la taille de la grille, 10 à 21 px ; 19 px en mode loupe) : lettres de la grille ; elles passent en 700 marine quand le mot est trouvé.
- **Title** (Poppins 500, 0,95 rem) : boutons, onglets, signature de la manchette (0,78 rem).
- **Body** (système 400, 16 px, interligne 1,55, chiffres alignés) : texte courant de l'interface.
- **Prose** (système 400, 1,04 rem, interligne 1,72, 68 caractères au plus) : cours, définitions du glossaire, dos des flashcards.
- **Label** (système 600, 0,72 rem, capitales, approche 0,02 em) : étiquettes de statut (gratuit, premium, en validation) et en-têtes de tableau (0,74 rem, approche 0,05 em). Elles se placent à côté d'un élément, jamais au-dessus d'un titre.

### Named Rules
**La règle des chiffres alignés.** Tout nombre qui change ou se compare (compteur, chronomètre, score, prix, pourcentage, numéro de chapitre, numéros de la liste, tableaux) est en chiffres tabulaires.

**La règle des deux voix.** Poppins pour ce qui se repère, police système pour ce qui se lit. Aucun paragraphe en Poppins, aucun titre en police système.

## Layout

**Téléphone d'abord.** En dessous de 900 px, l'écran se lit de haut en bas : la manchette blanche (logo de 34 px à gauche, signature « Apprends. Révise. Progresse. » à droite) au-dessus d'un double filet marine de 4 px, un bandeau d'état éventuel (validation pédagogique, hors ligne), puis la page, et en bas une barre de navigation fixe à cinq rubriques (icône au-dessus du libellé, 58 px de haut, zone de sécurité respectée). La rubrique active est marine, marquée d'un trait de 3 px collé au filet supérieur.

**Ordinateur à partir de 900 px.** La manchette disparaît ; la navigation devient une colonne latérale collante de 248 px, logo en tête au-dessus du même double filet, rubriques en ligne, la rubrique active sur teinte marine. Sur l'écran de mots mêlés, la grille et la liste passent côte à côte : la grille à gauche (au plus 38 rem et toujours contenue dans la hauteur de l'écran), la liste dans une colonne collante à droite (15 rem au moins), défilable seule.

**Gabarits.** Page à 780 px au plus (1 080 px pour la grille et les écrans larges), formulaires à 460 px, marges internes fluides (space : 1 à 1,5 rem), 1,5 rem entre rubriques, 0,75 rem dans une pile. Seuils observés : 420 px (petits téléphones : grilles à deux colonnes, grille de jeu élargie jusqu'aux bords), 520 px (liste de mots en trois colonnes), 760 px (offres empilées), 900 px (passage ordinateur).

**Listes en colonnes.** La liste des mots de la grille est numérotée et coulée en colonnes séparées par un filet : deux colonnes sur téléphone, trois à partir de 520 px, deux dans la colonne latérale sur ordinateur, sous un filet marine de 2 px. Les sommaires (disciplines, chapitres) sont des lignes séparées par des filets ; les activités d'un chapitre sont un quadrillage de cases à filets fins.

### Named Rules
**La règle de la grille immobile.** La zone au-dessus de la grille a une hauteur réservée (4,9 em) : consigne, lettres sélectionnées et définition s'y succèdent sans jamais déplacer la grille sous le doigt.

## Elevation & Depth

Le système est plat. La profondeur vient des filets : filet fin pour séparer, filet marine de 2 px pour ouvrir une rubrique, double filet de 4 px pour la manchette, cadre d'encre de 3 px pour la grille. Trois ombres seulement existent, toutes diffuses, toutes teintées de marine, et chacune signale un objet posé au-dessus de la page.

### Shadow Vocabulary
- **Feuille de grille** (`box-shadow: 0 1px 0 var(--rule), 0 10px 28px -18px rgba(0, 33, 63, .45)`) : la grille posée sur la page comme une feuille ; retirée en mode loupe.
- **Coupure dépliée** (`box-shadow: 0 14px 28px -14px rgba(0, 33, 63, .45)`) : la définition dépliée qui recouvre momentanément le haut de la grille.
- **Toast** (`box-shadow: 0 6px 20px rgba(0, 33, 63, .22)`) : message bref sur fond marine profond.
- **Focus de champ** (`box-shadow: 0 0 0 3px var(--sky-wash)`) : halo bleu ciel autour d'un champ actif, avec bordure marine.

### Named Rules
**La règle du filet avant l'ombre.** Pour séparer ou hiérarchiser, on trace un filet. Une ombre n'est admise que pour un objet qui recouvre la page, et elle reste diffuse.

## Shapes

Papier coupé : angles de 6 px (r) pour les boutons, champs, options, encadrés et la navigation active ; 3 px (hairline) pour les étiquettes, la barre de progression et le cadre de la grille ; aucun angle pour les listes à filets, les cases d'activités, les relevés et les offres juxtaposées. Les seules formes arrondies sont celles du stylo : la capsule qui entoure un mot (bouts en demi-cercle, légèrement inclinée), l'ovale à main levée autour de l'économie, et le tampon à double filet incliné de -9°.

## Components

### Buttons
Sobres et nets, en lettrage Poppins.
- **Shape :** papier coupé (6 px), 46 px de haut au moins, bordure de 1,5 px.
- **Primary :** fond marine, texte blanc ; marine profond au survol ; enfoncement de 1 px à l'appui.
- **Soft :** papier, texte et bordure marine ; teinte marine au survol.
- **Ghost :** sans fond, texte marine ; teinte marine au survol (« Arrêter et voir le résultat »).
- **Danger :** papier, texte et bordure rouge stylo ; lavis rouge au survol.
- **Icône seule :** carré tactile de 44 px, marine, teinte marine au survol ou quand l'option est enclenchée (chronomètre, loupe).
- **Désactivé :** opacité 45 %.

### Chips
- **Style :** papier, filet de 1,5 px, 36 px de haut, angle de 6 px.
- **State :** sélectionnée, elle passe en fond marine et texte blanc.

### Cards / Containers
Les feuillets sont du papier posé sur le fond, sans ombre.
- **Corner Style :** 6 px ; 0 quand ils deviennent des lignes ou des cases.
- **Background :** papier ; teinte marine pour les points clés ; fond marine plein pour « Continuer mes révisions » et l'offre mise en avant.
- **Shadow Strategy :** aucune (voir Elevation & Depth).
- **Border :** filet fin ; marine au survol d'un feuillet cliquable.
- **Internal Padding :** 1 rem × 1,1 rem.
- **Sommaires :** dans une pile, les feuillets cliquables perdent leur cadre et deviennent des lignes séparées par des filets.
- **Cases d'activités :** quadrillage à filets fins, cases de 96 px de haut au moins, titre en Poppins marine.
- **Relevés :** un chiffre Poppins marine (1,45 rem) sous un filet marine de 2 px, avec son libellé dessous ; ni cadre ni fond.

### Inputs / Fields
- **Style :** papier, bordure de 1,5 px (rule-field), angle de 6 px, 46 px de haut ; libellé au-dessus en système 600, encre diluée.
- **Focus :** bordure marine et halo bleu ciel de 3 px.
- **Error :** message en encadré rouge (lavis rouge, texte pen-deep, rôle alert).

### Navigation
- **Téléphone :** barre blanche fixe en bas, filet supérieur fin, cinq rubriques (Accueil, Apprendre, Réviser, Progrès, Profil), icône SVG au-dessus d'un libellé de 0,7 rem ; la rubrique active passe en marine avec un trait de 3 px en haut.
- **Ordinateur :** colonne de 248 px, logo au-dessus du double filet, rubriques en ligne (0,95 rem) ; survol sur fond gris-bleu, rubrique active en gras sur teinte marine.
- **En-tête de page :** bouton retour de 44 px, titre en Display sur deux lignes au plus, actions à droite, le tout fermé par un filet marine de 2 px.

### Grille de mots mêlés (signature)
- **Cadre :** feuille blanche dans un cadre d'encre marine de 3 px (2 px sous 420 px), marge intérieure de 11 px, grille carrée.
- **Lettres :** Poppins 500 encre ; mot trouvé en 700 marine ; lettres en cours de sélection en 700 marine profond.
- **Sélection :** glisser d'une lettre à l'autre, ou toucher la première puis la dernière ; la direction s'aligne sur les huit directions. Une capsule bleu ciel suit le doigt, et les lettres sélectionnées s'affichent en direct au-dessus de la grille en Poppins 700 espacée (sky-ink).
- **Trait de stylo :** chaque mot trouvé est entouré d'une capsule rouge tracée en SVG au-dessus des lettres, avec un léger tremblé : son inclinaison varie de ±2° d'un mot à l'autre, car le stylo ne trace jamais deux fois le même ovale. Le dernier mot se dessine en 0,55 s.
- **Liste :** numérotée, en colonnes à filets ; un mot trouvé est barré d'un trait rouge de 2 px et passe en encre diluée, de sorte que l'information ne repose pas sur la seule couleur. Toucher un mot trouvé rappelle sa définition.
- **Définition :** la coupure du dernier mot trouvé apparaît dans la zone réservée au-dessus de la grille, papier sous un filet rouge de 3 px, terme en Poppins marine, texte coupé à trois lignes. Un toucher la déplie par-dessus la grille ; elle s'efface seule après 7 à 20 s selon sa longueur. Une définition absente s'affiche « Définition non fournie par les auteurs. » en italique, encre diluée ; rien n'est inventé pour la combler.
- **Tampon RÉSOLU :** en fin de grille, « RÉSOLU » en Poppins 700 capitales rouges, double filet rouge de 4 px, incliné de -9°, sur un voile blanc à 86 %, tombe en 0,5 s.
- **Barre d'outils :** compteur « 11 / 40 trouvés » et chronomètre en chiffres tabulaires (rouge et gras quand le temps dépasse), puis chronomètre affichable, loupe (grille à 36 px par case, défilable) et pause (la grille est masquée).

### Offres
- **Mise en page :** les offres sont juxtaposées dans un même cadre, séparées par des filets verticaux (empilées sous 760 px). L'offre mise en avant (annuelle) est sur fond marine plein, texte blanc, bouton blanc à texte marine.
- **Prix :** en devise locale du pays (sélecteur de devise dans l'en-tête), formatés selon la langue, en Figure ; dessous, la période, l'équivalent mensuel et le prix de référence en dollars.
- **Économie entourée :** le pourcentage économisé est entouré d'un ovale à main levée tracé au stylo rouge (pen-on-navy sur fond marine).

### Points clés, pièges, alertes, corrélations cliniques
Chaque rubrique du cours a un titre Headline sous filet marine, puis son encadré à puces :
- **Points clés :** fond teinte marine, puces marine.
- **Pièges :** lavis ambre bordé d'ambre pâle.
- **Alertes (red flags) :** lavis rouge bordé de rouge pâle, puces rouge stylo.
- **Corrélations cliniques :** sans fond ni cadre, ouvertes par un filet marine de 2 px.

### QCM et flashcards
- **Options :** lignes de 48 px au moins, case carrée (ronde pour un choix unique) ; choisie, marine sur teinte marine ; corrigée, verte si juste, rouge stylo si fausse, avec la marque dans la case.
- **Explication :** encadré gris-bleu sous la question.
- **Flashcard :** recto en Poppins 700 marine sous un filet marine de 3 px ; verso séparé par un filet fin ; quatre boutons d'évaluation alignés.

### Progression
Une barre fine de 5 px (teinte marine, remplissage marine) et, pour la maîtrise d'un chapitre, un pourcentage en Poppins marine au-dessus de cette barre. Le graphique du temps d'étude est fait de barres gris-bleu, la dernière en marine.

## Do's and Don'ts

### Do:
- **Faire** entourer, barrer et corriger en rouge stylo, et nulle part ailleurs.
- **Faire** tracer un filet (fin, marine de 2 px ou double de 4 px) avant d'envisager un cadre ou une ombre.
- **Faire** passer tout nombre qui change ou s'aligne en chiffres tabulaires.
- **Faire** doubler chaque information colorée par un autre signe : mot barré en plus d'être rouge, marque dans la case en plus de la couleur de l'option.
- **Faire** respecter la demande de réduction des animations : sous `prefers-reduced-motion`, toutes les animations et transitions s'arrêtent et les mots entourés s'affichent déjà tracés.
- **Faire** employer le logo et les icônes de `apps/web/public/brand/` tels quels.
- **Faire** garder des cibles tactiles de 44 px au moins.

### Don't:
- **Ne pas** placer de surtitre ni de petite étiquette en capitales au-dessus d'un titre.
- **Ne pas** border un bloc d'une bande latérale colorée ; les accents se posent en filet supérieur.
- **Ne pas** afficher de progression en anneau ou en jauge circulaire ; un chiffre et une barre fine suffisent.
- **Ne pas** appliquer de dégradé à un texte, ni de dégradé décoratif à une surface.
- **Ne pas** poser d'ombre décalée dure ; les rares ombres restent diffuses et teintées de marine.
- **Ne pas** composer de tuile « gros chiffre » encadrée où le nombre sert de décor.
- **Ne pas** employer le bleu ciel comme texte sur blanc ni pour autre chose que la sélection en cours.
- **Ne pas** redessiner, recolorer ou réinterpréter le logo.
- **Ne pas** combler une définition manquante ; afficher « Définition non fournie par les auteurs. ».

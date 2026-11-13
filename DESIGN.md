# DESIGN.md — Cherche & Diagnostic

Source de vérité : le design system « Cherche & Diagnostic » du propriétaire (artefact claude.ai
`c8bd9b69-9a98-41eb-ad1f-76b2cfa1f0e4`, `project/README.md` et `project/tokens.json`, version 1).
Ce fichier décrit comment l'application web (`apps/web`) l'applique. En cas d'écart, le design system fait foi.
Implantation : 13/11/2026, en remplacement de la direction « page de jeux au stylo rouge » des 12–13/11.

## En une phrase

Une application de jeux pour apprendre la médecine : marine pour l'interface, ciel pour mettre en avant, rouge
pour le geste médical ; aplats, Poppins seule, formes arrondies comme le C et le stéthoscope du logo.

## Couleur

Tous les tokens sont des variables CSS dans `apps/web/src/styles.css` (`:root`). Les composants n'emploient que
les tokens sémantiques.

Thème : l'utilisateur choisit « Système », « Clair » ou « Sombre » dans Profil → Apparence (`lib/theme.ts`). Le
choix est propre à l'appareil (clé locale `cd.theme`, absente pour « Système ») et posé en `data-theme` sur
`<html>` ; sans attribut, `prefers-color-scheme` décide. Le logo (versions claire et inverse) et la couleur de la
barre du navigateur suivent le thème affiché.

| Token | Clair | Sombre | Emploi |
|---|---|---|---|
| `fond` | #f4f8fd | #00112b | Fond de page |
| `surface` / `surface-2` | #ffffff / #e9f1fa | #05214a / #0b2e5e | Cartes, grille, champs / zones en retrait |
| `bordure` / `bordure-forte` | #cddbec / #5d7ca3 | #1d4479 / #6f93c4 | Filets / contour des champs et boutons secondaires |
| `texte` / `texte-doux` | #012d69 / #43608a | #f1f6fc / #a9c1e0 | Texte courant et titres / secondaire |
| `primaire` | #012d69 | #079cef | Bouton principal, sélection en cours dans la grille |
| `accent` / `accent-fond` | #0067b5 / #d8effc | #6cc4f5 / #0b3b6e | Liens, valeurs, progression, réussite |
| `diagnostic` | #d80403 | #ff5a55 | Bouton « Diagnostic » : une fois par écran |
| `danger` / `alerte` | #a80303 / #7a4f00 | #ff9a96 / #f6c560 | Erreur / indice, temps presque écoulé |
| `surlignage-*` | ciel, rouge, ambre, marine | | Mots trouvés dans la grille, en alternance |

Règles appliquées :
- Le marine porte l'interface. Le ciel (`accent`) met en avant ; `ciel-500` n'est jamais du texte sur fond clair.
- Le rouge est réservé au bouton `diagnostic` (« Arrêter et voir le résultat » dans la grille, une fois par écran),
  à l'erreur (`danger`) et au logo. Jamais en décor ni pour un titre.
- Réussite en bleu, erreur en rouge, indice en ambre ; pas de vert. Chaque état porte aussi une icône ou un mot.
- Focus clavier : anneau `focus` plein de 2 px, décalé de 2 px.
- Aplats uniquement : pas de dégradé, pas de flou.

## Typographie

Une seule famille, Poppins 400, 500 et 700 (SIL OFL), auto-hébergée en WOFF (`apps/web/public/fonts`,
`tools/brand/build_assets.py`). Repli système pour le chinois. Pas d'italique (`em` est neutralisé).

| Style | Taille / interligne | Graisse | Emploi dans l'app |
|---|---|---|---|
| affichage | 40/44 | 700 | Titre de l'accueil (`.hero h1`), une fois par écran |
| titre-1 | 32/38 | 700 | Titre de page (`h1`, 26/32 sous 420 px) |
| titre-2 | 24/30 | 700 | Titre de section (`h2`) |
| titre-3 | 20/26 | 500 | Titre de carte (`h3`) |
| corps-l | 18/28 | 400 | Chapeau, définition dépliée, verso de carte |
| corps / corps-s / légende | 16/24, 14/20, 12/16 | 400–500 | Texte, aide, mentions |
| étiquette | 12/16, +0,06 em, capitales | 700 | Badges, en-têtes de tableau |
| lettre-grille | ≤ 20, +0,02 em | 500 | Lettres de la grille |
| mot-liste | 14/20, +0,04 em | 500 | Liste des mots (les libellés des livres sont déjà en capitales) |
| chiffre | 28/32, tabulaires | 700 | Compteur, statistiques |

Capitales réservées aux étiquettes, à la grille et à la liste ; jamais pour un titre ni un bouton.

## Espacement, formes, ombres

Pas de 4 px (`--space-1` à `--space-8`). Cartes : `space-4` de marge intérieure, filet `bordure` de 1 px,
`ombre-1`, `ombre-2` au survol. Rayons : `radius-md` (10) boutons et champs, `radius-lg` (16) cartes et grille,
`radius-pill` badges, barres, surlignages et pastille de navigation. Cible tactile ≥ 44 px (40 px pour un mot de
la liste). Mouvement : 120 ms sur les survols, 200 ms pour l'apparition d'un surlignage ; rien ne clignote ni ne
rebondit ; tout s'arrête avec `prefers-reduced-motion`.

## Composants (correspondance avec le design system)

| Design system | Application |
|---|---|
| `Logo` | `Logo` (`ui.tsx`) : SVG en aplats, version inverse en thème sombre |
| `Bouton` primaire / secondaire / diagnostic | `Button` variantes `primary`, `soft`, `ghost`, `danger`, `diagnostic` |
| `Badge` | `Badge` et `.tag` (pastille, étiquette en capitales) ; l'économie de l'offre annuelle est un badge ciel |
| `GrilleMots` | Grille 20 × 20 : pastilles `surlignage-*` sous les lettres (qui restent en `texte`), sélection en `primaire` |
| `ListeMots` | Liste numérotée en 2–3 colonnes, puce de la couleur du surlignage avec coche, mot barré |
| `BarreProgression` | `.bar` : piste `surface-2`, remplissage `accent`, en pastille |
| `Stat` | Cartes `.card.stat` avec chiffre tabulaire |
| `Message` | `Notice` (`ok` → réussite bleue, `warn` → indice ambre, `error` → erreur rouge) |
| `CarteJeu` | Cartes de chapitre et de discipline |

Écran de jeu : compteur et chronomètre en haut, définition (zone fixe de 100 px, la grille ne bouge jamais),
grille au centre, liste et bouton « Diagnostic » dessous sur téléphone, à droite sur ordinateur (≥ 900 px).

## Logo et images

- `apps/web/public/brand/*.svg` : logo horizontal, horizontal inverse, vertical et symbole, générés en aplats par
  `tools/brand/build_logo.py` à partir des tracés du composant `Logo` du design system
  (`assets/brand/logo-vectoriel.json`), eux-mêmes redessinés d'après le logo fourni par le propriétaire.
- `icon-*.png`, `apple-touch-icon.png`, `favicon-48.png` : symbole sur carré blanc arrondi (22 %), rendus par le
  même script. `logo-horizontal.png` sert aux e-mails, la plupart des messageries n'affichant pas le SVG.
- Les originaux fournis restent dans `assets/brand/*-source.png`, comme référence ; ils ne sont plus servis.
- Ne pas recolorer, déformer, ni poser le logo sur une photo ou un aplat rouge ou ciel.

## Voix

Français au vouvoiement, phrases courtes à l'impératif ; libellés de bouton en casse de phrase, verbe d'abord.
Termes médicaux accentués dans les définitions, en capitales sans accents dans la grille. Pas d'emoji ni de
points d'exclamation en série. La signature « Apprends. Révise. Progresse. » est conservée telle que fixée par le
propriétaire.

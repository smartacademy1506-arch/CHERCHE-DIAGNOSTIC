# Livres de la collection « CHERCHE ET DIAGNOSTIQUE »

Ce dossier reçoit, sur le poste de travail, le texte extrait des livres fournis par le propriétaire du projet.
Il n'est **pas** versionné : le dépôt est public et ces livres sont le contenu payant de l'application.
Seul ce README est suivi par git.

## Régénérer

Les PDF sont attendus dans `/mnt/user-data/uploads`, leur texte `pdftotext` dans `/home/claude/books/txt`.

```sh
python3 -I tools/books/parse_marked_books.py   # Physiologie générale, Ostéologie, Myologie, Innervation
python3 -I tools/books/parse_expert_books.py   # Organes, Vascularisation (20 chapitres)
python3 -I tools/books/parse_pharma_semio.py   # Pharmacologie, Sémiologie (édition à 21 chapitres)
python3 -I tools/books/check_books.py content/books/*
```

Chaque livre donne `content/books/<livre>/book.json` et un fichier par chapitre :
`slug`, `order`, `title.fr`, `summary.fr`, `terms[]` (`word`, `fr`, `definition.fr`), `grid` (`size`, `rows`),
`placements[]` (`term_index`, `word`, `row`, `col`, `d_row`, `d_col`), `questions[]`, `vignettes[]` (`case`, `answer`),
`key_points[]`, `pitfalls[]`, `red_flags[]`, `clinical_correlations[]`.

## Importer

Voir `supabase/seed/books/README.md`.

## Points à valider par les auteurs

Les `notes` de chaque `book.json` listent les rattachements approximatifs entre un mot de grille et une entrée
du glossaire, et les définitions laissées vides faute d'entrée correspondante (38 au total : 31 en Pharmacologie,
4 en Vascularisation, 3 en Organes).

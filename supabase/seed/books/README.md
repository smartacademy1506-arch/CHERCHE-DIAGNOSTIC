# Charges d'import chiffrées des livres

Les fichiers `*.asc` contiennent, chiffrés (OpenPGP, AES-256, RFC 4880), les chapitres des huit livres de la
collection au format de `public.admin_import_chapter`. Le dépôt est public : le texte des livres n'y figure
jamais en clair. La clé est conservée dans Supabase Vault (secret `books_import_passphrase`) du projet.

| Fichier | Livre | Chapitres | Termes | Définitions absentes du livre |
|---|---|---|---|---|
| physiologie.asc | Physiologie générale | 16 | 960 | 0 |
| anatomie-osteologie.asc | Anatomie humaine : Ostéologie | 11 | 660 | 0 |
| anatomie-myologie.asc | Anatomie humaine : Myologie | 11 | 660 | 0 |
| anatomie-innervation.asc | Anatomie humaine : Innervation | 12 | 720 | 0 |
| anatomie-vascularisation.asc | Anatomie humaine : Vascularisation | 20 | 1200 | 4 |
| anatomie-organes.asc | Anatomie humaine : Organes | 21 | 1260 | 3 |
| pharmacologie.asc | Pharmacologie par classes thérapeutiques | 37 | 2220 | 31 |
| semiologie.asc | Sémiologie médicale par systèmes (21 chapitres) | 21 | 1260 | 0 |

## Refaire les charges

```sh
python3 -I tools/books/to_payloads.py /tmp/import         # revérifie chaque grille comme app.puzzle_errors
export GNUPGHOME=$(mktemp -d)
for f in /tmp/import/*.json; do
  [ "$(basename $f)" = manifest.json ] && continue
  gpg --batch --rfc4880 --symmetric --armor --cipher-algo AES256 --compress-algo zlib \
      --passphrase-file <fichier contenant la clé> -o supabase/seed/books/$(basename $f .json).asc $f
done
```

## Importer

1. Appliquer la migration `20261113000800_book_disciplines.sql` (disciplines d'anatomie par volume).
2. Pousser les `.asc`, puis lancer `import_books.sql` en remplaçant `__REF__` par le commit.

La base télécharge chaque fichier depuis GitHub (extension `http`), le déchiffre avec la clé du Vault
(`pgcrypto`) et appelle `admin_import_chapter`. Tout le contenu entre « in_review » ; le chapitre 1 de chaque
livre est gratuit. Une grille invalide annule l'import du livre entier.

3. Relancer ensuite `apply_corrections.sql` (même remplacement de `__REF__`) : un réimport efface les corrections.

## Corrections validées par les auteurs

`corrections-2026-11-14.asc` contient, chiffrées avec la même clé, les 49 définitions validées par les auteurs
le 14 novembre 2026 (détail : `docs/06_VALIDATION/VALIDATION_AUTEURS_2026-11-14.md`) :

- 38 mots dont le livre ne reliait pas la définition : chacun est rattaché à l'entrée de son glossaire et affiche la
  définition originale du livre ;
- 11 définitions corrigées, chacune avec ses sources.

`apply_corrections.sql` met à jour la définition et la fiche de révision de chaque mot (la fiche est créée si elle
manquait), conserve l'état antérieur dans `content_versions` et incrémente la version du chapitre. Depuis ces
corrections, plus aucun mot des grilles n'est sans définition.

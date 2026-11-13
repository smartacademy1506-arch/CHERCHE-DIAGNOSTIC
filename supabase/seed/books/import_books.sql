-- Import des huit livres dans la base (à lancer avec le rôle postgres, après la migration 20261113000800).
-- Remplacer __REF__ par le commit qui contient les fichiers .asc. La clé de déchiffrement est lue dans
-- Supabase Vault (secret « books_import_passphrase ») : elle ne figure jamais dans ce dépôt.
-- Tout le contenu entre « in_review » ; le chapitre 1 de chaque livre est gratuit.
-- Une grille invalide (vérifiée par app.puzzle_errors) annule l'import de tout le livre.
with books(discipline) as (values
  ('physiologie'), ('anatomie-osteologie'), ('anatomie-myologie'), ('anatomie-innervation'),
  ('anatomie-vascularisation'), ('anatomie-organes'), ('pharmacologie'), ('semiologie')),
key as (select decrypted_secret as k from vault.decrypted_secrets where name = 'books_import_passphrase'),
payloads as (
  select b.discipline, convert_from(extensions.pgp_sym_decrypt_bytea(extensions.dearmor(
           (extensions.http_get('https://raw.githubusercontent.com/smartacademy1506-arch/CHERCHE-DIAGNOSTIC/__REF__/supabase/seed/books/'
                                 || b.discipline || '.asc')).content), (select k from key)), 'UTF8')::jsonb as chapters
  from books b),
imported as (
  select p.discipline, public.admin_import_chapter(p.discipline, ch, (ch ->> 'order')::int = 1, false) as r
  from payloads p, jsonb_array_elements(p.chapters) ch)
select discipline, count(*) as chapters, sum((r ->> 'terms')::int) as terms, sum((r ->> 'puzzles')::int) as grilles_validees
from imported group by discipline order by discipline;

-- Un terme sans définition dans le livre garde sa place dans la grille mais n'a pas de fiche de révision.
delete from public.flashcards f using public.glossary_entries g
where g.term_id = f.term_id and coalesce(g.definition ->> 'fr', '') = '';

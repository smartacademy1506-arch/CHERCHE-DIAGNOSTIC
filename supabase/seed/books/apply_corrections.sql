-- Corrections de définitions validées par les auteurs (à lancer avec le rôle postgres, APRÈS import_books.sql :
-- un réimport des livres efface ces corrections, il faut donc relancer ce script ensuite).
-- Remplacer __REF__ par le commit qui contient le fichier .asc. La clé est celle des livres (Vault,
-- secret « books_import_passphrase ») : elle ne figure jamais dans ce dépôt.
--
-- Pour chaque élément du fichier : la définition du glossaire et sa fiche de révision sont mises à jour (la fiche
-- est créée si le terme n'en avait pas, faute de définition), avec les sources et la date de validation.
-- L'état antérieur de chaque définition est conservé dans public.content_versions (migration 20261114000100),
-- et la version du chapitre est incrémentée pour que les appareils hors ligne le retéléchargent.
-- Le script s'arrête sans rien modifier si un mot est introuvable ou ambigu. Il peut être relancé sans effet.
do $$
declare
  v_doc jsonb; it jsonb; v_term record; v_def text; v_n int := 0;
begin
  select convert_from(extensions.pgp_sym_decrypt_bytea(extensions.dearmor(
           (extensions.http_get('https://raw.githubusercontent.com/smartacademy1506-arch/CHERCHE-DIAGNOSTIC/__REF__/supabase/seed/books/corrections-2026-11-14.asc')).content),
           (select decrypted_secret from vault.decrypted_secrets where name = 'books_import_passphrase')), 'UTF8')::jsonb
    into v_doc;

  for it in select value from jsonb_array_elements(v_doc -> 'items') loop
    begin
      select t.id, t.chapter_id, t.label, t.sort, t.status into strict v_term
      from public.disciplines di
      join public.chapters c on c.discipline_id = di.id and c.sort = (it ->> 'chapter')::int and c.status <> 'archived'
      join public.word_search_puzzles p on p.chapter_id = c.id and p.language_code = 'fr'
      join public.puzzle_words pw on pw.puzzle_id = p.id and pw.word = it ->> 'word'
      join public.medical_terms t on t.id = pw.term_id
      where di.slug = it ->> 'discipline';
    exception
      when no_data_found then raise exception 'Mot introuvable : % (%, chapitre %)', it ->> 'word', it ->> 'discipline', it ->> 'chapter';
      when too_many_rows then raise exception 'Mot ambigu : % (%, chapitre %)', it ->> 'word', it ->> 'discipline', it ->> 'chapter';
    end;

    v_def := it ->> 'definition';
    update public.glossary_entries g
    set definition = g.definition || jsonb_build_object('fr', v_def),
        source_refs = it -> 'source_refs',
        last_verified_at = (v_doc ->> 'validated_at')::timestamptz
    where g.term_id = v_term.id;
    if not found then
      raise exception 'Entrée du glossaire absente pour %', it ->> 'word';
    end if;

    insert into public.flashcards(chapter_id, term_id, front, back, sort, status)
    values (v_term.chapter_id, v_term.id, v_term.label, jsonb_build_object('fr', v_def), v_term.sort, v_term.status)
    on conflict (term_id) do update set back = public.flashcards.back || jsonb_build_object('fr', v_def);
    v_n := v_n + 1;
  end loop;

  if v_n <> jsonb_array_length(v_doc -> 'items') then
    raise exception 'Seulement % éléments appliqués sur %', v_n, jsonb_array_length(v_doc -> 'items');
  end if;
  raise notice '% définitions appliquées', v_n;
end $$;

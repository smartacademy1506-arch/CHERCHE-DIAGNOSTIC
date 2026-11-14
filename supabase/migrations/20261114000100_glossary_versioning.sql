-- Une définition du glossaire modifiée doit, comme les autres contenus pédagogiques :
-- 1. garder son état antérieur dans public.content_versions (traçabilité des corrections médicales) ;
-- 2. incrémenter la version de son chapitre, pour que les appareils hors ligne retéléchargent le chapitre
--    (apps/web/src/lib/data.ts compare chapters.content_version à la copie locale).
-- Jusqu'ici, glossary_entries n'avait que le déclencheur updated_at : une correction de définition
-- restait invisible pour un chapitre déjà téléchargé.

create or replace function app.bump_chapter_version_by_term() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  update public.chapters c set content_version = c.content_version + 1
  where c.id in (select distinct t.chapter_id from changed n join public.medical_terms t on t.id = n.term_id);
  return null;
end $$;

revoke execute on function app.bump_chapter_version_by_term() from public, anon, authenticated;

create trigger glossary_entries_track after update on public.glossary_entries
  for each row execute function app.track_content();
create trigger glossary_entries_bump_i after insert on public.glossary_entries
  referencing new table as changed for each statement execute function app.bump_chapter_version_by_term();
create trigger glossary_entries_bump_u after update on public.glossary_entries
  referencing new table as changed for each statement execute function app.bump_chapter_version_by_term();
create trigger glossary_entries_bump_d after delete on public.glossary_entries
  referencing old table as changed for each statement execute function app.bump_chapter_version_by_term();

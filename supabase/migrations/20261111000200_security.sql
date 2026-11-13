-- CHERCHE & DIAGNOSTIC — fonctions d'autorisation, déclencheurs d'intégrité et politiques RLS

grant usage on schema app to anon, authenticated, service_role;

-- Les paiements sont conservés (comptabilité) mais anonymisés si le compte est supprimé.
alter table public.payments alter column user_id drop not null;
alter table public.payments drop constraint payments_user_id_fkey;
alter table public.payments add constraint payments_user_id_fkey
  foreign key (user_id) references auth.users(id) on delete set null;

-- Adresses e-mail autorisées à devenir super administrateur (après confirmation de l'e-mail).
create table app.bootstrap_admins (email text primary key);

-- ───────────────────────── Fonctions d'autorisation ─────────────────────────
create or replace function app.has_role(variadic p_roles text[]) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.user_roles ur
                 where ur.user_id = (select auth.uid()) and ur.role_code = any (p_roles));
$$;

create or replace function app.is_admin() returns boolean
language sql stable security definer set search_path = '' as $$
  select app.has_role('super_admin', 'admin');
$$;

create or replace function app.can_publish() returns boolean
language sql stable security definer set search_path = '' as $$
  select app.has_role('super_admin', 'admin', 'pedagogy_lead');
$$;

create or replace function app.can_edit_content() returns boolean
language sql stable security definer set search_path = '' as $$
  select app.has_role('super_admin', 'admin', 'pedagogy_lead', 'contributor');
$$;

create or replace function app.is_staff() returns boolean
language sql stable security definer set search_path = '' as $$
  select app.has_role('super_admin', 'admin', 'pedagogy_lead', 'contributor', 'moderator');
$$;

create or replace function app.has_active_subscription() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.subscriptions s
                 where s.user_id = (select auth.uid()) and s.status = 'active'
                   and s.starts_at <= now() and (s.ends_at is null or s.ends_at > now()));
$$;

-- Mode pilote : le contenu « in_review » est visible (avec un bandeau) tant que la validation éditoriale est en cours.
create or replace function app.pilot_mode() returns boolean
language sql stable security definer set search_path = '' as $$
  select coalesce((select (s.value)::boolean from public.app_settings s where s.key = 'show_in_review_content'), false);
$$;

create or replace function app.content_visible(p_status text) returns boolean
language sql stable security definer set search_path = '' as $$
  select p_status = 'published' or (p_status = 'in_review' and app.pilot_mode()) or app.can_edit_content();
$$;

create or replace function app.can_access_chapter(p_chapter_id uuid) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.chapters c join public.disciplines d on d.id = c.discipline_id
    where c.id = p_chapter_id
      and app.content_visible(c.status) and app.content_visible(d.status)
      and (c.is_free or app.has_active_subscription() or app.is_staff()));
$$;

-- Forme « grille » d'un terme : majuscules, sans accents, sans espaces ni ponctuation.
create or replace function app.grid_form(p_term text) returns text
language sql immutable set search_path = '' as $$
  select regexp_replace(
    translate(replace(replace(upper(p_term), 'Œ', 'OE'), 'Æ', 'AE'),
              'ÀÂÄÁÃÅÇÉÈÊËÍÌÎÏÑÓÒÔÖÕÚÙÛÜÝŸ', 'AAAAAACEEEEIIIINOOOOOUUUUYY'),
    '[^A-Z]', '', 'g');
$$;

-- ───────────────────────── Déclencheurs génériques ─────────────────────────
create or replace function app.touch_updated_at() returns trigger
language plpgsql set search_path = '' as $$
begin new.updated_at := now(); return new; end $$;

create or replace function app.guard_publish() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if new.status = 'published' and (tg_op = 'INSERT' or old.status is distinct from 'published') then
    if (select auth.uid()) is not null and not app.can_publish() then
      raise exception 'Seul un responsable pédagogique peut publier un contenu' using errcode = '42501';
    end if;
  end if;
  return new;
end $$;

create or replace function app.track_content() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if (to_jsonb(old) - 'updated_at' - 'content_version') is distinct from (to_jsonb(new) - 'updated_at' - 'content_version') then
    insert into public.content_versions(entity_type, entity_id, snapshot, changed_by)
    values (tg_table_name, old.id, to_jsonb(old), (select auth.uid()));
  end if;
  return null;
end $$;

create or replace function app.bump_chapter_version() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  update public.chapters c set content_version = c.content_version + 1
  where c.id in (select distinct n.chapter_id from changed n);
  return null;
end $$;

create or replace function app.audit() returns trigger
language plpgsql security definer set search_path = '' as $$
declare v_row jsonb := case when tg_op = 'DELETE' then to_jsonb(old) else to_jsonb(new) end;
begin
  insert into public.audit_logs(actor_id, action, entity_type, entity_id, details)
  values ((select auth.uid()), tg_op, tg_table_name,
          coalesce(v_row->>'id', v_row->>'code', v_row->>'key', v_row->>'user_id'), v_row - 'raw');
  return null;
end $$;

do $$
declare t text;
begin
  foreach t in array array['disciplines','chapters','lessons','medical_terms','quiz_questions','open_questions','flashcards','clinical_cases','word_search_puzzles'] loop
    execute format('create trigger %I before update on public.%I for each row execute function app.touch_updated_at()', t || '_touch', t);
    execute format('create trigger %I before insert or update of status on public.%I for each row execute function app.guard_publish()', t || '_guard_publish', t);
    execute format('create trigger %I after update on public.%I for each row execute function app.track_content()', t || '_track', t);
  end loop;
  foreach t in array array['lessons','learning_objectives','medical_terms','quiz_questions','open_questions','flashcards','word_search_puzzles'] loop
    execute format('create trigger %I after insert on public.%I referencing new table as changed for each statement execute function app.bump_chapter_version()', t || '_bump_i', t);
    execute format('create trigger %I after update on public.%I referencing new table as changed for each statement execute function app.bump_chapter_version()', t || '_bump_u', t);
    execute format('create trigger %I after delete on public.%I referencing old table as changed for each statement execute function app.bump_chapter_version()', t || '_bump_d', t);
  end loop;
  foreach t in array array['profiles','glossary_entries','open_question_submissions','plans','app_settings'] loop
    execute format('create trigger %I before update on public.%I for each row execute function app.touch_updated_at()', t || '_touch', t);
  end loop;
  foreach t in array array['user_roles','subscriptions','payments','plans','plan_prices','currencies','app_settings'] loop
    execute format('create trigger %I after insert or update or delete on public.%I for each row execute function app.audit()', t || '_audit', t);
  end loop;
end $$;

-- ───────────────────────── Intégrité des grilles de mots mêlés ─────────────────────────
-- Une grille ne peut quitter le statut « draft » que si chaque mot est réellement présent
-- aux coordonnées annoncées et si la liste des mots correspond aux termes du chapitre.
create or replace function app.puzzle_errors(p_puzzle_id uuid, p_chapter_id uuid, p_lang text, p_grid text[], p_size int)
returns text[] language plpgsql stable security definer set search_path = '' as $$
declare
  errs text[] := '{}';
  w record; i int; r int; c int; v_missing text;
begin
  if array_length(p_grid, 1) is distinct from p_size then return array['hauteur de grille incorrecte']; end if;
  for i in 1..p_size loop
    if p_grid[i] !~ ('^[A-Z]{' || p_size || '}$') then errs := errs || format('ligne %s invalide', i); end if;
  end loop;
  if cardinality(errs) > 0 then return errs; end if;
  if not exists (select 1 from public.puzzle_words pw where pw.puzzle_id = p_puzzle_id) then return array['aucun mot dans la grille']; end if;

  for w in select pw.*, t.chapter_id as term_chapter, app.grid_form(t.label ->> p_lang) as expected
           from public.puzzle_words pw join public.medical_terms t on t.id = pw.term_id
           where pw.puzzle_id = p_puzzle_id loop
    if w.term_chapter <> p_chapter_id then errs := errs || format('%s : terme d''un autre chapitre', w.word); end if;
    if w.expected is distinct from w.word then errs := errs || format('%s : ne correspond pas au terme (%s)', w.word, w.expected); end if;
    for i in 0..length(w.word) - 1 loop
      r := w.start_row + i * w.d_row; c := w.start_col + i * w.d_col;
      if r < 0 or c < 0 or r >= p_size or c >= p_size then
        errs := errs || format('%s : hors de la grille', w.word); exit;
      end if;
      if substr(p_grid[r + 1], c + 1, 1) <> substr(w.word, i + 1, 1) then
        errs := errs || format('%s : lettre %s absente aux coordonnées annoncées', w.word, i + 1); exit;
      end if;
    end loop;
  end loop;

  select string_agg(t.label ->> p_lang, ', ') into v_missing
  from public.medical_terms t
  where t.chapter_id = p_chapter_id and t.status <> 'archived' and coalesce(t.label ->> p_lang, '') <> ''
    and not exists (select 1 from public.puzzle_words pw where pw.puzzle_id = p_puzzle_id and pw.term_id = t.id);
  if v_missing is not null then errs := errs || ('termes absents de la grille : ' || v_missing); end if;
  return errs;
end $$;

create or replace function app.guard_puzzle() returns trigger
language plpgsql security definer set search_path = '' as $$
declare errs text[];
begin
  if tg_op = 'INSERT' then
    if new.status <> 'draft' then
      raise exception 'Une grille se crée en brouillon, puis se valide une fois ses mots enregistrés' using errcode = '23514';
    end if;
    new.validated_at := null;
    return new;
  end if;
  if new.status = 'draft' then
    new.validated_at := null;
  elsif old.status = 'draft' or new.grid is distinct from old.grid or new.size is distinct from old.size
        or new.language_code is distinct from old.language_code or new.validated_at is null then
    errs := app.puzzle_errors(new.id, new.chapter_id, new.language_code, new.grid, new.size);
    if cardinality(errs) > 0 then
      raise exception 'Grille invalide : %', array_to_string(errs, ' ; ') using errcode = '23514';
    end if;
    new.validated_at := now();
  else
    new.validated_at := old.validated_at;
  end if;
  return new;
end $$;
create trigger word_search_puzzles_guard before insert or update on public.word_search_puzzles
  for each row execute function app.guard_puzzle();

-- Toute modification des mots renvoie la grille en brouillon (elle devra être revalidée).
create or replace function app.unvalidate_puzzle() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  update public.word_search_puzzles p set status = 'draft'
  where p.id in (select distinct n.puzzle_id from changed n) and p.status <> 'draft';
  return null;
end $$;
create trigger puzzle_words_unvalidate_i after insert on public.puzzle_words
  referencing new table as changed for each statement execute function app.unvalidate_puzzle();
create trigger puzzle_words_unvalidate_u after update on public.puzzle_words
  referencing new table as changed for each statement execute function app.unvalidate_puzzle();
create trigger puzzle_words_unvalidate_d after delete on public.puzzle_words
  referencing old table as changed for each statement execute function app.unvalidate_puzzle();

-- ───────────────────────── Comptes et rôles ─────────────────────────
create or replace function app.handle_new_user() returns trigger
language plpgsql security definer set search_path = '' as $$
declare
  v_lang text := lower(coalesce(new.raw_user_meta_data ->> 'language_code', 'fr'));
  v_country text := upper(new.raw_user_meta_data ->> 'country_code');
begin
  if not exists (select 1 from public.languages l where l.code = v_lang and l.is_active) then v_lang := 'fr'; end if;
  if v_country is not null and not exists (select 1 from public.countries c where c.code = v_country) then v_country := null; end if;
  insert into public.profiles(id, full_name, country_code, language_code, consent_at)
  values (new.id, left(nullif(trim(new.raw_user_meta_data ->> 'full_name'), ''), 120), v_country, v_lang,
          case when new.raw_user_meta_data ->> 'consent' = 'true' then now() end)
  on conflict (id) do nothing;
  insert into public.user_roles(user_id, role_code) values (new.id, 'student') on conflict do nothing;
  return new;
end $$;
create trigger on_auth_user_created after insert on auth.users
  for each row execute function app.handle_new_user();

create or replace function app.handle_user_confirmed() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if new.email_confirmed_at is not null
     and exists (select 1 from app.bootstrap_admins b where lower(b.email) = lower(new.email)) then
    insert into public.user_roles(user_id, role_code) values (new.id, 'super_admin') on conflict do nothing;
  end if;
  return new;
end $$;
create trigger on_auth_user_confirmed after insert or update of email_confirmed_at on auth.users
  for each row execute function app.handle_user_confirmed();

create or replace function app.guard_user_roles() returns trigger
language plpgsql security definer set search_path = '' as $$
declare v_role text := case when tg_op = 'DELETE' then old.role_code else new.role_code end;
begin
  if (select auth.uid()) is not null then
    if not app.is_admin() then
      raise exception 'Réservé aux administrateurs' using errcode = '42501';
    end if;
    if v_role in ('super_admin', 'admin') and not app.has_role('super_admin') then
      raise exception 'Seul un super administrateur peut attribuer ou retirer ce rôle' using errcode = '42501';
    end if;
    if tg_op = 'INSERT' then new.granted_by := (select auth.uid()); end if;
  end if;
  return case when tg_op = 'DELETE' then old else new end;
end $$;
create trigger user_roles_guard before insert or update or delete on public.user_roles
  for each row execute function app.guard_user_roles();

-- ───────────────────────── Privilèges et RLS ─────────────────────────
grant select on all tables in schema public to anon, authenticated;
grant insert, update, delete on all tables in schema public to authenticated;
grant usage on all sequences in schema public to authenticated;
revoke all on public.quiz_answer_keys from anon;

do $$
declare t text;
begin
  for t in select tablename from pg_tables where schemaname = 'public' loop
    execute format('alter table public.%I enable row level security', t);
  end loop;

  -- Référentiels : lecture publique, écriture réservée aux administrateurs.
  foreach t in array array['languages','currencies','countries','curricula','roles','permissions','role_permissions','plan_prices'] loop
    execute format('create policy %I on public.%I for select to anon, authenticated using (true)', t || '_read', t);
    execute format('create policy %I on public.%I for insert to authenticated with check (app.is_admin())', t || '_admin_insert', t);
    execute format('create policy %I on public.%I for update to authenticated using (app.is_admin()) with check (app.is_admin())', t || '_admin_update', t);
    execute format('create policy %I on public.%I for delete to authenticated using (app.is_admin())', t || '_admin_delete', t);
  end loop;

  -- Contenus : écriture par l'équipe éditoriale, suppression par les responsables.
  foreach t in array array['disciplines','chapters','lessons','learning_objectives','medical_terms','glossary_entries','word_search_puzzles','puzzle_words','quiz_questions','quiz_options','quiz_answer_keys','open_questions','flashcards','clinical_cases','clinical_case_questions','media_assets'] loop
    execute format('create policy %I on public.%I for insert to authenticated with check (app.can_edit_content())', t || '_staff_insert', t);
    execute format('create policy %I on public.%I for update to authenticated using (app.can_edit_content()) with check (app.can_edit_content())', t || '_staff_update', t);
    execute format('create policy %I on public.%I for delete to authenticated using (app.can_publish())', t || '_lead_delete', t);
  end loop;

  -- Contenus rattachés à un chapitre : lecture selon l'accès au chapitre (gratuit, abonné ou équipe).
  foreach t in array array['lessons','medical_terms','word_search_puzzles','quiz_questions','open_questions','flashcards'] loop
    execute format('create policy %I on public.%I for select to anon, authenticated using (app.can_access_chapter(chapter_id) and app.content_visible(status))', t || '_read', t);
  end loop;

  -- Données personnelles : chacun ne voit et ne modifie que les siennes.
  foreach t in array array['puzzle_sessions','open_question_submissions','flashcard_states','flashcard_reviews','user_progress','learning_sessions','bookmarks'] loop
    execute format('create policy %I on public.%I for select to authenticated using (user_id = (select auth.uid()))', t || '_own_read', t);
    execute format('create policy %I on public.%I for delete to authenticated using (user_id = (select auth.uid()))', t || '_own_delete', t);
  end loop;
  foreach t in array array['user_progress','learning_sessions','bookmarks'] loop
    execute format('create policy %I on public.%I for insert to authenticated with check (user_id = (select auth.uid()))', t || '_own_insert', t);
    execute format('create policy %I on public.%I for update to authenticated using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()))', t || '_own_update', t);
  end loop;
end $$;

create policy app_settings_read on public.app_settings for select to anon, authenticated using (is_public or app.is_admin());
create policy app_settings_admin_insert on public.app_settings for insert to authenticated with check (app.is_admin());
create policy app_settings_admin_update on public.app_settings for update to authenticated using (app.is_admin()) with check (app.is_admin());
create policy app_settings_admin_delete on public.app_settings for delete to authenticated using (app.is_admin());

create policy plans_read on public.plans for select to anon, authenticated using (is_active or app.is_admin());
create policy plans_admin_insert on public.plans for insert to authenticated with check (app.is_admin());
create policy plans_admin_update on public.plans for update to authenticated using (app.is_admin()) with check (app.is_admin());
create policy plans_admin_delete on public.plans for delete to authenticated using (app.is_admin());

create policy profiles_read on public.profiles for select to authenticated using (id = (select auth.uid()) or app.is_admin());
create policy profiles_insert on public.profiles for insert to authenticated with check (id = (select auth.uid()));
create policy profiles_update on public.profiles for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy user_roles_read on public.user_roles for select to authenticated using (user_id = (select auth.uid()) or app.is_admin());
create policy user_roles_admin_insert on public.user_roles for insert to authenticated with check (app.is_admin());
create policy user_roles_admin_delete on public.user_roles for delete to authenticated using (app.is_admin());

create policy disciplines_read on public.disciplines for select to anon, authenticated using (app.content_visible(status));
create policy chapters_read on public.chapters for select to anon, authenticated using (app.content_visible(status));
create policy learning_objectives_read on public.learning_objectives for select to anon, authenticated
  using (exists (select 1 from public.chapters c where c.id = chapter_id));
create policy glossary_entries_read on public.glossary_entries for select to anon, authenticated
  using (exists (select 1 from public.medical_terms t where t.id = term_id));
create policy puzzle_words_read on public.puzzle_words for select to anon, authenticated
  using (exists (select 1 from public.word_search_puzzles p where p.id = puzzle_id));
create policy quiz_options_read on public.quiz_options for select to anon, authenticated
  using (exists (select 1 from public.quiz_questions q where q.id = question_id));
create policy quiz_answer_keys_staff_read on public.quiz_answer_keys for select to authenticated using (app.can_edit_content());
create policy clinical_cases_read on public.clinical_cases for select to anon, authenticated
  using (status = 'published' or app.can_edit_content());
create policy clinical_case_questions_read on public.clinical_case_questions for select to anon, authenticated
  using (exists (select 1 from public.clinical_cases cc where cc.id = case_id));
create policy media_assets_read on public.media_assets for select to anon, authenticated using (true);

-- Résultats : l'insertion exige aussi l'accès au contenu visé (la sous-requête est soumise au RLS).
create policy puzzle_sessions_own_insert on public.puzzle_sessions for insert to authenticated
  with check (user_id = (select auth.uid()) and exists (select 1 from public.word_search_puzzles p where p.id = puzzle_id));
create policy puzzle_sessions_own_update on public.puzzle_sessions for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy open_question_submissions_own_insert on public.open_question_submissions for insert to authenticated
  with check (user_id = (select auth.uid()) and exists (select 1 from public.open_questions q where q.id = question_id));
create policy open_question_submissions_own_update on public.open_question_submissions for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy flashcard_states_own_insert on public.flashcard_states for insert to authenticated
  with check (user_id = (select auth.uid()) and exists (select 1 from public.flashcards f where f.id = flashcard_id));
create policy flashcard_states_own_update on public.flashcard_states for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy flashcard_reviews_own_insert on public.flashcard_reviews for insert to authenticated
  with check (user_id = (select auth.uid()) and exists (select 1 from public.flashcards f where f.id = flashcard_id));

-- Tentatives de QCM : lecture seule côté client, l'écriture passe par submit_quiz_attempt().
create policy quiz_attempts_own_read on public.quiz_attempts for select to authenticated using (user_id = (select auth.uid()));
create policy quiz_answers_own_read on public.quiz_answers for select to authenticated
  using (exists (select 1 from public.quiz_attempts a where a.id = attempt_id and a.user_id = (select auth.uid())));

-- Paiements et abonnements : lecture seule côté client, l'écriture passe par les fonctions serveur.
create policy payments_read on public.payments for select to authenticated using (user_id = (select auth.uid()) or app.is_admin());
create policy subscriptions_read on public.subscriptions for select to authenticated using (user_id = (select auth.uid()) or app.is_admin());

create policy notifications_own_read on public.notifications for select to authenticated using (user_id = (select auth.uid()));
create policy notifications_own_update on public.notifications for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy notifications_admin_insert on public.notifications for insert to authenticated with check (app.is_admin());

create policy content_versions_staff_read on public.content_versions for select to authenticated using (app.can_edit_content());
create policy audit_logs_admin_read on public.audit_logs for select to authenticated using (app.is_admin());

-- Les tables sans politique d'écriture côté client sont également fermées au niveau des privilèges.
revoke insert, update, delete on public.quiz_attempts, public.quiz_answers, public.payments, public.subscriptions,
  public.content_versions, public.audit_logs from authenticated;

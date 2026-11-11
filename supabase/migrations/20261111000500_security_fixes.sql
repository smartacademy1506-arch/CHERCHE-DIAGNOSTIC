-- CHERCHE & DIAGNOSTIC — correctifs issus de la revue de sécurité indépendante du 11/11/2026

-- E1. La suppression de son propre compte échouait : le garde des rôles refusait la suppression en cascade,
--     et le journal d'audit référençait l'utilisateur en cours de suppression.
create or replace function app.guard_user_roles() returns trigger
language plpgsql security definer set search_path = '' as $$
declare v_role text := case when tg_op = 'DELETE' then old.role_code else new.role_code end;
begin
  if (select auth.uid()) is not null then
    -- suppression en cascade du compte de l'appelant lui-même
    if tg_op = 'DELETE' and old.user_id = (select auth.uid())
       and not exists (select 1 from auth.users u where u.id = old.user_id) then
      return old;
    end if;
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

create or replace function app.audit() returns trigger
language plpgsql security definer set search_path = '' as $$
declare v_row jsonb := case when tg_op = 'DELETE' then to_jsonb(old) else to_jsonb(new) end;
begin
  insert into public.audit_logs(actor_id, action, entity_type, entity_id, details)
  values ((select u.id from auth.users u where u.id = (select auth.uid())), tg_op, tg_table_name,
          coalesce(v_row->>'id', v_row->>'code', v_row->>'key', v_row->>'user_id'), v_row - 'raw');
  return null;
end $$;

-- M1 / F6. Une nouvelle demande n'annule plus une demande peut-être déjà réglée : la demande en attente pour la
--          même offre et la même devise est réutilisée, et le nombre de demandes en attente est plafonné.
create or replace function public.create_payment_intent(p_plan_code text, p_currency text default 'USD')
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_uid uuid := (select auth.uid()); v_plan public.plans%rowtype; v_cur text; v_pay public.payments%rowtype;
begin
  if v_uid is null then raise exception 'not_authenticated' using errcode = '42501'; end if;
  select * into v_plan from public.plans where code = p_plan_code and is_active;
  if not found then raise exception 'plan_not_found' using errcode = '22023'; end if;
  select c.code into v_cur from public.currencies c where c.code = upper(p_currency) and c.is_active;
  if v_cur is null then v_cur := 'USD'; end if;

  select * into v_pay from public.payments
  where user_id = v_uid and plan_id = v_plan.id and currency_code = v_cur and status = 'pending'
  order by created_at desc limit 1;
  if not found then
    if (select count(*) from public.payments where user_id = v_uid and status = 'pending') >= 5 then
      raise exception 'too_many_pending_payments' using errcode = '54000';
    end if;
    insert into public.payments(user_id, plan_id, reference, amount, currency_code, amount_usd)
    values (v_uid, v_plan.id, 'CD-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 10)),
            app.plan_amount(v_plan.id, v_cur), v_cur, v_plan.price_usd)
    returning * into v_pay;
  end if;
  return jsonb_build_object('id', v_pay.id, 'reference', v_pay.reference, 'amount', v_pay.amount,
                            'currency_code', v_pay.currency_code, 'plan_code', v_plan.code, 'status', v_pay.status);
end $$;

-- M3. Objectifs et cas cliniques d'un chapitre payant : même règle d'accès que le reste du chapitre.
drop policy learning_objectives_read on public.learning_objectives;
create policy learning_objectives_read on public.learning_objectives for select to anon, authenticated
  using (app.can_access_chapter(chapter_id));
drop policy clinical_cases_read on public.clinical_cases;
create policy clinical_cases_read on public.clinical_cases for select to anon, authenticated
  using (app.can_edit_content() or (status = 'published' and (chapter_id is null or app.can_access_chapter(chapter_id))));

-- M4. Un contributeur ne peut ni rendre un chapitre gratuit ou payant, ni modifier un contenu déjà publié
--     sans le renvoyer en validation.
create or replace function app.guard_chapter_access() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if new.is_free is distinct from old.is_free and (select auth.uid()) is not null and not app.can_publish() then
    raise exception 'Seul un responsable peut changer l''accès gratuit ou payant d''un chapitre' using errcode = '42501';
  end if;
  return new;
end $$;
create trigger chapters_guard_access before update of is_free on public.chapters
  for each row execute function app.guard_chapter_access();

create or replace function app.demote_on_edit() returns trigger
language plpgsql security definer set search_path = '' as $$
begin
  if old.status = 'published' and new.status = 'published' and (select auth.uid()) is not null and not app.can_publish()
     and (to_jsonb(old) - 'updated_at' - 'content_version') is distinct from (to_jsonb(new) - 'updated_at' - 'content_version') then
    new.status := 'in_review';
  end if;
  return new;
end $$;
do $$
declare t text;
begin
  foreach t in array array['chapters','lessons','medical_terms','quiz_questions','open_questions','flashcards'] loop
    execute format('create trigger %I before update on public.%I for each row execute function app.demote_on_edit()', t || '_demote', t);
  end loop;
end $$;

-- Le remplacement d'un chapitre existant supprime du contenu et des résultats d'étudiants : réservé aux responsables.
create or replace function app.guard_import_replace(p_discipline_slug text, p_slug text, p_replace boolean) returns void
language plpgsql security definer set search_path = '' as $$
begin
  if p_replace and (select auth.uid()) is not null and not app.can_publish()
     and exists (select 1 from public.chapters c join public.disciplines d on d.id = c.discipline_id
                 where d.slug = p_discipline_slug and c.slug = p_slug) then
    raise exception 'Seul un responsable peut remplacer un chapitre existant' using errcode = '42501';
  end if;
end $$;
alter function public.admin_import_chapter(text, jsonb, boolean, boolean) rename to admin_import_chapter_unchecked;
revoke execute on function public.admin_import_chapter_unchecked(text, jsonb, boolean, boolean) from public, anon, authenticated;
alter function public.admin_import_chapter_unchecked(text, jsonb, boolean, boolean) set schema app;
create or replace function public.admin_import_chapter(p_discipline_slug text, p_payload jsonb, p_is_free boolean default false, p_replace boolean default false)
returns jsonb language plpgsql security definer set search_path = '' as $$
begin
  if (select auth.uid()) is not null and not app.can_edit_content() then raise exception 'forbidden' using errcode = '42501'; end if;
  perform app.guard_import_replace(p_discipline_slug, p_payload ->> 'slug', p_replace);
  return app.admin_import_chapter_unchecked(p_discipline_slug, p_payload, p_is_free, p_replace);
end $$;
revoke execute on function public.admin_import_chapter(text, jsonb, boolean, boolean) from public, anon;
grant execute on function public.admin_import_chapter(text, jsonb, boolean, boolean) to authenticated;
revoke execute on function app.guard_import_replace(text, text, boolean) from public, anon, authenticated;

-- F4. Colonnes réellement modifiables par leur propriétaire.
revoke update on public.profiles from authenticated;
grant update (full_name, country_code, language_code, currency_code, study_field, study_level, curriculum_id, daily_goal_minutes)
  on public.profiles to authenticated;
revoke update on public.notifications from authenticated;
grant update (read_at) on public.notifications to authenticated;

-- F10. Export complet des données personnelles.
create or replace function public.export_my_data()
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare v_uid uuid := (select auth.uid());
begin
  if v_uid is null then raise exception 'not_authenticated' using errcode = '42501'; end if;
  return jsonb_build_object(
    'exported_at', now(),
    'profile', (select to_jsonb(p) from public.profiles p where p.id = v_uid),
    'roles', (select coalesce(jsonb_agg(r.role_code), '[]'::jsonb) from public.user_roles r where r.user_id = v_uid),
    'quiz_attempts', (select coalesce(jsonb_agg(to_jsonb(a) || jsonb_build_object('answers',
        (select coalesce(jsonb_agg(to_jsonb(x) - 'attempt_id'), '[]'::jsonb) from public.quiz_answers x where x.attempt_id = a.id))), '[]'::jsonb)
      from public.quiz_attempts a where a.user_id = v_uid),
    'puzzle_sessions', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.puzzle_sessions s where s.user_id = v_uid),
    'open_question_submissions', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.open_question_submissions s where s.user_id = v_uid),
    'flashcard_states', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.flashcard_states s where s.user_id = v_uid),
    'flashcard_reviews', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.flashcard_reviews s where s.user_id = v_uid),
    'user_progress', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.user_progress s where s.user_id = v_uid),
    'learning_sessions', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.learning_sessions s where s.user_id = v_uid),
    'bookmarks', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.bookmarks s where s.user_id = v_uid),
    'notifications', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.notifications s where s.user_id = v_uid),
    'subscriptions', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.subscriptions s where s.user_id = v_uid),
    'payments', (select coalesce(jsonb_agg(to_jsonb(p) - 'raw'), '[]'::jsonb) from public.payments p where p.user_id = v_uid));
end $$;
revoke execute on function public.export_my_data() from public, anon;
grant execute on function public.export_my_data() to authenticated;

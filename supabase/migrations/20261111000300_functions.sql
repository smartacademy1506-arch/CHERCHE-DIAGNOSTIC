-- CHERCHE & DIAGNOSTIC — fonctions appelées par l'application (RPC)
-- Toutes sont SECURITY DEFINER avec search_path vide et vérifient elles-mêmes les droits de l'appelant.

-- ───────────────────────── Tarification ─────────────────────────
-- Prix d'une offre dans une devise : prix fixé manuellement s'il existe, sinon conversion du prix USD arrondie.
create or replace function app.plan_amount(p_plan_id uuid, p_currency text) returns numeric
language sql stable security definer set search_path = '' as $$
  select coalesce(
    (select pp.amount from public.plan_prices pp where pp.plan_id = p_plan_id and pp.currency_code = p_currency),
    (select greatest(c.rounding, round(p.price_usd * c.usd_rate / c.rounding) * c.rounding)
     from public.plans p, public.currencies c
     where p.id = p_plan_id and c.code = p_currency and c.is_active));
$$;

create or replace function public.get_pricing(p_currency text default 'USD')
returns table (plan_id uuid, code text, billing_period text, price_usd numeric, currency_code text, amount numeric,
               name jsonb, description jsonb, features jsonb, is_featured boolean, sort int)
language sql stable security definer set search_path = '' as $$
  with cur as (
    select coalesce((select c.code from public.currencies c where c.code = upper(p_currency) and c.is_active), 'USD') as code)
  select p.id, p.code, p.billing_period, p.price_usd, cur.code, app.plan_amount(p.id, cur.code),
         p.name, p.description, p.features, p.is_featured, p.sort
  from public.plans p, cur where p.is_active order by p.sort;
$$;

-- ───────────────────────── Paiements et abonnements ─────────────────────────
create or replace function app.activate_subscription(p_user uuid, p_plan uuid, p_payment uuid, p_source text)
returns uuid language plpgsql security definer set search_path = '' as $$
declare v_period text; v_start timestamptz := now(); v_end timestamptz; v_id uuid;
begin
  select billing_period into v_period from public.plans where id = p_plan;
  if v_period is null then raise exception 'plan_not_found' using errcode = '22023'; end if;
  if v_period <> 'lifetime' then
    -- un renouvellement prolonge l'abonnement en cours au lieu de le chevaucher
    select greatest(now(), coalesce(max(s.ends_at), now())) into v_start
    from public.subscriptions s where s.user_id = p_user and s.status = 'active' and s.ends_at > now();
    v_end := v_start + case v_period when 'month' then interval '1 month' else interval '1 year' end;
  end if;
  insert into public.subscriptions(user_id, plan_id, payment_id, source, starts_at, ends_at)
  values (p_user, p_plan, p_payment, p_source, v_start, v_end) returning id into v_id;
  return v_id;
end $$;

-- L'utilisateur déclare son intention de payer : le montant est calculé côté serveur.
create or replace function public.create_payment_intent(p_plan_code text, p_currency text default 'USD')
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_uid uuid := (select auth.uid()); v_plan public.plans%rowtype; v_cur text; v_amount numeric; v_pay public.payments%rowtype;
begin
  if v_uid is null then raise exception 'not_authenticated' using errcode = '42501'; end if;
  select * into v_plan from public.plans where code = p_plan_code and is_active;
  if not found then raise exception 'plan_not_found' using errcode = '22023'; end if;
  select c.code into v_cur from public.currencies c where c.code = upper(p_currency) and c.is_active;
  if v_cur is null then v_cur := 'USD'; end if;
  v_amount := app.plan_amount(v_plan.id, v_cur);
  update public.payments set status = 'canceled' where user_id = v_uid and status = 'pending';
  insert into public.payments(user_id, plan_id, reference, amount, currency_code, amount_usd)
  values (v_uid, v_plan.id, 'CD-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 8)), v_amount, v_cur, v_plan.price_usd)
  returning * into v_pay;
  return jsonb_build_object('id', v_pay.id, 'reference', v_pay.reference, 'amount', v_pay.amount,
                            'currency_code', v_pay.currency_code, 'plan_code', v_plan.code, 'status', v_pay.status);
end $$;

-- Confirmation d'un paiement par un administrateur (ou, plus tard, par le webhook du prestataire de paiement).
create or replace function public.admin_confirm_payment(p_payment_id uuid, p_provider_ref text default null)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_pay public.payments%rowtype; v_sub uuid;
begin
  if not app.is_admin() then raise exception 'forbidden' using errcode = '42501'; end if;
  select * into v_pay from public.payments where id = p_payment_id for update;
  if not found then raise exception 'payment_not_found' using errcode = '22023'; end if;
  if v_pay.status = 'succeeded' then
    return jsonb_build_object('payment_id', v_pay.id, 'status', 'succeeded', 'already_confirmed', true);
  end if;
  if v_pay.status <> 'pending' or v_pay.user_id is null then raise exception 'payment_not_pending' using errcode = '22023'; end if;
  update public.payments set status = 'succeeded', confirmed_at = now(), confirmed_by = (select auth.uid()),
         provider_ref = coalesce(p_provider_ref, provider_ref) where id = p_payment_id;
  v_sub := app.activate_subscription(v_pay.user_id, v_pay.plan_id, v_pay.id, 'payment');
  return jsonb_build_object('payment_id', v_pay.id, 'status', 'succeeded', 'subscription_id', v_sub);
end $$;

create or replace function public.admin_grant_subscription(p_user_id uuid, p_plan_code text)
returns uuid language plpgsql security definer set search_path = '' as $$
declare v_plan uuid;
begin
  if not app.is_admin() then raise exception 'forbidden' using errcode = '42501'; end if;
  select id into v_plan from public.plans where code = p_plan_code;
  if v_plan is null then raise exception 'plan_not_found' using errcode = '22023'; end if;
  return app.activate_subscription(p_user_id, v_plan, null, 'admin_grant');
end $$;

-- ───────────────────────── QCM : correction côté serveur ─────────────────────────
-- p_answers = { "<question_id>": ["<option_id>", ...], ... }
-- Les bonnes réponses ne sont renvoyées que pour les questions soumises. Rejouer le même p_attempt_id
-- (resynchronisation hors ligne) renvoie le résultat déjà enregistré sans créer de doublon.
create or replace function public.submit_quiz_attempt(
  p_attempt_id uuid, p_chapter_id uuid, p_answers jsonb,
  p_duration_s int default null, p_mode text default 'practice', p_client_ts timestamptz default null)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_uid uuid := (select auth.uid());
  v_answers jsonb := p_answers;
  v_store boolean := false;
  v_existing public.quiz_attempts%rowtype;
  v_results jsonb := '[]'::jsonb;
  v_score int := 0; v_total int := 0;
  v_sel uuid[]; v_ok boolean; r record;
begin
  if p_attempt_id is null or p_chapter_id is null or p_answers is null or jsonb_typeof(p_answers) <> 'object' then
    raise exception 'invalid_arguments' using errcode = '22023';
  end if;
  if not app.can_access_chapter(p_chapter_id) then raise exception 'forbidden' using errcode = '42501'; end if;
  if v_uid is not null then
    select * into v_existing from public.quiz_attempts where id = p_attempt_id;
    if found then
      if v_existing.user_id <> v_uid or v_existing.chapter_id <> p_chapter_id then
        raise exception 'forbidden' using errcode = '42501';
      end if;
      select coalesce(jsonb_object_agg(a.question_id::text, to_jsonb(a.selected_option_ids)), '{}'::jsonb)
        into v_answers from public.quiz_answers a where a.attempt_id = p_attempt_id;
    else
      v_store := true;
    end if;
  end if;

  for r in
    select q.id, k.correct_option_ids, k.explanation,
           (select coalesce(array_agg(o.id), '{}') from public.quiz_options o where o.question_id = q.id) as option_ids
    from public.quiz_questions q join public.quiz_answer_keys k on k.question_id = q.id
    where q.chapter_id = p_chapter_id and app.content_visible(q.status) and v_answers ? q.id::text
    order by q.sort
  loop
    begin
      select coalesce(array_agg(distinct x::uuid), '{}') into v_sel
      from jsonb_array_elements_text(v_answers -> r.id::text) x where x::uuid = any (r.option_ids);
    exception when others then v_sel := '{}';
    end;
    v_ok := cardinality(v_sel) > 0 and v_sel <@ r.correct_option_ids and r.correct_option_ids <@ v_sel;
    v_total := v_total + 1;
    if v_ok then v_score := v_score + 1; end if;
    v_results := v_results || jsonb_build_object('question_id', r.id, 'selected', to_jsonb(v_sel),
      'correct', to_jsonb(r.correct_option_ids), 'is_correct', v_ok, 'explanation', r.explanation);
  end loop;
  if v_total = 0 then raise exception 'no_answers' using errcode = '22023'; end if;

  if v_store then
    insert into public.quiz_attempts(id, user_id, chapter_id, mode, score, total, duration_s, client_ts)
    values (p_attempt_id, v_uid, p_chapter_id,
            case when p_mode in ('practice', 'timed', 'exam') then p_mode else 'practice' end,
            v_score, v_total, greatest(p_duration_s, 0), p_client_ts);
    insert into public.quiz_answers(attempt_id, question_id, selected_option_ids, is_correct)
    select p_attempt_id, (e ->> 'question_id')::uuid,
           array(select jsonb_array_elements_text(e -> 'selected')::uuid), (e ->> 'is_correct')::boolean
    from jsonb_array_elements(v_results) e;
  end if;
  return jsonb_build_object('attempt_id', p_attempt_id, 'score', v_score, 'total', v_total,
                            'stored', v_uid is not null, 'results', v_results);
end $$;

-- Corrigés pour le mode hors ligne : réservés aux utilisateurs connectés ayant accès au chapitre.
create or replace function public.get_offline_keys(p_chapter_id uuid)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
begin
  if (select auth.uid()) is null or not app.can_access_chapter(p_chapter_id) then
    raise exception 'forbidden' using errcode = '42501';
  end if;
  return coalesce((
    select jsonb_object_agg(k.question_id::text, jsonb_build_object('correct', to_jsonb(k.correct_option_ids), 'explanation', k.explanation))
    from public.quiz_answer_keys k join public.quiz_questions q on q.id = k.question_id
    where q.chapter_id = p_chapter_id and app.content_visible(q.status)), '{}'::jsonb);
end $$;

-- ───────────────────────── Session : droits de l'utilisateur courant ─────────────────────────
create or replace function public.my_access()
returns jsonb language sql stable security definer set search_path = '' as $$
  select jsonb_build_object(
    'roles', coalesce((select jsonb_agg(ur.role_code) from public.user_roles ur where ur.user_id = (select auth.uid())), '[]'::jsonb),
    'premium', app.has_active_subscription(),
    'subscription', (select jsonb_build_object('plan_code', p.code, 'ends_at', s.ends_at, 'source', s.source)
                     from public.subscriptions s join public.plans p on p.id = s.plan_id
                     where s.user_id = (select auth.uid()) and s.status = 'active' and s.starts_at <= now()
                       and (s.ends_at is null or s.ends_at > now())
                     order by s.ends_at desc nulls first limit 1),
    'pilot', app.pilot_mode());
$$;

-- ───────────────────────── Administration ─────────────────────────
create or replace function public.admin_list_users(p_search text default null, p_limit int default 50, p_offset int default 0)
returns table (id uuid, email text, full_name text, country_code text, created_at timestamptz, roles text[], plan_code text, ends_at timestamptz)
language plpgsql stable security definer set search_path = '' as $$
begin
  if not app.is_admin() then raise exception 'forbidden' using errcode = '42501'; end if;
  return query
  select u.id, u.email::text, p.full_name, p.country_code, u.created_at,
         array(select ur.role_code from public.user_roles ur where ur.user_id = u.id order by 1),
         sub.code, sub.ends_at
  from auth.users u
  left join public.profiles p on p.id = u.id
  left join lateral (
    select pl.code, s.ends_at from public.subscriptions s join public.plans pl on pl.id = s.plan_id
    where s.user_id = u.id and s.status = 'active' and (s.ends_at is null or s.ends_at > now())
    order by s.ends_at desc nulls first limit 1) sub on true
  where p_search is null or u.email ilike '%' || p_search || '%' or p.full_name ilike '%' || p_search || '%'
  order by u.created_at desc
  limit least(greatest(p_limit, 1), 200) offset greatest(p_offset, 0);
end $$;

create or replace function public.admin_set_role(p_user_id uuid, p_role text, p_grant boolean)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if not app.is_admin() then raise exception 'forbidden' using errcode = '42501'; end if;
  if p_grant then
    insert into public.user_roles(user_id, role_code) values (p_user_id, p_role) on conflict do nothing;
  else
    if p_user_id = (select auth.uid()) and p_role = 'super_admin' then
      raise exception 'Vous ne pouvez pas retirer votre propre rôle de super administrateur' using errcode = '42501';
    end if;
    delete from public.user_roles where user_id = p_user_id and role_code = p_role;
  end if;
end $$;

create or replace function public.admin_stats()
returns jsonb language plpgsql stable security definer set search_path = '' as $$
begin
  if not app.is_staff() then raise exception 'forbidden' using errcode = '42501'; end if;
  return jsonb_build_object(
    'users', (select count(*) from public.profiles),
    'users_7d', (select count(*) from public.profiles where created_at > now() - interval '7 days'),
    'active_subscriptions', (select count(distinct user_id) from public.subscriptions where status = 'active' and (ends_at is null or ends_at > now())),
    'pending_payments', (select count(*) from public.payments where status = 'pending'),
    'quiz_attempts_7d', (select count(*) from public.quiz_attempts where submitted_at > now() - interval '7 days'),
    'puzzle_sessions_7d', (select count(*) from public.puzzle_sessions where updated_at > now() - interval '7 days'),
    'chapters', (select coalesce(jsonb_object_agg(status, n), '{}'::jsonb) from (select status, count(*) n from public.chapters group by status) s),
    'terms', (select count(*) from public.medical_terms),
    'questions', (select count(*) from public.quiz_questions),
    'puzzles_validated', (select count(*) from public.word_search_puzzles where validated_at is not null));
end $$;

-- Import d'un chapitre complet au format content/SPEC.md (+ grilles générées et vérifiées par l'outil).
-- Le contenu importé entre toujours en « in_review » : la publication reste une décision humaine.
create or replace function public.admin_import_chapter(p_discipline_slug text, p_payload jsonb, p_is_free boolean default false, p_replace boolean default false)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_disc uuid; v_ch uuid; v_existing boolean; v_term_ids uuid[] := '{}'; v_id uuid; v_q uuid; v_opt uuid; v_correct uuid[];
  v_puz uuid; t record; q record; o record; w record; lang text; v_title jsonb := p_payload -> 'title';
begin
  if (select auth.uid()) is not null and not app.can_edit_content() then raise exception 'forbidden' using errcode = '42501'; end if;
  select id into v_disc from public.disciplines where slug = p_discipline_slug;
  if v_disc is null then raise exception 'discipline_not_found' using errcode = '22023'; end if;
  if coalesce(p_payload ->> 'slug', '') = '' or v_title is null then raise exception 'invalid_payload' using errcode = '22023'; end if;

  select id into v_ch from public.chapters where discipline_id = v_disc and slug = p_payload ->> 'slug';
  v_existing := v_ch is not null;
  if v_existing and exists (select 1 from public.medical_terms where chapter_id = v_ch) then
    if not p_replace then raise exception 'chapter_exists : relancer avec p_replace pour remplacer son contenu' using errcode = '23505'; end if;
    delete from public.word_search_puzzles where chapter_id = v_ch;
    delete from public.lessons where chapter_id = v_ch;
    delete from public.learning_objectives where chapter_id = v_ch;
    delete from public.quiz_questions where chapter_id = v_ch;
    delete from public.open_questions where chapter_id = v_ch;
    delete from public.medical_terms where chapter_id = v_ch;
  end if;
  if v_existing then
    update public.chapters set title = v_title, description = coalesce(p_payload -> 'description', '{}'::jsonb),
           sort = coalesce((p_payload ->> 'order')::int, sort), is_free = p_is_free where id = v_ch;
  else
    insert into public.chapters(discipline_id, slug, title, description, sort, is_free, status)
    values (v_disc, p_payload ->> 'slug', v_title, coalesce(p_payload -> 'description', '{}'::jsonb),
            coalesce((p_payload ->> 'order')::int, 0), p_is_free, 'in_review') returning id into v_ch;
  end if;

  insert into public.lessons(chapter_id, title, summary, key_points, source_refs, status)
  values (v_ch, v_title, p_payload -> 'summary', coalesce(p_payload -> 'key_points', '[]'::jsonb),
          coalesce(p_payload -> 'references', '[]'::jsonb), 'in_review');
  insert into public.learning_objectives(chapter_id, body, sort)
  select v_ch, e.value, e.ordinality from jsonb_array_elements(coalesce(p_payload -> 'objectives', '[]'::jsonb)) with ordinality e;

  for t in select e.value, e.ordinality from jsonb_array_elements(coalesce(p_payload -> 'terms', '[]'::jsonb)) with ordinality e loop
    insert into public.medical_terms(chapter_id, label, sort, status)
    values (v_ch, jsonb_build_object('fr', t.value ->> 'fr', 'en', t.value ->> 'en'), t.ordinality, 'in_review') returning id into v_id;
    v_term_ids := v_term_ids || v_id;
    insert into public.glossary_entries(term_id, definition) values (v_id, t.value -> 'definition');
    insert into public.flashcards(chapter_id, term_id, front, back, sort, status)
    values (v_ch, v_id, jsonb_build_object('fr', t.value ->> 'fr', 'en', t.value ->> 'en'), t.value -> 'definition', t.ordinality, 'in_review');
  end loop;

  for q in select e.value, e.ordinality from jsonb_array_elements(coalesce(p_payload -> 'quiz', '[]'::jsonb)) with ordinality e loop
    insert into public.quiz_questions(chapter_id, type, difficulty, stem, sort, status)
    values (v_ch, q.value ->> 'type', coalesce((q.value ->> 'difficulty')::int, 2), q.value -> 'stem', q.ordinality, 'in_review') returning id into v_q;
    v_correct := '{}';
    for o in select e.value, e.ordinality from jsonb_array_elements(q.value -> 'options') with ordinality e loop
      insert into public.quiz_options(question_id, label, sort)
      values (v_q, jsonb_build_object('fr', o.value ->> 'fr', 'en', o.value ->> 'en'), o.ordinality) returning id into v_opt;
      if (o.value ->> 'correct')::boolean then v_correct := v_correct || v_opt; end if;
    end loop;
    insert into public.quiz_answer_keys(question_id, correct_option_ids, explanation) values (v_q, v_correct, coalesce(q.value -> 'explanation', '{}'::jsonb));
  end loop;

  insert into public.open_questions(chapter_id, question, model_answer, sort, status)
  select v_ch, e.value -> 'question', e.value -> 'model_answer', e.ordinality, 'in_review'
  from jsonb_array_elements(coalesce(p_payload -> 'open_questions', '[]'::jsonb)) with ordinality e;

  for lang in select jsonb_object_keys(coalesce(p_payload -> 'puzzles', '{}'::jsonb)) loop
    insert into public.word_search_puzzles(chapter_id, language_code, size, grid, seed, directions, status)
    values (v_ch, lang, (p_payload -> 'puzzles' -> lang ->> 'size')::int,
            array(select jsonb_array_elements_text(p_payload -> 'puzzles' -> lang -> 'grid')),
            (p_payload -> 'puzzles' -> lang ->> 'seed')::bigint,
            coalesce((p_payload -> 'puzzles' -> lang ->> 'directions')::int, 8), 'draft') returning id into v_puz;
    for w in select e.value from jsonb_array_elements(p_payload -> 'puzzles' -> lang -> 'words') e loop
      insert into public.puzzle_words(puzzle_id, term_id, word, start_row, start_col, d_row, d_col)
      values (v_puz, v_term_ids[(w.value ->> 'term_index')::int + 1], w.value ->> 'word',
              (w.value ->> 'row')::int, (w.value ->> 'col')::int, (w.value ->> 'd_row')::int, (w.value ->> 'd_col')::int);
    end loop;
    -- le passage en « in_review » déclenche la vérification de la grille ; toute erreur annule l'import entier
    update public.word_search_puzzles set status = 'in_review' where id = v_puz;
  end loop;

  return jsonb_build_object('chapter_id', v_ch, 'terms', cardinality(v_term_ids),
    'questions', (select count(*) from public.quiz_questions where chapter_id = v_ch),
    'puzzles', (select count(*) from public.word_search_puzzles where chapter_id = v_ch and validated_at is not null));
end $$;

-- ───────────────────────── Données personnelles ─────────────────────────
create or replace function public.export_my_data()
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare v_uid uuid := (select auth.uid());
begin
  if v_uid is null then raise exception 'not_authenticated' using errcode = '42501'; end if;
  return jsonb_build_object(
    'exported_at', now(),
    'profile', (select to_jsonb(p) from public.profiles p where p.id = v_uid),
    'quiz_attempts', (select coalesce(jsonb_agg(to_jsonb(a)), '[]'::jsonb) from public.quiz_attempts a where a.user_id = v_uid),
    'puzzle_sessions', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.puzzle_sessions s where s.user_id = v_uid),
    'open_question_submissions', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.open_question_submissions s where s.user_id = v_uid),
    'flashcard_states', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.flashcard_states s where s.user_id = v_uid),
    'learning_sessions', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.learning_sessions s where s.user_id = v_uid),
    'subscriptions', (select coalesce(jsonb_agg(to_jsonb(s)), '[]'::jsonb) from public.subscriptions s where s.user_id = v_uid),
    'payments', (select coalesce(jsonb_agg(to_jsonb(p) - 'raw'), '[]'::jsonb) from public.payments p where p.user_id = v_uid));
end $$;

create or replace function public.delete_my_account()
returns void language plpgsql security definer set search_path = '' as $$
declare v_uid uuid := (select auth.uid());
begin
  if v_uid is null then raise exception 'not_authenticated' using errcode = '42501'; end if;
  delete from auth.users where id = v_uid;
end $$;

-- ───────────────────────── Droits d'exécution ─────────────────────────
revoke execute on all functions in schema public from public, anon, authenticated;
grant execute on function public.get_pricing(text) to anon, authenticated;
grant execute on function public.submit_quiz_attempt(uuid, uuid, jsonb, int, text, timestamptz) to anon, authenticated;
grant execute on function public.my_access() to authenticated;
grant execute on function public.get_offline_keys(uuid) to authenticated;
grant execute on function public.create_payment_intent(text, text) to authenticated;
grant execute on function public.admin_confirm_payment(uuid, text) to authenticated;
grant execute on function public.admin_grant_subscription(uuid, text) to authenticated;
grant execute on function public.admin_list_users(text, int, int) to authenticated;
grant execute on function public.admin_set_role(uuid, text, boolean) to authenticated;
grant execute on function public.admin_stats() to authenticated;
grant execute on function public.admin_import_chapter(text, jsonb, boolean, boolean) to authenticated;
grant execute on function public.export_my_data() to authenticated;
grant execute on function public.delete_my_account() to authenticated;

revoke execute on all functions in schema app from public;
grant execute on all functions in schema app to anon, authenticated, service_role;
revoke execute on function app.activate_subscription(uuid, uuid, uuid, text) from anon, authenticated;

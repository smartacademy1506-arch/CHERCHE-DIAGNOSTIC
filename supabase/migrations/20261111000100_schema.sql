-- CHERCHE & DIAGNOSTIC — schéma principal
-- Conventions :
--   * textes traduisibles = jsonb {"fr": "...", "en": "...", ...} (une clé par langue de contenu)
--   * statut éditorial = draft | in_review | published | archived
--   * identifiants des résultats (tentatives, sessions) générés côté client => synchronisation idempotente

create schema if not exists app;

-- ───────────────────────── Référentiels ─────────────────────────
create table public.languages (
  code text primary key check (code ~ '^[a-z]{2}$'),
  name text not null,
  native_name text not null,
  is_ui_language boolean not null default true,
  is_content_language boolean not null default false,
  is_active boolean not null default true,
  sort int not null default 0
);

create table public.currencies (
  code text primary key check (code ~ '^[A-Z]{3}$'),
  name text not null,
  symbol text not null,
  usd_rate numeric(18,6) not null check (usd_rate > 0),   -- unités de la devise pour 1 USD
  decimals smallint not null default 2 check (decimals between 0 and 3),
  rounding numeric(12,2) not null default 0.01 check (rounding > 0), -- pas d'arrondi des prix affichés
  is_active boolean not null default true,
  rate_updated_at timestamptz not null default now()
);

create table public.countries (
  code text primary key check (code ~ '^[A-Z]{2}$'),
  name jsonb not null,
  currency_code text not null references public.currencies(code) on update cascade on delete restrict,
  default_language text not null references public.languages(code) on update cascade on delete restrict,
  is_active boolean not null default true
);
create index countries_currency_idx on public.countries(currency_code);

create table public.curricula (
  id uuid primary key default gen_random_uuid(),
  country_code text references public.countries(code) on delete set null,
  code text not null unique,
  name jsonb not null,
  levels jsonb not null default '[]'::jsonb,   -- niveaux d'étude du programme
  is_active boolean not null default true
);

create table public.app_settings (
  key text primary key,
  value jsonb not null,
  is_public boolean not null default false,
  updated_at timestamptz not null default now()
);

-- ───────────────────────── Utilisateurs et rôles ─────────────────────────
create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text check (char_length(full_name) <= 120),
  country_code text references public.countries(code) on delete set null,
  language_code text not null default 'fr' references public.languages(code),
  currency_code text references public.currencies(code) on delete set null,
  study_field text check (char_length(study_field) <= 60),
  study_level text check (char_length(study_level) <= 60),
  curriculum_id uuid references public.curricula(id) on delete set null,
  daily_goal_minutes int not null default 20 check (daily_goal_minutes between 5 and 240),
  consent_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.roles (
  code text primary key,
  name jsonb not null,
  rank int not null
);
create table public.permissions (
  code text primary key,
  description text not null
);
create table public.role_permissions (
  role_code text not null references public.roles(code) on delete cascade,
  permission_code text not null references public.permissions(code) on delete cascade,
  primary key (role_code, permission_code)
);
create table public.user_roles (
  user_id uuid not null references auth.users(id) on delete cascade,
  role_code text not null references public.roles(code) on delete restrict,
  granted_by uuid references auth.users(id) on delete set null,
  granted_at timestamptz not null default now(),
  primary key (user_id, role_code)
);
create index user_roles_role_idx on public.user_roles(role_code);

-- ───────────────────────── Catalogue pédagogique ─────────────────────────
create table public.disciplines (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  title jsonb not null,
  description jsonb not null default '{}'::jsonb,
  icon text not null default 'book',
  sort int not null default 0,
  status text not null default 'draft' check (status in ('draft','in_review','published','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.chapters (
  id uuid primary key default gen_random_uuid(),
  discipline_id uuid not null references public.disciplines(id) on delete restrict,
  parent_id uuid references public.chapters(id) on delete restrict,   -- sous-chapitre
  curriculum_id uuid references public.curricula(id) on delete set null,
  slug text not null check (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
  title jsonb not null,
  description jsonb not null default '{}'::jsonb,
  study_level text,
  sort int not null default 0,
  is_free boolean not null default false,
  status text not null default 'draft' check (status in ('draft','in_review','published','archived')),
  content_version int not null default 1,          -- incrémenté à chaque modification de contenu (cache hors ligne)
  last_verified_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (discipline_id, slug)
);
create index chapters_discipline_idx on public.chapters(discipline_id, sort);
create index chapters_parent_idx on public.chapters(parent_id);

create table public.lessons (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  title jsonb not null,
  summary jsonb not null,                       -- Markdown simple par langue
  key_points jsonb not null default '[]'::jsonb, -- [{fr,en}]
  source_refs jsonb not null default '[]'::jsonb, -- [{citation,url}]
  sort int not null default 0,
  status text not null default 'draft' check (status in ('draft','in_review','published','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index lessons_chapter_idx on public.lessons(chapter_id, sort);

create table public.learning_objectives (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  body jsonb not null,
  sort int not null default 0
);
create index learning_objectives_chapter_idx on public.learning_objectives(chapter_id, sort);

create table public.medical_terms (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  label jsonb not null,                          -- terme affiché par langue
  sort int not null default 0,
  status text not null default 'draft' check (status in ('draft','in_review','published','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index medical_terms_chapter_idx on public.medical_terms(chapter_id, sort);

create table public.glossary_entries (
  id uuid primary key default gen_random_uuid(),
  term_id uuid not null unique references public.medical_terms(id) on delete cascade,
  definition jsonb not null,
  source_refs jsonb not null default '[]'::jsonb,
  last_verified_at timestamptz,
  updated_at timestamptz not null default now()
);

-- ───────────────────────── Mots mêlés ─────────────────────────
create table public.word_search_puzzles (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  language_code text not null references public.languages(code),
  size smallint not null check (size between 8 and 30),
  grid text[] not null,                          -- une chaîne de `size` lettres par ligne
  seed bigint,
  directions smallint not null default 8 check (directions in (2,4,8)),
  status text not null default 'draft' check (status in ('draft','in_review','published','archived')),
  validated_at timestamptz,                      -- renseigné uniquement par app.validate_puzzle()
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (chapter_id, language_code),
  check (array_length(grid, 1) = size)
);

create table public.puzzle_words (
  id uuid primary key default gen_random_uuid(),
  puzzle_id uuid not null references public.word_search_puzzles(id) on delete cascade,
  term_id uuid not null references public.medical_terms(id) on delete cascade,
  word text not null check (word ~ '^[A-Z]{3,30}$'),   -- forme grille (sans accents ni espaces)
  start_row smallint not null check (start_row >= 0),
  start_col smallint not null check (start_col >= 0),
  d_row smallint not null check (d_row between -1 and 1),
  d_col smallint not null check (d_col between -1 and 1),
  check (d_row <> 0 or d_col <> 0),
  unique (puzzle_id, term_id),
  unique (puzzle_id, word)
);
create index puzzle_words_term_idx on public.puzzle_words(term_id);

create table public.puzzle_sessions (
  id uuid primary key,                           -- généré côté client
  user_id uuid not null references auth.users(id) on delete cascade,
  puzzle_id uuid not null references public.word_search_puzzles(id) on delete cascade,
  found_term_ids uuid[] not null default '{}',
  words_total smallint not null check (words_total > 0),
  elapsed_s int not null default 0 check (elapsed_s >= 0),
  completed boolean not null default false,
  started_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (coalesce(array_length(found_term_ids, 1), 0) <= words_total)
);
create index puzzle_sessions_user_idx on public.puzzle_sessions(user_id, updated_at desc);
create index puzzle_sessions_puzzle_idx on public.puzzle_sessions(puzzle_id);

-- ───────────────────────── QCM ─────────────────────────
create table public.quiz_questions (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  type text not null check (type in ('single','multiple')),
  difficulty smallint not null default 2 check (difficulty between 1 and 3),
  stem jsonb not null,
  media_asset_id uuid,
  sort int not null default 0,
  status text not null default 'draft' check (status in ('draft','in_review','published','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index quiz_questions_chapter_idx on public.quiz_questions(chapter_id, sort);

create table public.quiz_options (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references public.quiz_questions(id) on delete cascade,
  label jsonb not null,
  sort int not null default 0
);
create index quiz_options_question_idx on public.quiz_options(question_id, sort);

-- Bonnes réponses et explications : table séparée, jamais lisible par les clients.
create table public.quiz_answer_keys (
  question_id uuid primary key references public.quiz_questions(id) on delete cascade,
  correct_option_ids uuid[] not null check (array_length(correct_option_ids, 1) >= 1),
  explanation jsonb not null default '{}'::jsonb
);

create table public.quiz_attempts (
  id uuid primary key,                           -- généré côté client
  user_id uuid not null references auth.users(id) on delete cascade,
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  mode text not null default 'practice' check (mode in ('practice','timed','exam')),
  score smallint not null check (score >= 0),
  total smallint not null check (total > 0),
  duration_s int check (duration_s >= 0),
  client_ts timestamptz,
  submitted_at timestamptz not null default now(),
  check (score <= total)
);
create index quiz_attempts_user_idx on public.quiz_attempts(user_id, submitted_at desc);
create index quiz_attempts_chapter_idx on public.quiz_attempts(chapter_id);

create table public.quiz_answers (
  attempt_id uuid not null references public.quiz_attempts(id) on delete cascade,
  question_id uuid not null references public.quiz_questions(id) on delete cascade,
  selected_option_ids uuid[] not null default '{}',
  is_correct boolean not null,
  primary key (attempt_id, question_id)
);
create index quiz_answers_question_idx on public.quiz_answers(question_id);

-- ───────────────────────── Questions ouvertes ─────────────────────────
create table public.open_questions (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  question jsonb not null,
  model_answer jsonb,                            -- éléments de correction validés (null si aucun)
  sort int not null default 0,
  status text not null default 'draft' check (status in ('draft','in_review','published','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index open_questions_chapter_idx on public.open_questions(chapter_id, sort);

create table public.open_question_submissions (
  id uuid primary key,                           -- généré côté client
  user_id uuid not null references auth.users(id) on delete cascade,
  question_id uuid not null references public.open_questions(id) on delete cascade,
  answer text not null check (char_length(answer) between 1 and 6000),
  self_score smallint check (self_score between 0 and 3),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, question_id)
);
create index open_question_submissions_question_idx on public.open_question_submissions(question_id);

-- ───────────────────────── Flashcards et répétition espacée ─────────────────────────
create table public.flashcards (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  term_id uuid unique references public.medical_terms(id) on delete cascade,
  front jsonb not null,
  back jsonb not null,
  sort int not null default 0,
  status text not null default 'draft' check (status in ('draft','in_review','published','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index flashcards_chapter_idx on public.flashcards(chapter_id, sort);

create table public.flashcard_states (
  user_id uuid not null references auth.users(id) on delete cascade,
  flashcard_id uuid not null references public.flashcards(id) on delete cascade,
  ease numeric(4,2) not null default 2.50 check (ease between 1.30 and 3.00),
  interval_days int not null default 0 check (interval_days >= 0),
  repetitions int not null default 0 check (repetitions >= 0),
  due_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, flashcard_id)
);
create index flashcard_states_due_idx on public.flashcard_states(user_id, due_at);
create index flashcard_states_card_idx on public.flashcard_states(flashcard_id);

create table public.flashcard_reviews (
  id uuid primary key,                           -- généré côté client
  user_id uuid not null references auth.users(id) on delete cascade,
  flashcard_id uuid not null references public.flashcards(id) on delete cascade,
  rating smallint not null check (rating between 0 and 3),  -- 0 à revoir, 1 difficile, 2 bien, 3 facile
  reviewed_at timestamptz not null default now()
);
create index flashcard_reviews_user_idx on public.flashcard_reviews(user_id, reviewed_at desc);
create index flashcard_reviews_card_idx on public.flashcard_reviews(flashcard_id);

-- ───────────────────────── Cas cliniques (module activable après validation) ─────────────────────────
create table public.clinical_cases (
  id uuid primary key default gen_random_uuid(),
  chapter_id uuid references public.chapters(id) on delete set null,
  discipline_id uuid references public.disciplines(id) on delete set null,
  title jsonb not null,
  presentation jsonb not null,                   -- patient fictif, motif, antécédents, examen…
  discussion jsonb,
  conclusion jsonb,
  status text not null default 'draft' check (status in ('draft','in_review','published','archived')),
  validated_by uuid references auth.users(id) on delete set null,
  validated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index clinical_cases_chapter_idx on public.clinical_cases(chapter_id);
create index clinical_cases_discipline_idx on public.clinical_cases(discipline_id);

create table public.clinical_case_questions (
  id uuid primary key default gen_random_uuid(),
  case_id uuid not null references public.clinical_cases(id) on delete cascade,
  step int not null default 0,
  prompt jsonb not null,
  expected jsonb,
  sort int not null default 0
);
create index clinical_case_questions_case_idx on public.clinical_case_questions(case_id, sort);

-- ───────────────────────── Progression ─────────────────────────
create table public.user_progress (
  user_id uuid not null references auth.users(id) on delete cascade,
  chapter_id uuid not null references public.chapters(id) on delete cascade,
  lesson_read_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (user_id, chapter_id)
);
create index user_progress_chapter_idx on public.user_progress(chapter_id);

create table public.learning_sessions (
  id uuid primary key,                           -- généré côté client
  user_id uuid not null references auth.users(id) on delete cascade,
  chapter_id uuid references public.chapters(id) on delete set null,
  activity text not null check (activity in ('lesson','word_search','quiz','open_question','flashcards','glossary')),
  duration_s int not null check (duration_s between 0 and 86400),
  started_at timestamptz not null default now()
);
create index learning_sessions_user_idx on public.learning_sessions(user_id, started_at desc);
create index learning_sessions_chapter_idx on public.learning_sessions(chapter_id);

create table public.bookmarks (
  user_id uuid not null references auth.users(id) on delete cascade,
  entity_type text not null check (entity_type in ('chapter','term','question','flashcard')),
  entity_id uuid not null,
  created_at timestamptz not null default now(),
  primary key (user_id, entity_type, entity_id)
);

-- ───────────────────────── Offres, abonnements, paiements ─────────────────────────
create table public.plans (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name jsonb not null,
  description jsonb not null default '{}'::jsonb,
  features jsonb not null default '[]'::jsonb,   -- [{fr,en,…}]
  billing_period text not null check (billing_period in ('month','year','lifetime')),
  price_usd numeric(10,2) not null check (price_usd >= 0),
  is_active boolean not null default true,
  is_featured boolean not null default false,
  sort int not null default 0,
  updated_at timestamptz not null default now()
);

-- Prix fixé manuellement pour une devise (prioritaire sur la conversion automatique).
create table public.plan_prices (
  plan_id uuid not null references public.plans(id) on delete cascade,
  currency_code text not null references public.currencies(code) on update cascade on delete cascade,
  amount numeric(14,2) not null check (amount >= 0),
  primary key (plan_id, currency_code)
);
create index plan_prices_currency_idx on public.plan_prices(currency_code);

create table public.payments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete restrict,
  plan_id uuid not null references public.plans(id) on delete restrict,
  reference text not null unique,                -- référence courte communiquée à l'utilisateur
  amount numeric(14,2) not null check (amount >= 0),
  currency_code text not null references public.currencies(code) on update cascade,
  amount_usd numeric(10,2) not null,
  provider text not null default 'manual',
  provider_ref text,
  status text not null default 'pending' check (status in ('pending','succeeded','failed','refunded','canceled')),
  raw jsonb,
  created_at timestamptz not null default now(),
  confirmed_at timestamptz,
  confirmed_by uuid references auth.users(id) on delete set null
);
create index payments_user_idx on public.payments(user_id, created_at desc);
create index payments_plan_idx on public.payments(plan_id);
create index payments_status_idx on public.payments(status);
create unique index payments_provider_ref_idx on public.payments(provider, provider_ref) where provider_ref is not null;

create table public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  plan_id uuid not null references public.plans(id) on delete restrict,
  payment_id uuid unique references public.payments(id) on delete set null,
  status text not null default 'active' check (status in ('active','expired','canceled')),
  source text not null default 'payment' check (source in ('payment','admin_grant','institution')),
  starts_at timestamptz not null default now(),
  ends_at timestamptz,                           -- null = accès à vie
  created_at timestamptz not null default now(),
  check (ends_at is null or ends_at > starts_at)
);
create index subscriptions_user_idx on public.subscriptions(user_id, status, ends_at);
create index subscriptions_plan_idx on public.subscriptions(plan_id);

-- ───────────────────────── Transverse ─────────────────────────
create table public.media_assets (
  id uuid primary key default gen_random_uuid(),
  storage_path text not null unique,
  mime_type text not null,
  alt jsonb not null default '{}'::jsonb,
  credit text,
  license text,
  uploaded_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now()
);
alter table public.quiz_questions
  add constraint quiz_questions_media_fk foreign key (media_asset_id) references public.media_assets(id) on delete set null;
create index quiz_questions_media_idx on public.quiz_questions(media_asset_id);

create table public.content_versions (
  id bigint generated always as identity primary key,
  entity_type text not null,
  entity_id uuid not null,
  snapshot jsonb not null,                       -- état AVANT modification
  changed_by uuid references auth.users(id) on delete set null,
  created_at timestamptz not null default now()
);
create index content_versions_entity_idx on public.content_versions(entity_type, entity_id, created_at desc);

create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title jsonb not null,
  body jsonb not null default '{}'::jsonb,
  read_at timestamptz,
  created_at timestamptz not null default now()
);
create index notifications_user_idx on public.notifications(user_id, created_at desc);

create table public.audit_logs (
  id bigint generated always as identity primary key,
  actor_id uuid references auth.users(id) on delete set null,
  action text not null,
  entity_type text not null,
  entity_id text,
  details jsonb,
  created_at timestamptz not null default now()
);
create index audit_logs_created_idx on public.audit_logs(created_at desc);
create index audit_logs_actor_idx on public.audit_logs(actor_id);

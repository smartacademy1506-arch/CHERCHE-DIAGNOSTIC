-- Premier contenu : les huit livres de la collection CHERCHE ET DIAGNOSTIQUE (12/11/2026).
-- Chaque volume d'anatomie devient une discipline ; la discipline « Anatomie », vide, est archivée.
-- Les quatre chapitres de physiologie rédigés par IA le 11/11 sont archivés (non supprimés) :
-- le livre Physiologie générale les remplace comme source principale.

update public.disciplines set sort = sort + 5 where sort >= 2;

insert into public.disciplines(slug, title, icon, sort, status) values
  ('anatomie-osteologie', '{"fr":"Anatomie — Ostéologie","en":"Anatomy — Osteology","es":"Anatomía — Osteología","zh":"解剖学 — 骨学"}', 'bone', 2, 'published'),
  ('anatomie-myologie', '{"fr":"Anatomie — Myologie","en":"Anatomy — Myology","es":"Anatomía — Miología","zh":"解剖学 — 肌学"}', 'bone', 3, 'published'),
  ('anatomie-innervation', '{"fr":"Anatomie — Innervation","en":"Anatomy — Innervation","es":"Anatomía — Inervación","zh":"解剖学 — 神经分布"}', 'bone', 4, 'published'),
  ('anatomie-vascularisation', '{"fr":"Anatomie — Vascularisation","en":"Anatomy — Vascularisation","es":"Anatomía — Vascularización","zh":"解剖学 — 血管分布"}', 'bone', 5, 'published'),
  ('anatomie-organes', '{"fr":"Anatomie — Organes","en":"Anatomy — Organs","es":"Anatomía — Órganos","zh":"解剖学 — 器官"}', 'bone', 6, 'published')
on conflict (slug) do nothing;

update public.disciplines set status = 'archived'
where slug = 'anatomie' and not exists (
  select 1 from public.chapters c where c.discipline_id = public.disciplines.id and c.status <> 'archived');

update public.chapters c set status = 'archived'
from public.disciplines d
where d.id = c.discipline_id and d.slug = 'physiologie'
  and c.slug in ('physiologie-cellulaire', 'physiologie-cardiovasculaire', 'physiologie-respiratoire', 'physiologie-renale');

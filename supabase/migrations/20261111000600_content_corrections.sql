-- Corrections issues de la relecture médicale indépendante (docs/06_VALIDATION/REVUES_INDEPENDANTES.md).
-- Chapitre 2 : volume télédiastolique cohérent avec la fraction d'éjection annoncée (OpenStax A&P 2e, 19.4).
update public.lessons l
set summary = jsonb_build_object(
  'fr', replace(l.summary ->> 'fr', 'environ 120 à 130 mL en fin de diastole', 'environ 120 mL en fin de diastole'),
  'en', replace(l.summary ->> 'en', 'about 120 to 130 mL at the end of diastole', 'about 120 mL at the end of diastole'))
from public.chapters c
where c.id = l.chapter_id and c.slug = 'physiologie-cardiovasculaire';

-- Chapitre 4 : auteurs non vérifiables retirés de la référence StatPearls « Anion Gap ».
update public.lessons l
set source_refs = (
  select jsonb_agg(case when r ->> 'citation' like '%Biochemistry, Anion Gap%'
                        then jsonb_set(r, '{citation}', to_jsonb('StatPearls. Biochemistry, Anion Gap. Treasure Island (FL): StatPearls Publishing.'::text))
                        else r end order by n)
  from jsonb_array_elements(l.source_refs) with ordinality as x(r, n))
from public.chapters c
where c.id = l.chapter_id and c.slug = 'physiologie-renale';

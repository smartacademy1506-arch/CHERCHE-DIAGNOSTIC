#!/usr/bin/env node
// Valide un ou plusieurs fichiers de contenu (voir content/SPEC.md).
// Usage : node tools/validate-content.mjs content/physiologie/*.json
import { readFileSync } from 'node:fs';

export function gridForm(term) {
  return term
    .toUpperCase()
    .replace(/Œ/g, 'OE')
    .replace(/Æ/g, 'AE')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[\s\-'’.]/g, '');
}

const words = (s) => s.trim().split(/\s+/).filter(Boolean).length;
const isBi = (o) => o && typeof o.fr === 'string' && typeof o.en === 'string' && o.fr.trim() && o.en.trim();

export function validateChapter(c) {
  const errors = [];
  const err = (m) => errors.push(m);
  if (!/^[a-z0-9]+(-[a-z0-9]+)*$/.test(c.slug || '')) err('slug invalide');
  if (!Number.isInteger(c.order)) err('order manquant');
  for (const k of ['title', 'description', 'summary']) if (!isBi(c[k])) err(`${k} : fr/en requis`);
  if (isBi(c.summary)) {
    for (const l of ['fr', 'en']) {
      const n = words(c.summary[l]);
      if (n < 300 || n > 560) err(`summary.${l} : ${n} mots (attendu 350-500)`);
    }
  }
  const exact = (arr, n, name) => {
    if (!Array.isArray(arr) || arr.length !== n) err(`${name} : ${arr?.length ?? 0} éléments (attendu ${n})`);
  };
  exact(c.objectives, 5, 'objectives');
  exact(c.key_points, 6, 'key_points');
  exact(c.terms, 40, 'terms');
  exact(c.quiz, 12, 'quiz');
  exact(c.open_questions, 5, 'open_questions');
  for (const [i, o] of (c.objectives || []).entries()) if (!isBi(o)) err(`objectives[${i}] : fr/en requis`);
  for (const [i, o] of (c.key_points || []).entries()) if (!isBi(o)) err(`key_points[${i}] : fr/en requis`);

  for (const lang of ['fr', 'en']) {
    const forms = [];
    for (const [i, t] of (c.terms || []).entries()) {
      if (typeof t[lang] !== 'string' || !t[lang].trim()) { err(`terms[${i}].${lang} manquant`); continue; }
      if (t[lang] !== t[lang].toUpperCase()) err(`terms[${i}].${lang} « ${t[lang]} » doit être en majuscules`);
      const g = gridForm(t[lang]);
      if (!/^[A-Z]+$/.test(g)) err(`terms[${i}].${lang} « ${t[lang]} » : caractères non autorisés (${g})`);
      if (g.length < 4 || g.length > 14) err(`terms[${i}].${lang} « ${t[lang]} » : ${g.length} lettres (4-14)`);
      if (g === [...g].reverse().join('')) err(`terms[${i}].${lang} « ${t[lang]} » : palindrome`);
      forms.push(g);
    }
    forms.forEach((a, i) => forms.forEach((b, j) => {
      if (i !== j && b.includes(a)) err(`terms.${lang} : « ${a} » est contenu dans « ${b} »${a === b ? ' (doublon)' : ''}`);
    }));
  }
  for (const [i, t] of (c.terms || []).entries()) {
    if (!isBi(t.definition)) { err(`terms[${i}].definition : fr/en requis`); continue; }
    for (const l of ['fr', 'en']) {
      const n = words(t.definition[l]);
      if (n < 10 || n > 55) err(`terms[${i}].definition.${l} : ${n} mots (15-45)`);
    }
  }

  let multi = 0;
  for (const [i, q] of (c.quiz || []).entries()) {
    if (!['single', 'multiple'].includes(q.type)) err(`quiz[${i}].type invalide`);
    if (![1, 2, 3].includes(q.difficulty)) err(`quiz[${i}].difficulty invalide`);
    if (!isBi(q.stem)) err(`quiz[${i}].stem : fr/en requis`);
    if (!isBi(q.explanation)) err(`quiz[${i}].explanation : fr/en requis`);
    const opts = q.options || [];
    if (opts.length < 4 || opts.length > 5) err(`quiz[${i}] : ${opts.length} options (4-5)`);
    for (const [j, o] of opts.entries()) {
      if (!isBi(o)) err(`quiz[${i}].options[${j}] : fr/en requis`);
      if (typeof o.correct !== 'boolean') err(`quiz[${i}].options[${j}].correct doit être booléen`);
    }
    const nc = opts.filter((o) => o.correct === true).length;
    if (q.type === 'single' && nc !== 1) err(`quiz[${i}] (single) : ${nc} bonnes réponses (attendu 1)`);
    if (q.type === 'multiple') { multi++; if (nc < 2 || nc > 3) err(`quiz[${i}] (multiple) : ${nc} bonnes réponses (2-3)`); }
    for (const l of ['fr', 'en']) {
      const set = new Set(opts.map((o) => (o[l] || '').trim().toLowerCase()));
      if (set.size !== opts.length) err(`quiz[${i}] : options ${l} en double`);
    }
  }
  if (multi < 3) err(`quiz : ${multi} questions "multiple" (au moins 3)`);

  for (const [i, q] of (c.open_questions || []).entries()) {
    if (!isBi(q.question)) err(`open_questions[${i}].question : fr/en requis`);
    if (!isBi(q.model_answer)) err(`open_questions[${i}].model_answer : fr/en requis`);
  }
  if (!Array.isArray(c.references) || c.references.length < 3) err('references : au moins 3');
  for (const [i, r] of (c.references || []).entries()) {
    if (!r.citation) err(`references[${i}].citation manquante`);
    if (typeof r.url !== 'string') err(`references[${i}].url doit être une chaîne (vide si aucune)`);
  }
  return errors;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  let bad = 0;
  for (const f of process.argv.slice(2)) {
    let c;
    try { c = JSON.parse(readFileSync(f, 'utf8')); } catch (e) { console.log(`ERREUR ${f} : JSON invalide — ${e.message}`); bad++; continue; }
    const errors = validateChapter(c);
    if (errors.length) { bad++; console.log(`ERREUR ${f}\n  - ${errors.join('\n  - ')}`); }
    else console.log(`OK ${f}`);
  }
  process.exit(bad ? 1 : 0);
}

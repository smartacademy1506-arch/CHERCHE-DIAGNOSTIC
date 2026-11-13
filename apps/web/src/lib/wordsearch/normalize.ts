// Forme « grille » d'un terme : majuscules, sans accents, sans espaces ni ponctuation.
// Doit rester identique à app.grid_form() (SQL) et à tools/validate-content.mjs.
export function gridForm(term: string): string {
  return term
    .toUpperCase()
    .replace(/Œ/g, 'OE')
    .replace(/Æ/g, 'AE')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^A-Z]/g, '');
}

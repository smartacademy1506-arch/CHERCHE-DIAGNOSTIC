// Valeurs publiques par conception : l'URL du projet et la clé « publishable » sont protégées par le RLS.
// Aucune clé secrète ne doit figurer dans ce dossier.
declare const __SUPABASE_URL__: string | undefined;
declare const __SUPABASE_KEY__: string | undefined;
declare const __APP_VERSION__: string | undefined;

export const SUPABASE_URL =
  (typeof __SUPABASE_URL__ !== 'undefined' && __SUPABASE_URL__) || 'https://ukhcfzecjhbkiftoaeup.supabase.co';
export const SUPABASE_KEY =
  (typeof __SUPABASE_KEY__ !== 'undefined' && __SUPABASE_KEY__) || 'sb_publishable_Z_aU-eYUzILDTwcBYrTqtw_escTcTq9';
export const APP_VERSION = (typeof __APP_VERSION__ !== 'undefined' && __APP_VERSION__) || 'dev';

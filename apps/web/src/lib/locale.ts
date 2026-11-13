// Détection du pays et de la langue par défaut. Le choix de l'utilisateur reste toujours prioritaire.
export const UI_LANGS = ['fr', 'en', 'es', 'zh'] as const;
export type Lang = (typeof UI_LANGS)[number];

const TZ_COUNTRY: Record<string, string> = {
  'Africa/Douala': 'CM', 'Africa/Libreville': 'GA', 'Africa/Brazzaville': 'CG', 'Africa/Ndjamena': 'TD', 'Africa/Bangui': 'CF',
  'Africa/Malabo': 'GQ', 'Africa/Dakar': 'SN', 'Africa/Abidjan': 'CI', 'Africa/Bamako': 'ML', 'Africa/Ouagadougou': 'BF',
  'Africa/Porto-Novo': 'BJ', 'Africa/Lome': 'TG', 'Africa/Niamey': 'NE', 'Africa/Conakry': 'GN', 'Africa/Kinshasa': 'CD',
  'Indian/Antananarivo': 'MG', 'Africa/Casablanca': 'MA', 'Africa/Algiers': 'DZ', 'Africa/Tunis': 'TN', 'Africa/Lagos': 'NG',
  'Africa/Accra': 'GH', 'Africa/Nairobi': 'KE', 'Africa/Johannesburg': 'ZA', 'Africa/Kigali': 'RW', 'Africa/Dar_es_Salaam': 'TZ',
  'Africa/Cairo': 'EG', 'Europe/Paris': 'FR', 'Europe/Brussels': 'BE', 'Europe/Zurich': 'CH', 'Europe/Berlin': 'DE',
  'Europe/Madrid': 'ES', 'Europe/London': 'GB', 'Europe/Rome': 'IT', 'Europe/Lisbon': 'PT', 'Europe/Amsterdam': 'NL',
  'America/New_York': 'US', 'America/Chicago': 'US', 'America/Los_Angeles': 'US', 'America/Toronto': 'CA', 'America/Montreal': 'CA',
  'America/Mexico_City': 'MX', 'America/Bogota': 'CO', 'America/Argentina/Buenos_Aires': 'AR', 'America/Lima': 'PE',
  'America/Santiago': 'CL', 'America/Sao_Paulo': 'BR', 'America/Port-au-Prince': 'HT', 'Asia/Shanghai': 'CN',
  'Asia/Kolkata': 'IN', 'Asia/Tokyo': 'JP', 'Australia/Sydney': 'AU',
};

/** Pays estimé : adresse IP (fonction /api/geo), sinon fuseau horaire, sinon région du navigateur. */
export async function detectCountry(): Promise<string | null> {
  try {
    const res = await fetch('/api/geo', { signal: AbortSignal.timeout(2500) });
    if (res.ok) {
      const { country } = await res.json();
      if (typeof country === 'string' && /^[A-Z]{2}$/.test(country)) return country;
    }
  } catch { /* hors ligne ou fonction absente */ }
  try {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (TZ_COUNTRY[tz]) return TZ_COUNTRY[tz];
  } catch { /* ignore */ }
  const region = (navigator.language || '').split('-')[1];
  return region && /^[A-Za-z]{2}$/.test(region) ? region.toUpperCase() : null;
}

export function browserLang(): Lang | null {
  for (const l of navigator.languages ?? [navigator.language]) {
    const code = (l || '').slice(0, 2).toLowerCase();
    if ((UI_LANGS as readonly string[]).includes(code)) return code as Lang;
  }
  return null;
}

/** Langue du contenu pédagogique : français ou anglais uniquement tant que les traductions médicales ne sont pas validées. */
export const contentLang = (ui: Lang): 'fr' | 'en' => (ui === 'fr' ? 'fr' : 'en');

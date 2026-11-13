/**
 * Thème d'affichage choisi par l'utilisateur : clair, sombre ou comme l'appareil.
 * Le choix est propre à l'appareil (clé locale `cd.theme`) et s'applique par l'attribut `data-theme` de <html> ;
 * sans attribut, la feuille de style suit `prefers-color-scheme`. Les couleurs viennent toutes des tokens
 * du design system (styles.css), aucune n'est fixée ici sauf celle de la barre du navigateur.
 */
export type ThemeChoice = 'system' | 'light' | 'dark';

const KEY = 'cd.theme';
const BAR = { light: '#012d69', dark: '#00112b' } as const;

export function readTheme(): ThemeChoice {
  try {
    const v = localStorage.getItem(KEY);
    return v === 'light' || v === 'dark' ? v : 'system';
  } catch { return 'system'; }
}

function systemDark(): boolean {
  return typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: dark)').matches;
}

/** Thème réellement affiché, une fois le choix « comme l'appareil » résolu. */
export function resolvedTheme(choice: ThemeChoice = readTheme()): 'light' | 'dark' {
  return choice === 'system' ? (systemDark() ? 'dark' : 'light') : choice;
}

function syncBarColor(): void {
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', BAR[resolvedTheme()]);
}

export function applyTheme(choice: ThemeChoice): void {
  const root = document.documentElement;
  if (choice === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', choice);
  syncBarColor();
}

export function saveTheme(choice: ThemeChoice): void {
  try {
    if (choice === 'system') localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, choice);
  } catch { /* stockage indisponible : le choix vaut pour la session */ }
  applyTheme(choice);
}

/** À appeler une fois au démarrage, avant le premier rendu. */
export function initTheme(): void {
  applyTheme(readTheme());
  if (typeof matchMedia === 'function') matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change', syncBarColor);
}

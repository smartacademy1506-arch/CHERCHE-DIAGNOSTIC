// Composants d'interface réutilisables.
import type { ButtonHTMLAttributes, ReactNode } from 'react';

const ICONS: Record<string, string> = {
  home: 'M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10',
  book: 'M4 5a2 2 0 012-2h13v16H6a2 2 0 00-2 2zM4 21V5M9 7h6',
  repeat: 'M17 2l4 4-4 4M3 11V9a3 3 0 013-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 01-3 3H3',
  chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  user: 'M12 12a4 4 0 100-8 4 4 0 000 8zM4 21a8 8 0 0116 0',
  lock: 'M6 11h12v10H6zM8 11V7a4 4 0 018 0v4',
  check: 'M4 12l5 5L20 6',
  download: 'M12 3v12M7 10l5 5 5-5M4 21h16',
  grid: 'M4 4h16v16H4zM4 9.3h16M4 14.6h16M9.3 4v16M14.6 4v16',
  cards: 'M3 7h13v13H3zM7 7V4h14v13h-3',
  edit: 'M4 20h4L20 8l-4-4L4 16zM14 6l4 4',
  list: 'M8 6h13M8 12h13M8 18h13M3.5 6h.01M3.5 12h.01M3.5 18h.01',
  quiz: 'M9 9a3 3 0 115 2.2c-.9.7-2 1.3-2 2.8M12 18h.01M3 3h18v18H3z',
  pause: 'M8 5v14M16 5v14',
  play: 'M7 4l13 8-13 8z',
  back: 'M15 5l-7 7 7 7',
  x: 'M5 5l14 14M19 5L5 19',
  clock: 'M12 7v5l3 2M12 21a9 9 0 100-18 9 9 0 000 18z',
  zoom: 'M11 18a7 7 0 100-14 7 7 0 000 14zM21 21l-5-5M11 8v6M8 11h6',
  globe: 'M12 21a9 9 0 100-18 9 9 0 000 18zM3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18',
  star: 'M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z',
  alert: 'M12 9v4M12 17h.01M10.3 3.9L2.4 18a2 2 0 001.7 3h15.8a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
  pulse: 'M2 12h4l3-8 4 16 3-8h6',
  bone: 'M17 3a3 3 0 00-2.8 4.1l-7.1 7.1A3 3 0 103 17a3 3 0 104 4 3 3 0 002.8-4.1l7.1-7.1A3 3 0 1021 7a3 3 0 10-4-4z',
  pill: 'M10.5 3.5a5 5 0 017 7l-7 7a5 5 0 01-7-7zM7 10l7 7',
  stethoscope: 'M6 3v6a4 4 0 008 0V3M10 13v3a5 5 0 0010 0v-3M20 13a2 2 0 100-4 2 2 0 000 4z',
};

export function Icon({ name, size = 20 }: { name: string; size?: number }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ICONS[name] ?? ICONS.book} />
    </svg>
  );
}

/** Variantes du design system : primaire (marine), secondaire (« soft »), discrète (« ghost »), danger, et « diagnostic » (rouge, une fois par écran, pour valider). */
type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'primary' | 'ghost' | 'danger' | 'soft' | 'diagnostic'; icon?: string; block?: boolean };
export function Button({ variant = 'primary', icon, block, children, className = '', ...rest }: BtnProps) {
  return (
    <button type="button" className={`btn btn-${variant}${block ? ' btn-block' : ''} ${className}`} {...rest}>
      {icon && <Icon name={icon} size={18} />}
      {children && <span>{children}</span>}
    </button>
  );
}

export function Card({ children, className = '', onClick, label }: { children: ReactNode; className?: string; onClick?: () => void; label?: string }) {
  if (onClick) return <button type="button" className={`card card-action ${className}`} onClick={onClick} aria-label={label}>{children}</button>;
  return <div className={`card ${className}`}>{children}</div>;
}

/** Maîtrise d'un chapitre : un chiffre lisible et une barre fine (pas d'anneau décoratif). */
export function Ring({ value, label }: { value: number; size?: number; label?: string }) {
  const v = Math.max(0, Math.min(1, value));
  return (
    <span className="meter" role="img" aria-label={label ?? `${Math.round(v * 100)} %`}>
      <span>{Math.round(v * 100)}<small>%</small></span>
      <span className="bar"><span style={{ display: 'block', height: '100%', width: `${v * 100}%`, background: 'currentColor', borderRadius: 3 }} /></span>
    </span>
  );
}

/** Logo du design system, en aplats (public/brand, généré par tools/brand/build_logo.py) ; version inverse en thème sombre. */
export function Logo({ variant = 'horizontal', className }: { variant?: 'horizontal' | 'vertical' | 'symbole'; className?: string }) {
  if (variant === 'vertical') return <img src="/brand/logo-vertical.svg" alt="Cherche & Diagnostic" width={1089} height={1146} className={className} />;
  if (variant === 'symbole') return <img src="/brand/symbole.svg" alt="Cherche & Diagnostic" width={814} height={747} className={className} />;
  return (
    <picture className={className}>
      <source srcSet="/brand/logo-horizontal-inverse.svg" media="(prefers-color-scheme: dark)" />
      <img src="/brand/logo-horizontal.svg" alt="Cherche & Diagnostic" width={887} height={240} />
    </picture>
  );
}

/** Badge du design system : pastille, étiquette en capitales. */
export function Badge({ tone = 'ciel', children }: { tone?: 'ciel' | 'marine' | 'succes' | 'alerte' | 'danger' | 'neutre'; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function Bar({ value }: { value: number }) {
  return <div className="bar" role="progressbar" aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={100}><div style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} /></div>;
}

export const Loader = ({ text }: { text: string }) => <p className="muted center pad" role="status">{text}</p>;
export const Notice = ({ kind = 'info', children }: { kind?: 'info' | 'warn' | 'ok' | 'error'; children: ReactNode }) => <div className={`notice notice-${kind}`} role={kind === 'error' ? 'alert' : 'status'}>{children}</div>;
export const Tag = ({ children, kind = 'neutral' }: { children: ReactNode; kind?: 'neutral' | 'free' | 'premium' | 'review' }) => <span className={`tag tag-${kind}`}>{children}</span>;

export function Header({ title, onBack, right }: { title: string; onBack?: () => void; right?: ReactNode }) {
  return (
    <header className="page-header">
      {onBack && <button type="button" className="icon-btn" onClick={onBack} aria-label="Retour"><Icon name="back" /></button>}
      <h1>{title}</h1>
      <div className="page-header-right">{right}</div>
    </header>
  );
}

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => (part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part));
}

/** Rendu d'un Markdown simple (titres ##, listes -, gras) sans HTML brut. */
export function Markdown({ text }: { text: string }) {
  const out: ReactNode[] = [];
  let list: string[] = [];
  const flush = () => { if (list.length) { out.push(<ul key={out.length}>{list.map((l, i) => <li key={i}>{inline(l)}</li>)}</ul>); list = []; } };
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line) { flush(); continue; }
    if (/^[-*] /.test(line)) { list.push(line.slice(2)); continue; }
    flush();
    if (line.startsWith('### ')) out.push(<h4 key={out.length}>{inline(line.slice(4))}</h4>);
    else if (line.startsWith('## ')) out.push(<h3 key={out.length}>{inline(line.slice(3))}</h3>);
    else if (line.startsWith('# ')) out.push(<h3 key={out.length}>{inline(line.slice(2))}</h3>);
    else out.push(<p key={out.length}>{inline(line)}</p>);
  }
  flush();
  return <div className="prose">{out}</div>;
}

export const formatTime = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

// Affichage des prix dans la devise locale. Le montant facturé est toujours recalculé côté serveur
// (app.plan_amount) ; cette fonction en est le miroir pour l'affichage.
export interface Currency { code: string; symbol: string; usd_rate: number; decimals: number; rounding: number }
export interface Plan {
  id: string; code: string; billing_period: 'month' | 'year' | 'lifetime'; price_usd: number;
  name: Record<string, string>; description: Record<string, string>; features: Record<string, string>[];
  is_featured: boolean; sort: number;
}

export function localAmount(priceUsd: number, cur: Currency, override?: number | null): number {
  if (override != null) return Number(override);
  const step = Number(cur.rounding);
  const rounded = Math.round((priceUsd * Number(cur.usd_rate)) / step) * step;
  return Math.max(step, Math.round(rounded * 1000) / 1000);
}

export function formatPrice(amount: number, cur: Pick<Currency, 'code' | 'decimals'>, lang: string): string {
  const locale = lang === 'zh' ? 'zh-CN' : lang;
  try {
    return new Intl.NumberFormat(locale, { style: 'currency', currency: cur.code, minimumFractionDigits: cur.decimals, maximumFractionDigits: cur.decimals }).format(amount);
  } catch {
    return `${amount.toFixed(cur.decimals)} ${cur.code}`;
  }
}

// Répétition espacée (variante simplifiée de SM-2).
export interface CardState { ease: number; interval_days: number; repetitions: number; due_at: string }
export type Rating = 0 | 1 | 2 | 3; // 0 à revoir, 1 difficile, 2 bien, 3 facile

export const NEW_CARD: CardState = { ease: 2.5, interval_days: 0, repetitions: 0, due_at: new Date(0).toISOString() };

export function review(state: CardState, rating: Rating, now: Date = new Date()): CardState {
  let { ease, interval_days, repetitions } = state;
  if (rating === 0) {
    repetitions = 0;
    interval_days = 0; // revue dans la même séance (10 minutes)
    ease = Math.max(1.3, ease - 0.2);
  } else {
    ease = Math.min(3, Math.max(1.3, ease + (rating === 1 ? -0.15 : rating === 2 ? 0 : 0.15)));
    repetitions += 1;
    if (repetitions === 1) interval_days = rating === 3 ? 3 : 1;
    else if (repetitions === 2) interval_days = rating === 1 ? 3 : rating === 2 ? 6 : 8;
    else interval_days = Math.max(interval_days + 1, Math.round(interval_days * ease * (rating === 1 ? 0.6 : 1)));
  }
  const due = new Date(now.getTime() + (interval_days === 0 ? 10 * 60_000 : interval_days * 86_400_000));
  return { ease: Math.round(ease * 100) / 100, interval_days, repetitions, due_at: due.toISOString() };
}

export const isDue = (state: CardState | undefined, now: Date = new Date()) => !state || new Date(state.due_at) <= now;

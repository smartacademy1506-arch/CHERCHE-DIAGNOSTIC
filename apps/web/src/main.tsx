import { StrictMode, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { AppProvider, Shell, useApp } from './app';
import './styles.css';
import { Plans, Settings } from './screens/Account';
import { Admin } from './screens/Admin';
import { AuthScreen, ResetPassword, Welcome } from './screens/Auth';
import { ChapterHub, Glossary, Lesson, OpenQuestions } from './screens/Chapter';
import { Catalog, DisciplineScreen, Home, Stats } from './screens/Home';
import { QuizScreen } from './screens/Quiz';
import { DailyReview, FlashcardsScreen } from './screens/Review';
import { WordSearchScreen } from './screens/WordSearch';

function Routes() {
  const { route } = useApp();
  const [a, b, c] = route;
  switch (a) {
    case undefined: return <Home />;
    case 'learn': return <Catalog />;
    case 'd': return <DisciplineScreen slug={b} />;
    case 'c':
      switch (c) {
        case 'lesson': return <Lesson id={b} />;
        case 'ws': return <WordSearchScreen id={b} />;
        case 'glossary': return <Glossary id={b} />;
        case 'quiz': return <QuizScreen id={b} />;
        case 'open': return <OpenQuestions id={b} />;
        case 'cards': return <FlashcardsScreen id={b} />;
        default: return <ChapterHub id={b} />;
      }
    case 'review': return <DailyReview />;
    case 'stats': return <Stats />;
    case 'me': return <Settings />;
    case 'plans': return <Plans />;
    case 'auth': return <AuthScreen />;
    case 'reset': return <ResetPassword />;
    case 'admin': return <Admin />;
    default: return <Home />;
  }
}

function Root() {
  const [onboarded, setOnboarded] = useState(() => { try { return localStorage.getItem('cd.onboarded') === '1'; } catch { return true; } });
  if (!onboarded) return <Welcome onDone={() => { try { localStorage.setItem('cd.onboarded', '1'); } catch { /* ignore */ } setOnboarded(true); }} />;
  return <Shell><Routes /></Shell>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><AppProvider><Root /></AppProvider></StrictMode>);

if ('serviceWorker' in navigator && location.protocol === 'https:') {
  window.addEventListener('load', () => { navigator.serviceWorker.register('/sw.js').catch(() => { /* hors ligne indisponible */ }); });
}

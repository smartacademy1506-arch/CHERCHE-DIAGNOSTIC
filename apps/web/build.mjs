// Construit l'application dans dist/ : bundle esbuild + copie de public/.
// Variables facultatives : SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY (sinon valeurs de src/lib/config.ts).
import { build } from 'esbuild';
import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const root = import.meta.dirname;
const dist = join(root, 'dist');
const version = process.env.VERCEL_GIT_COMMIT_SHA?.slice(0, 7) || new Date().toISOString().replace(/[-:T]/g, '').slice(0, 12);

rmSync(dist, { recursive: true, force: true });
mkdirSync(join(dist, 'assets'), { recursive: true });
cpSync(join(root, 'public'), dist, { recursive: true });

await build({
  entryPoints: [join(root, 'src/main.tsx')],
  bundle: true,
  format: 'esm',
  target: ['es2020'],
  minify: !process.argv.includes('--dev'),
  sourcemap: process.argv.includes('--dev'),
  jsx: 'automatic',
  outfile: join(dist, 'assets/app.js'),
  loader: { '.css': 'css' },
  external: ['/fonts/*', '/brand/*'], // fichiers servis tels quels depuis public/
  define: {
    'process.env.NODE_ENV': '"production"',
    __APP_VERSION__: JSON.stringify(version),
    __SUPABASE_URL__: JSON.stringify(process.env.SUPABASE_URL || ''),
    __SUPABASE_KEY__: JSON.stringify(process.env.SUPABASE_PUBLISHABLE_KEY || ''),
  },
  logLevel: 'info',
});

const sw = join(dist, 'sw.js');
writeFileSync(sw, readFileSync(sw, 'utf8').replace('__APP_VERSION__', version));

console.log(`Build ${version} terminé → dist/`);

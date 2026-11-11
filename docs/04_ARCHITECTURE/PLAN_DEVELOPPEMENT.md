# Plan de développement — état au 11 novembre 2026

Légende : ✅ fait et testé · 🟡 fait, test incomplet · ⬜ non fait

| Phase | État | Détail |
|---|---|---|
| 1. Audit | ✅ | `docs/06_VALIDATION/AUDIT_DOCUMENTAIRE.md` |
| 2. Architecture | ✅ | ce dossier |
| 3. Dépôt et application | ✅ | `apps/web`, branche `claude/mvp` |
| 4. Base et authentification | 🟡 | Schéma, RLS et fonctions appliqués. Inscription, connexion, réinitialisation : écrans faits, **non testés contre le vrai Supabase** (pas d'accès réseau depuis l'environnement de test). |
| 5. Import des contenus | ✅ | `tools/build-payloads.ts` + `admin_import_chapter` ; 4 chapitres importés, 8 grilles vérifiées par la base. |
| 6. Catalogue, cours, glossaire | ✅ | Testés de bout en bout. |
| 7. Mots mêlés | ✅ | 7 tests du moteur, 3 scénarios de bout en bout (glisser, toucher début/fin, reprise). Non testé sur de vrais téléphones. |
| 8. QCM et questions ouvertes | ✅ | Correction serveur ; scénarios de bout en bout avec un faux serveur. Examens blancs multi-chapitres : ⬜. |
| 9. Progression et flashcards | ✅ | Répétition espacée, révisions du jour, statistiques. |
| 10. Hors ligne | 🟡 | Lecture hors ligne et conservation des résultats testées. File de synchronisation écrite, **renvoi au serveur non testé en conditions réelles**. |
| 11. Administration | 🟡 | Statistiques, statuts, import, glossaire, offres, devises, utilisateurs, rôles, paiements : écrans faits, **non testés avec un compte administrateur réel**. Édition des QCM, médias, programmes : ⬜. |
| 12. Abonnements et paiements | 🟡 | Offres, devises, demande de paiement, confirmation manuelle. Prestataire de paiement : ⬜. |
| 13. IA pédagogique | ⬜ | Non commencé (l'application n'en dépend pas). |
| 14. Tests, optimisation, déploiement | 🟡 | 7 tests du moteur et 15 scénarios de bout en bout réussis. Revues médicale et de sécurité indépendantes faites (docs/06_VALIDATION/REVUES_INDEPENDANTES.md). Déployé sur Vercel. Test de charge : ⬜. |

## Non fait dans ce MVP

Applications Flutter Android et iOS ; Next.js ; cas cliniques ; examens blancs ; illustrations ; offre institutions ;
notifications ; assistant IA ; import de PDF, Word, Excel (l'import accepte le JSON de `content/SPEC.md`) ;
vérification TypeScript complète (les types de React n'étaient pas installables : le code est compilé et exécuté, pas typé de bout en bout).

## Commandes

```
cd apps/web
npm install
npm run build        # construit dist/
npm test             # moteur de mots mêlés
npm run test:e2e     # scénarios de bout en bout (Chromium)
node ../../tools/validate-content.mjs ../../content/physiologie/*.json
npx tsx ../../tools/build-payloads.ts ../../content/physiologie
```

## Prochaines décisions

1. Contenu : fournir les sources des livres, nommer le responsable pédagogique.
2. Paiement : choisir le prestataire, ouvrir le compte marchand.
3. Mobile : PWA empaquetée pour le Play Store d'abord, ou développement Flutter.
4. Grilles sur téléphone : une grille de 40 mots, ou deux grilles de 20.
5. Prix locaux : conversion automatique, ou prix ronds fixés par devise (par ex. FCFA).

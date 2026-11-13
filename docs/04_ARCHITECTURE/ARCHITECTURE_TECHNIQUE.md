# Architecture technique du MVP

## Vue d'ensemble

```
Navigateur / application installée (PWA)
  apps/web  — React 19 + TypeScript, bundle esbuild, service worker, IndexedDB
        │  HTTPS (clé « publishable », jeton utilisateur)
        ▼
Supabase (source de vérité)
  Auth  ·  PostgreSQL + RLS  ·  fonctions SQL (RPC)  ·  Storage (prévu pour les médias)
Vercel : hébergement statique + fonction /api/geo (pays du visiteur)
```

Aucun backend concurrent, aucun service GCP : rien dans le MVP ne le justifie encore.

## Écarts assumés par rapport à la pile imposée

| Imposé | Livré | Pourquoi | Retour à la cible |
|---|---|---|---|
| Next.js | React 19 + esbuild (application monopage) | Next.js n'était pas installable ici ; une application non testée aurait enfreint « ne pas déclarer terminé sans test ». | Les écrans et `src/lib` sont du React/TypeScript standard : migration vers Next.js sans réécriture de la logique. |
| Flutter (Android/iOS) | PWA installable (Android, iOS, ordinateur), hors ligne | Flutter absent de l'environnement. | Le moteur de grilles, la répétition espacée et la synchronisation sont documentés et testés : à porter en Dart. En attendant, la PWA peut être empaquetée pour le Play Store (TWA). |
| SQLite / Drift | IndexedDB | Équivalent navigateur. | Drift côté Flutter, mêmes règles de synchronisation. |
| Client `supabase-js` | Client REST maison (`src/lib/supabase.ts`, ~150 lignes) | Paquet non installable ; moins de poids à télécharger. | Remplaçable sans toucher aux écrans. |

## Sécurité

- RLS activé sur les 42 tables. Les droits sont décidés par des fonctions du schéma `app` (non exposé par l'API).
- Bonnes réponses des QCM dans `quiz_answer_keys`, sans politique de lecture pour les étudiants ; correction par
  `submit_quiz_attempt` ; corrigés hors ligne réservés aux utilisateurs connectés ayant accès au chapitre.
- Chapitres payants : contenu filtré en base (`app.can_access_chapter`), pas seulement masqué à l'écran.
- Abonnement activé uniquement côté serveur (`admin_confirm_payment`, futur webhook) ; le montant est recalculé en base.
- Publication réservée aux rôles `pedagogy_lead`, `admin`, `super_admin` (déclencheur `guard_publish`).
- Grilles : une grille ne peut quitter le statut `draft` que si la base a vérifié chaque mot (déclencheur `guard_puzzle`).
- Journal d'audit sur rôles, abonnements, paiements, offres, devises, paramètres ; historique des versions de contenu.
- Aucune clé secrète dans le dépôt ni dans le navigateur. En-têtes CSP, `X-Frame-Options`, `nosniff` (vercel.json).
- Export et suppression du compte par l'utilisateur (`export_my_data`, `delete_my_account`).

## Hors ligne et synchronisation

- Le service worker met en cache la coquille de l'application ; les contenus ouverts ou téléchargés vont dans IndexedDB.
- L'interface lit toujours l'historique local ; chaque résultat part dans une file d'attente et est renvoyé au retour du réseau.
- Pas de doublon : chaque résultat porte un identifiant créé sur l'appareil (`upsert`, ou RPC idempotente pour les QCM).
- Conflits : dernier état le plus récent pour une grille, une carte ou une réponse ouverte ; les tentatives de QCM s'ajoutent.
- Un élément refusé définitivement par le serveur reste dans la file avec son erreur : rien n'est supprimé en silence.
- Limite connue : le QCM hors ligne exige d'avoir téléchargé le chapitre en étant connecté à son compte.

## Langues, pays, devises

- Interface : français, anglais, espagnol, chinois (`src/lib/i18n.ts`). Contenu médical : français et anglais ; en espagnol
  et en chinois, le contenu s'affiche en anglais avec un bandeau (pas de traduction médicale automatique non validée).
- Pays détecté par l'adresse IP (`/api/geo`), sinon fuseau horaire, sinon navigateur ; toujours modifiable.
- 50 pays, 23 devises. Prix de référence en USD (2,99 / 19,99 / 49,99), convertis avec un taux et un pas d'arrondi
  modifiables dans l'administration ; un prix fixe par devise peut remplacer la conversion (`plan_prices`).
  **Les taux saisis sont indicatifs (novembre 2026)** : à tenir à jour, ou à automatiser.

## Paiements — non branchés

Le MVP enregistre une demande de paiement (référence `CD-XXXXXXXX`) qu'un administrateur confirme après encaissement
(Mobile Money, espèces). Aucun prestataire n'est intégré : il faut un compte marchand au nom du projet. Pistes à
comparer : agrégateurs Mobile Money actifs au Cameroun (par ex. NotchPay, CinetPay, Flutterwave) et, pour les cartes
internationales, un marchand de référence (Paddle, Lemon Squeezy). Stripe n'ouvre pas de compte marchand au Cameroun.

## Coûts d'exploitation (estimation, à vérifier sur les grilles tarifaires officielles)

Taux utilisé : 1 USD ≈ 574 FCFA.

| Poste | Démarrage | Dès les premiers abonnés payants |
|---|---|---|
| Supabase | Offre gratuite : 0 (projet mis en pause après une semaine sans activité, pas de sauvegardes) | Offre Pro ≈ 25 USD ≈ 14 400 FCFA / mois |
| Vercel | Offre Hobby : 0 (usage non commercial uniquement) | Offre Pro ≈ 20 USD ≈ 11 500 FCFA / mois |
| Nom de domaine | ≈ 10 à 15 USD / an | idem |
| E-mails transactionnels (SMTP) | Indispensable : le service d'e-mail intégré à Supabase est limité à quelques messages par heure | 0 à 20 USD / mois selon le volume |
| IA pédagogique | 0 (non activée) | À l'usage, à plafonner |
| **Total mensuel** | **≈ 0 à 1 000 FCFA** | **≈ 26 000 à 38 000 FCFA** — dans la cible de 25 000 à 50 000 |

Capacité : 10 000 à 30 000 **inscrits** tiennent dans l'offre Pro de Supabase (quota d'utilisateurs actifs mensuels et
8 Go de base inclus) tant que le contenu reste du texte. Le nombre d'utilisateurs **simultanés** supportés n'a pas été
mesuré : aucun test de charge n'a été fait. L'application est économe (contenus mis en cache sur l'appareil), mais il
faut le vérifier avant une campagne de lancement.

## Ce qui reste à faire avant une mise en production

SMTP et URL du site dans Supabase Auth ; prestataire de paiement et webhook ; validation éditoriale des contenus ;
tests sur de vrais téléphones Android et iOS ; test de charge ; politique de confidentialité rédigée ; sauvegardes (offre Pro).

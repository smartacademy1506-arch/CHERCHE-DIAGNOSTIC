# Service e-mail

Supabase Auth envoie quatre e-mails : confirmation d'inscription, réinitialisation du mot de passe, lien de
connexion et changement d'adresse. Sans serveur SMTP personnalisé, Supabase n'envoie qu'aux membres de
l'équipe du projet, deux fois par heure : il faut donc brancher un SMTP avant d'ouvrir l'application.

Ces réglages se font dans le tableau de bord Supabase (projet `ukhcfzecjhbkiftoaeup`) : aucun outil
connecté à ce dépôt ne peut les écrire, et le mot de passe SMTP ne doit jamais entrer dans le dépôt.

## 1. Adresses de l'application

Authentication → URL Configuration :

- **Site URL** : `https://cherche-diagnostic.vercel.app`
- **Redirect URLs** : `https://cherche-diagnostic.vercel.app/**`

## 2. Serveur SMTP

Authentication → Emails → SMTP Settings → *Enable custom SMTP*.

### Option A — Gmail (immédiat, gratuit, environ 500 envois par jour)

1. Sur le compte Google qui enverra les e-mails, activer la validation en deux étapes.
2. Créer un mot de passe d'application : <https://myaccount.google.com/apppasswords> (nom : « Supabase »).
3. Dans Supabase :

| Champ | Valeur |
|---|---|
| Sender email | l'adresse Gmail |
| Sender name | `CHERCHE & DIAGNOSTIC` |
| Host | `smtp.gmail.com` |
| Port | `465` |
| Username | l'adresse Gmail |
| Password | le mot de passe d'application (16 caractères) |

### Option B — Brevo ou Resend avec un domaine (recommandé avant le lancement public)

Meilleure délivrabilité et adresse d'expédition à votre nom (par exemple `noreply@<votre-domaine>`).
Créer le compte chez le fournisseur, ajouter le domaine, puis publier chez l'hébergeur DNS (Hostinger) les
enregistrements SPF, DKIM et DMARC qu'il indique. Le fournisseur donne ensuite l'hôte, le port, l'identifiant
et la clé SMTP à saisir dans le même formulaire.

## 3. Modèles aux couleurs de l'application

Authentication → Emails → Templates. Pour chaque type, coller le sujet de `supabase/templates/subjects.json`
et le contenu du fichier HTML correspondant :

| Type Supabase | Fichier |
|---|---|
| Confirm signup | `supabase/templates/confirmation.html` |
| Reset password | `supabase/templates/recovery.html` |
| Magic link | `supabase/templates/magic_link.html` |
| Change email address | `supabase/templates/email_change.html` |

Chaque modèle contient le français, l'anglais, l'espagnol et le chinois ; la langue suit celle choisie à
l'inscription (`user_metadata.language_code`), le français par défaut. Le logo est chargé depuis
`https://cherche-diagnostic.vercel.app/brand/logo-horizontal.png`.

Pour modifier un texte : éditer `tools/email/build_templates.py`, lancer
`python3 -I tools/email/build_templates.py`, puis recoller le modèle.

## 4. Vérifier

1. Authentication → Rate Limits : relever « emails per hour » (30 par défaut avec un SMTP personnalisé).
2. Créer un compte de test depuis l'application, vérifier la réception (et le dossier Spam), cliquer le lien.
3. Tester « Mot de passe oublié » depuis l'écran de connexion.

Le super administrateur est attribué automatiquement à la confirmation de son adresse (table
`app.bootstrap_admins`) : il suffit de s'inscrire avec cette adresse et de cliquer le lien reçu.

# CHERCHE & DIAGNOSTIC

**Apprends. Révise. Progresse.** — plateforme d'apprentissage des sciences de la santé : cours, mots mêlés médicaux,
glossaire, QCM, questions ouvertes, flashcards et suivi de progression, en français et en anglais
(interface également en espagnol et en chinois).

| Dossier | Contenu |
|---|---|
| `apps/web` | Application web installable (PWA) : React 19, TypeScript, hors ligne |
| `supabase/migrations` | Schéma PostgreSQL, sécurité RLS, fonctions |
| `supabase/seed` | Chapitres prêts à importer ; `seed/books` : les huit livres de la collection, chiffrés |
| `supabase/templates` | E-mails d'authentification aux couleurs de l'application (4 langues) |
| `content` | Contenu pédagogique source ; le texte des livres (`content/books`) reste hors du dépôt public |
| `tools` | Extraction et vérification des livres, import, modèles d'e-mails, éléments de marque |
| `docs` | Audit, cartographie pédagogique, architecture, schéma, plan |

Documentation : [audit](docs/06_VALIDATION/AUDIT_DOCUMENTAIRE.md) ·
[cartographie pédagogique](docs/06_VALIDATION/CARTOGRAPHIE_PEDAGOGIQUE.md) ·
[architecture et coûts](docs/04_ARCHITECTURE/ARCHITECTURE_TECHNIQUE.md) ·
[base de données](docs/04_ARCHITECTURE/SCHEMA_BASE_DONNEES.md) ·
[plan et état d'avancement](docs/04_ARCHITECTURE/PLAN_DEVELOPPEMENT.md) ·
[revues indépendantes](docs/06_VALIDATION/REVUES_INDEPENDANTES.md) ·
[service e-mail](docs/04_ARCHITECTURE/SERVICE_EMAIL.md) ·
[produit](PRODUCT.md) · [design system](DESIGN.md) ·
[import des livres](supabase/seed/books/README.md)

Le contenu vient des huit livres de la collection CHERCHE ET DIAGNOSTIQUE (149 chapitres, 8 940 termes,
149 grilles) ; il est en cours de validation pédagogique. L'application est un outil
d'apprentissage, pas un dispositif de diagnostic.

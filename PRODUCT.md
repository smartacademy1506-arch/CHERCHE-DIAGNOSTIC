# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Étudiants en médecine et dans les autres filières des sciences de la santé (pharmacie, soins infirmiers, maïeutique,
odontostomatologie), candidats aux examens et concours. Marché initial : Cameroun et Afrique francophone ; ensuite Afrique
anglophone, Europe et international. Usage majoritaire sur téléphone, souvent avec une connexion lente ou coupée, en
révision personnelle ou en groupe de travaux dirigés.

## Product Purpose

Faire apprendre, mémoriser et réviser le vocabulaire et les notions médicales par le jeu : chaque chapitre réunit un cours,
une grille de mots mêlés de 60 termes, un glossaire, des vignettes cliniques corrigées, des questions et des flashcards à
répétition espacée. Le succès : l'étudiant revient chaque jour, trouve les mots, connaît leurs définitions et progresse à
ses examens.

## Positioning

La plateforme prolonge la collection de livres « Cherche et Diagnostique » (Dr SOLLE SOLLE & Dr Jerry Jontzo) : le moteur
de mots mêlés médicaux, alimenté par les grilles et glossaires écrits par les auteurs, est le cœur distinctif. Les autres
outils (QCM, flashcards, statistiques) servent la révision autour de ces grilles.

## Operating Context

- Contenu d'auteur : 8 volumes (Physiologie générale, Anatomie : ostéologie, myologie, innervation, vascularisation,
  organes ; Pharmacologie ; Sémiologie par systèmes), chapitres à 60 mots par grille 20 × 20, grilles « niveau expert »
  dans les volumes récents (aucun mot de gauche à droite ni de haut en bas).
- Hors ligne et faible consommation de données obligatoires.
- Validation éditoriale avant publication ; l'application est un outil d'apprentissage, jamais un outil de diagnostic.

## Capabilities and Constraints

- PWA React 19 + TypeScript (apps/web), Supabase (Auth, PostgreSQL, RLS). Flutter et Next.js prévus par le cahier des
  charges, non disponibles dans l'environnement actuel.
- Interface : français, anglais, espagnol, chinois. Contenu médical : français (source) et anglais (traduction à valider).
- Offres : 2,99 $ par mois, 19,99 $ par an, 49,99 $ à vie ; prix affichés dans la devise du pays ; paiement confirmé côté
  serveur uniquement. Prestataire de paiement non choisi.

## Brand Commitments

- Nom affiché : « CHERCHE & DIAGNOSTIC » (confirmé par l'utilisateur le 12/11/2026 ; les livres écrivent « DIAGNOSTIQUE »).
- Signature : « Apprends. Révise. Progresse. »
- Logo fourni par l'utilisateur le 12/11/2026 (assets/brand/*-source.png) : loupe formant un « C », croix rouge, livre
  ouvert ; lettrage géométrique gras, « CHERCHE » en bleu marine, « & » en bleu ciel, « DIAGNOSTIC » en rouge.
  Couleurs relevées sur le logo : bleu marine #003562, rouge #CD1A1C, bleu ciel #30A8E0. Le logo s'emploie tel quel,
  sans le redessiner.
- Direction artistique imposée par le cahier des charges : bleu médical profond, blanc dominant pour la lecture, rouge
  réservé aux alertes et accents ; sérieux académique, innovation ; ne copier aucune application existante.

## Evidence on Hand

- Les 8 livres PDF de l'utilisateur (couvertures, grilles, glossaires, vignettes), extraits dans content/books/.
- Aucun témoignage, aucun chiffre d'usage, aucun partenaire institutionnel : ne pas en inventer.

## Product Principles

1. Le contenu des auteurs fait foi : l'application le restitue sans le réécrire.
2. La grille est le moment fort : elle doit être agréable au doigt, sur un petit écran, sans réseau.
3. Lire avant de jouer, jouer avant d'être évalué : chaque activité renvoie vers les définitions.
4. Sobriété de données et de batterie : rien d'inutile à télécharger.

## Accessibility & Inclusion

Écrans de 360 px, appareils d'entrée de gamme, lumière forte ; contraste AA minimum ; aucune information portée par la
seule couleur (mots trouvés barrés en plus d'être colorés) ; animations réduites si l'utilisateur le demande.

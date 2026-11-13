-- Les grilles du livre de pharmacologie contiennent des sigles de deux lettres (KD, QT, VX, MU, CD).
-- La grille imprimée fait foi : un mot de grille compte désormais de 2 à 30 lettres.
alter table public.puzzle_words drop constraint puzzle_words_word_check;
alter table public.puzzle_words add constraint puzzle_words_word_check check (word ~ '^[A-Z]{2,30}$');

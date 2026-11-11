-- CHERCHE & DIAGNOSTIC — données de référence (langues, devises, pays, rôles, offres, disciplines)
-- Les taux de change sont indicatifs (novembre 2026) et modifiables dans l'espace administrateur.

insert into public.languages(code, name, native_name, is_ui_language, is_content_language, sort) values
  ('fr', 'French', 'Français', true, true, 1),
  ('en', 'English', 'English', true, true, 2),
  ('es', 'Spanish', 'Español', true, false, 3),
  ('zh', 'Chinese', '中文', true, false, 4);

insert into public.currencies(code, name, symbol, usd_rate, decimals, rounding) values
  ('USD', 'US Dollar', '$', 1, 2, 0.01),
  ('EUR', 'Euro', '€', 0.875, 2, 0.01),
  ('XAF', 'Franc CFA (BEAC)', 'FCFA', 574, 0, 50),
  ('XOF', 'Franc CFA (BCEAO)', 'FCFA', 574, 0, 50),
  ('GBP', 'Pound Sterling', '£', 0.745, 2, 0.01),
  ('CAD', 'Canadian Dollar', 'CA$', 1.40, 2, 0.01),
  ('CHF', 'Swiss Franc', 'CHF', 0.82, 2, 0.05),
  ('CNY', 'Chinese Yuan', '¥', 6.75, 2, 0.1),
  ('NGN', 'Nigerian Naira', '₦', 1530, 0, 50),
  ('GHS', 'Ghanaian Cedi', 'GH₵', 10.9, 2, 0.5),
  ('KES', 'Kenyan Shilling', 'KSh', 129.9, 0, 10),
  ('ZAR', 'South African Rand', 'R', 16.5, 2, 1),
  ('MAD', 'Moroccan Dirham', 'DH', 9.2, 2, 1),
  ('DZD', 'Algerian Dinar', 'DA', 132.8, 0, 10),
  ('EGP', 'Egyptian Pound', 'E£', 49.8, 2, 1),
  ('RWF', 'Rwandan Franc', 'FRw', 1475, 0, 100),
  ('TZS', 'Tanzanian Shilling', 'TSh', 2640, 0, 100),
  ('MGA', 'Malagasy Ariary', 'Ar', 4254, 0, 100),
  ('GNF', 'Guinean Franc', 'FG', 8779, 0, 500),
  ('INR', 'Indian Rupee', '₹', 95.3, 0, 1),
  ('MXN', 'Mexican Peso', 'MX$', 17.4, 2, 1),
  ('JPY', 'Japanese Yen', '¥', 157.8, 0, 10),
  ('AUD', 'Australian Dollar', 'A$', 1.43, 2, 0.01);

insert into public.countries(code, name, currency_code, default_language) values
  ('CM', '{"fr":"Cameroun","en":"Cameroon","es":"Camerún","zh":"喀麦隆"}', 'XAF', 'fr'),
  ('GA', '{"fr":"Gabon","en":"Gabon","es":"Gabón","zh":"加蓬"}', 'XAF', 'fr'),
  ('CG', '{"fr":"Congo","en":"Congo","es":"Congo","zh":"刚果（布）"}', 'XAF', 'fr'),
  ('TD', '{"fr":"Tchad","en":"Chad","es":"Chad","zh":"乍得"}', 'XAF', 'fr'),
  ('CF', '{"fr":"Centrafrique","en":"Central African Republic","es":"República Centroafricana","zh":"中非"}', 'XAF', 'fr'),
  ('GQ', '{"fr":"Guinée équatoriale","en":"Equatorial Guinea","es":"Guinea Ecuatorial","zh":"赤道几内亚"}', 'XAF', 'es'),
  ('SN', '{"fr":"Sénégal","en":"Senegal","es":"Senegal","zh":"塞内加尔"}', 'XOF', 'fr'),
  ('CI', '{"fr":"Côte d''Ivoire","en":"Côte d''Ivoire","es":"Costa de Marfil","zh":"科特迪瓦"}', 'XOF', 'fr'),
  ('ML', '{"fr":"Mali","en":"Mali","es":"Malí","zh":"马里"}', 'XOF', 'fr'),
  ('BF', '{"fr":"Burkina Faso","en":"Burkina Faso","es":"Burkina Faso","zh":"布基纳法索"}', 'XOF', 'fr'),
  ('BJ', '{"fr":"Bénin","en":"Benin","es":"Benín","zh":"贝宁"}', 'XOF', 'fr'),
  ('TG', '{"fr":"Togo","en":"Togo","es":"Togo","zh":"多哥"}', 'XOF', 'fr'),
  ('NE', '{"fr":"Niger","en":"Niger","es":"Níger","zh":"尼日尔"}', 'XOF', 'fr'),
  ('GN', '{"fr":"Guinée","en":"Guinea","es":"Guinea","zh":"几内亚"}', 'GNF', 'fr'),
  ('CD', '{"fr":"RD Congo","en":"DR Congo","es":"RD Congo","zh":"刚果（金）"}', 'USD', 'fr'),
  ('MG', '{"fr":"Madagascar","en":"Madagascar","es":"Madagascar","zh":"马达加斯加"}', 'MGA', 'fr'),
  ('MA', '{"fr":"Maroc","en":"Morocco","es":"Marruecos","zh":"摩洛哥"}', 'MAD', 'fr'),
  ('DZ', '{"fr":"Algérie","en":"Algeria","es":"Argelia","zh":"阿尔及利亚"}', 'DZD', 'fr'),
  ('TN', '{"fr":"Tunisie","en":"Tunisia","es":"Túnez","zh":"突尼斯"}', 'USD', 'fr'),
  ('HT', '{"fr":"Haïti","en":"Haiti","es":"Haití","zh":"海地"}', 'USD', 'fr'),
  ('NG', '{"fr":"Nigeria","en":"Nigeria","es":"Nigeria","zh":"尼日利亚"}', 'NGN', 'en'),
  ('GH', '{"fr":"Ghana","en":"Ghana","es":"Ghana","zh":"加纳"}', 'GHS', 'en'),
  ('KE', '{"fr":"Kenya","en":"Kenya","es":"Kenia","zh":"肯尼亚"}', 'KES', 'en'),
  ('ZA', '{"fr":"Afrique du Sud","en":"South Africa","es":"Sudáfrica","zh":"南非"}', 'ZAR', 'en'),
  ('RW', '{"fr":"Rwanda","en":"Rwanda","es":"Ruanda","zh":"卢旺达"}', 'RWF', 'en'),
  ('TZ', '{"fr":"Tanzanie","en":"Tanzania","es":"Tanzania","zh":"坦桑尼亚"}', 'TZS', 'en'),
  ('EG', '{"fr":"Égypte","en":"Egypt","es":"Egipto","zh":"埃及"}', 'EGP', 'en'),
  ('FR', '{"fr":"France","en":"France","es":"Francia","zh":"法国"}', 'EUR', 'fr'),
  ('BE', '{"fr":"Belgique","en":"Belgium","es":"Bélgica","zh":"比利时"}', 'EUR', 'fr'),
  ('LU', '{"fr":"Luxembourg","en":"Luxembourg","es":"Luxemburgo","zh":"卢森堡"}', 'EUR', 'fr'),
  ('CH', '{"fr":"Suisse","en":"Switzerland","es":"Suiza","zh":"瑞士"}', 'CHF', 'fr'),
  ('DE', '{"fr":"Allemagne","en":"Germany","es":"Alemania","zh":"德国"}', 'EUR', 'en'),
  ('IT', '{"fr":"Italie","en":"Italy","es":"Italia","zh":"意大利"}', 'EUR', 'en'),
  ('PT', '{"fr":"Portugal","en":"Portugal","es":"Portugal","zh":"葡萄牙"}', 'EUR', 'en'),
  ('NL', '{"fr":"Pays-Bas","en":"Netherlands","es":"Países Bajos","zh":"荷兰"}', 'EUR', 'en'),
  ('ES', '{"fr":"Espagne","en":"Spain","es":"España","zh":"西班牙"}', 'EUR', 'es'),
  ('GB', '{"fr":"Royaume-Uni","en":"United Kingdom","es":"Reino Unido","zh":"英国"}', 'GBP', 'en'),
  ('US', '{"fr":"États-Unis","en":"United States","es":"Estados Unidos","zh":"美国"}', 'USD', 'en'),
  ('CA', '{"fr":"Canada","en":"Canada","es":"Canadá","zh":"加拿大"}', 'CAD', 'en'),
  ('MX', '{"fr":"Mexique","en":"Mexico","es":"México","zh":"墨西哥"}', 'MXN', 'es'),
  ('CO', '{"fr":"Colombie","en":"Colombia","es":"Colombia","zh":"哥伦比亚"}', 'USD', 'es'),
  ('AR', '{"fr":"Argentine","en":"Argentina","es":"Argentina","zh":"阿根廷"}', 'USD', 'es'),
  ('PE', '{"fr":"Pérou","en":"Peru","es":"Perú","zh":"秘鲁"}', 'USD', 'es'),
  ('CL', '{"fr":"Chili","en":"Chile","es":"Chile","zh":"智利"}', 'USD', 'es'),
  ('BR', '{"fr":"Brésil","en":"Brazil","es":"Brasil","zh":"巴西"}', 'USD', 'en'),
  ('CN', '{"fr":"Chine","en":"China","es":"China","zh":"中国"}', 'CNY', 'zh'),
  ('IN', '{"fr":"Inde","en":"India","es":"India","zh":"印度"}', 'INR', 'en'),
  ('JP', '{"fr":"Japon","en":"Japan","es":"Japón","zh":"日本"}', 'JPY', 'en'),
  ('AU', '{"fr":"Australie","en":"Australia","es":"Australia","zh":"澳大利亚"}', 'AUD', 'en');

insert into public.roles(code, name, rank) values
  ('super_admin', '{"fr":"Super administrateur","en":"Super administrator"}', 100),
  ('admin', '{"fr":"Administrateur","en":"Administrator"}', 80),
  ('pedagogy_lead', '{"fr":"Responsable pédagogique","en":"Pedagogy lead"}', 60),
  ('contributor', '{"fr":"Enseignant / contributeur","en":"Teacher / contributor"}', 40),
  ('moderator', '{"fr":"Modérateur","en":"Moderator"}', 20),
  ('student', '{"fr":"Étudiant","en":"Student"}', 0);

insert into public.permissions(code, description) values
  ('content.edit', 'Créer et modifier les contenus pédagogiques'),
  ('content.publish', 'Publier, dépublier et supprimer les contenus'),
  ('users.manage', 'Gérer les utilisateurs et les rôles'),
  ('billing.manage', 'Gérer les offres, les prix, les devises, les paiements et les abonnements'),
  ('stats.view', 'Consulter les statistiques'),
  ('settings.manage', 'Modifier les paramètres de la plateforme');

insert into public.role_permissions(role_code, permission_code)
select r, p from (values
  ('super_admin', 'content.edit'), ('super_admin', 'content.publish'), ('super_admin', 'users.manage'),
  ('super_admin', 'billing.manage'), ('super_admin', 'stats.view'), ('super_admin', 'settings.manage'),
  ('admin', 'content.edit'), ('admin', 'content.publish'), ('admin', 'users.manage'),
  ('admin', 'billing.manage'), ('admin', 'stats.view'), ('admin', 'settings.manage'),
  ('pedagogy_lead', 'content.edit'), ('pedagogy_lead', 'content.publish'), ('pedagogy_lead', 'stats.view'),
  ('contributor', 'content.edit'), ('moderator', 'stats.view')) v(r, p);

insert into public.app_settings(key, value, is_public) values
  ('show_in_review_content', 'true', true),
  ('support_contact', '""', true);

insert into public.plans(code, name, description, features, billing_period, price_usd, is_featured, sort) values
  ('monthly',
   '{"fr":"Mensuel","en":"Monthly","es":"Mensual","zh":"月度"}',
   '{"fr":"Accès complet, sans engagement","en":"Full access, cancel anytime","es":"Acceso completo, sin compromiso","zh":"完整访问，随时取消"}',
   '[{"fr":"Tous les chapitres et toutes les grilles","en":"All chapters and puzzles","es":"Todos los capítulos y sopas de letras","zh":"所有章节和字谜"},
     {"fr":"QCM corrigés et flashcards","en":"Corrected quizzes and flashcards","es":"Cuestionarios corregidos y tarjetas","zh":"带解析的测验和记忆卡"},
     {"fr":"Téléchargement hors ligne","en":"Offline downloads","es":"Descargas sin conexión","zh":"离线下载"}]',
   'month', 2.99, false, 1),
  ('yearly',
   '{"fr":"Annuel","en":"Yearly","es":"Anual","zh":"年度"}',
   '{"fr":"Une année complète de révisions","en":"A full year of revision","es":"Un año completo de repaso","zh":"全年复习"}',
   '[{"fr":"Tout le contenu de l''offre mensuelle","en":"Everything in Monthly","es":"Todo lo del plan mensual","zh":"包含月度套餐全部内容"},
     {"fr":"Statistiques détaillées","en":"Detailed statistics","es":"Estadísticas detalladas","zh":"详细统计"},
     {"fr":"Environ 44 % d''économie par rapport au mensuel","en":"About 44% cheaper than paying monthly","es":"Cerca de un 44 % de ahorro frente al mensual","zh":"比按月付费节省约44%"}]',
   'year', 19.99, true, 2),
  ('lifetime',
   '{"fr":"À vie","en":"Lifetime","es":"De por vida","zh":"终身"}',
   '{"fr":"Un seul paiement, accès permanent","en":"One payment, permanent access","es":"Un solo pago, acceso permanente","zh":"一次付费，永久访问"}',
   '[{"fr":"Tout le contenu actuel et à venir","en":"All current and future content","es":"Todo el contenido actual y futuro","zh":"所有现有及未来内容"},
     {"fr":"Aucun renouvellement","en":"No renewal","es":"Sin renovación","zh":"无需续费"}]',
   'lifetime', 49.99, false, 3);

insert into public.disciplines(slug, title, icon, sort, status) values
  ('physiologie', '{"fr":"Physiologie","en":"Physiology","es":"Fisiología","zh":"生理学"}', 'pulse', 1, 'published'),
  ('anatomie', '{"fr":"Anatomie","en":"Anatomy","es":"Anatomía","zh":"解剖学"}', 'bone', 2, 'published'),
  ('histologie-embryologie', '{"fr":"Histologie et embryologie","en":"Histology and embryology","es":"Histología y embriología","zh":"组织学与胚胎学"}', 'microscope', 3, 'published'),
  ('biochimie', '{"fr":"Biochimie","en":"Biochemistry","es":"Bioquímica","zh":"生物化学"}', 'flask', 4, 'published'),
  ('biologie-cellulaire', '{"fr":"Biologie cellulaire","en":"Cell biology","es":"Biología celular","zh":"细胞生物学"}', 'cell', 5, 'published'),
  ('microbiologie', '{"fr":"Microbiologie","en":"Microbiology","es":"Microbiología","zh":"微生物学"}', 'germ', 6, 'published'),
  ('parasitologie', '{"fr":"Parasitologie","en":"Parasitology","es":"Parasitología","zh":"寄生虫学"}', 'bug', 7, 'published'),
  ('immunologie', '{"fr":"Immunologie","en":"Immunology","es":"Inmunología","zh":"免疫学"}', 'shield', 8, 'published'),
  ('pharmacologie', '{"fr":"Pharmacologie","en":"Pharmacology","es":"Farmacología","zh":"药理学"}', 'pill', 9, 'published'),
  ('semiologie', '{"fr":"Sémiologie médicale","en":"Clinical semiology","es":"Semiología médica","zh":"症状学"}', 'stethoscope', 10, 'published'),
  ('medecine-interne', '{"fr":"Médecine interne","en":"Internal medicine","es":"Medicina interna","zh":"内科学"}', 'heart', 11, 'published'),
  ('chirurgie', '{"fr":"Chirurgie","en":"Surgery","es":"Cirugía","zh":"外科学"}', 'scalpel', 12, 'published'),
  ('gynecologie-obstetrique', '{"fr":"Gynécologie-obstétrique","en":"Obstetrics and gynaecology","es":"Ginecología y obstetricia","zh":"妇产科学"}', 'baby', 13, 'published'),
  ('pediatrie', '{"fr":"Pédiatrie","en":"Paediatrics","es":"Pediatría","zh":"儿科学"}', 'child', 14, 'published'),
  ('sante-publique', '{"fr":"Santé publique","en":"Public health","es":"Salud pública","zh":"公共卫生"}', 'globe', 15, 'published');

-- Contenu des trois offres (12/11/2026). Les prix restent ceux décidés : 2,99 $ / 19,99 $ / 49,99 $.
update public.plans set
  name = '{"fr":"Mensuel","en":"Monthly","es":"Mensual","zh":"月度"}',
  description = '{"fr":"Pour une période d''examens : tout débloquer, sans engagement.","en":"For an exam period: unlock everything, cancel anytime.","es":"Para una época de exámenes: todo desbloqueado, sin compromiso.","zh":"考试期间使用：解锁全部内容，随时取消。"}',
  features = '[
    {"fr":"Tous les volumes de la collection : chaque chapitre et chaque grille","en":"Every volume in the collection: every chapter and every word search","es":"Todos los volúmenes de la colección: cada capítulo y cada sopa de letras","zh":"全套各卷：所有章节和字谜"},
    {"fr":"Glossaires complets, vignettes cliniques corrigées et questions","en":"Full glossaries, answered clinical vignettes and questions","es":"Glosarios completos, viñetas clínicas corregidas y preguntas","zh":"完整术语表、带解析的临床病例和问题"},
    {"fr":"Flashcards à répétition espacée et révisions du jour","en":"Spaced-repetition flashcards and daily review","es":"Tarjetas con repetición espaciada y repaso diario","zh":"间隔重复记忆卡与每日复习"},
    {"fr":"Chapitres téléchargeables pour réviser hors ligne","en":"Downloadable chapters for offline revision","es":"Capítulos descargables para repasar sin conexión","zh":"可下载章节，离线复习"},
    {"fr":"Suivi de progression par chapitre","en":"Progress tracking for every chapter","es":"Seguimiento del progreso por capítulo","zh":"按章节跟踪学习进度"}]'
where code = 'monthly';

update public.plans set
  name = '{"fr":"Annuel","en":"Yearly","es":"Anual","zh":"年度"}',
  description = '{"fr":"Toute l''année universitaire, des premiers cours aux examens et concours.","en":"The whole academic year, from first lectures to exams and entrance tests.","es":"Todo el curso académico, de las primeras clases a los exámenes y oposiciones.","zh":"覆盖整个学年，从开学到考试和竞赛。"}',
  features = '[
    {"fr":"Tout le contenu de l''offre mensuelle","en":"Everything in Monthly","es":"Todo lo del plan mensual","zh":"包含月度套餐全部内容"},
    {"fr":"12 mois d''accès pour le prix de moins de 7 mois","en":"12 months of access for the price of under 7","es":"12 meses de acceso por el precio de menos de 7","zh":"12 个月的使用期，价格不到 7 个月"},
    {"fr":"Un seul paiement, rien à renouveler en cours d''année","en":"One payment, nothing to renew during the year","es":"Un solo pago, nada que renovar durante el año","zh":"一次付款，年内无需续费"}]'
where code = 'yearly';

update public.plans set
  name = '{"fr":"À vie","en":"Lifetime","es":"De por vida","zh":"终身"}',
  description = '{"fr":"Un seul paiement pour toute votre formation, et au-delà.","en":"One payment for your whole training, and beyond.","es":"Un solo pago para toda tu formación, y más allá.","zh":"一次付款，覆盖整个学业及以后。"}',
  features = '[
    {"fr":"Tout le contenu de l''offre annuelle, sans date de fin","en":"Everything in Yearly, with no end date","es":"Todo lo del plan anual, sin fecha de fin","zh":"包含年度套餐全部内容，永久有效"},
    {"fr":"Les nouveaux volumes de la collection inclus dès leur parution","en":"New volumes in the collection included as soon as they come out","es":"Los nuevos volúmenes de la colección incluidos en cuanto se publiquen","zh":"新出版的各卷一经推出即包含在内"},
    {"fr":"Aucun renouvellement à surveiller","en":"No renewal to keep track of","es":"Ninguna renovación que vigilar","zh":"无需关注续费"}]'
where code = 'lifetime';

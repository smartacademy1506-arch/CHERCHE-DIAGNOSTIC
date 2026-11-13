"""Génère les modèles d'e-mails d'authentification Supabase aux couleurs de CHERCHE & DIAGNOSTIC.

Usage : python3 -I tools/email/build_templates.py
Sortie : supabase/templates/<modèle>.html et supabase/templates/subjects.json

Supabase n'accepte qu'un modèle par type d'e-mail : la langue est choisie dans le modèle d'après
la langue enregistrée à l'inscription (user_metadata.language_code, envoyée par l'écran d'inscription).
Le français sert par défaut. Variables Supabase utilisées : {{ .ConfirmationURL }}, {{ .Email }}, {{ .NewEmail }}.
"""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'supabase' / 'templates'
SITE = 'https://cherche-diagnostic.vercel.app'
LANGS = ('fr', 'en', 'es', 'zh')

TEXT = {
    'confirmation': {
        'subject': 'Confirmez votre adresse · Confirm your email — CHERCHE & DIAGNOSTIC',
        'fr': ('Confirmez votre adresse', 'Bienvenue ! Confirmez votre adresse e-mail pour activer votre compte et retrouver vos grilles, fiches et progrès sur tous vos appareils.', 'Confirmer mon adresse'),
        'en': ('Confirm your email', 'Welcome! Confirm your email address to activate your account and keep your grids, flashcards and progress on all your devices.', 'Confirm my email'),
        'es': ('Confirma tu correo', '¡Bienvenido! Confirma tu dirección de correo para activar tu cuenta y conservar tus sopas de letras, fichas y progreso en todos tus dispositivos.', 'Confirmar mi correo'),
        'zh': ('确认您的邮箱', '欢迎！请确认您的邮箱地址以激活账户，并在所有设备上保留您的字谜、卡片和学习进度。', '确认邮箱'),
    },
    'recovery': {
        'subject': 'Nouveau mot de passe · Reset your password — CHERCHE & DIAGNOSTIC',
        'fr': ('Choisissez un nouveau mot de passe', 'Vous avez demandé à réinitialiser votre mot de passe. Le lien ci-dessous est valable une heure et ne sert qu’une fois.', 'Choisir un mot de passe'),
        'en': ('Choose a new password', 'You asked to reset your password. The link below is valid for one hour and works only once.', 'Choose a password'),
        'es': ('Elige una nueva contraseña', 'Has pedido restablecer tu contraseña. El enlace de abajo es válido durante una hora y solo funciona una vez.', 'Elegir una contraseña'),
        'zh': ('设置新密码', '您申请了重置密码。以下链接在一小时内有效，且只能使用一次。', '设置密码'),
    },
    'magic_link': {
        'subject': 'Votre lien de connexion · Your sign-in link — CHERCHE & DIAGNOSTIC',
        'fr': ('Votre lien de connexion', 'Utilisez ce lien pour vous connecter. Il est valable une heure et ne sert qu’une fois.', 'Me connecter'),
        'en': ('Your sign-in link', 'Use this link to sign in. It is valid for one hour and works only once.', 'Sign in'),
        'es': ('Tu enlace de acceso', 'Usa este enlace para iniciar sesión. Es válido durante una hora y solo funciona una vez.', 'Iniciar sesión'),
        'zh': ('您的登录链接', '使用此链接登录。链接在一小时内有效，且只能使用一次。', '登录'),
    },
    'email_change': {
        'subject': 'Confirmez votre nouvelle adresse · Confirm your new email — CHERCHE & DIAGNOSTIC',
        'fr': ('Confirmez votre nouvelle adresse', 'Vous avez demandé à remplacer {{ .Email }} par {{ .NewEmail }}. Confirmez ce changement avec le lien ci-dessous.', 'Confirmer le changement'),
        'en': ('Confirm your new email', 'You asked to change {{ .Email }} to {{ .NewEmail }}. Confirm the change with the link below.', 'Confirm the change'),
        'es': ('Confirma tu nuevo correo', 'Has pedido cambiar {{ .Email }} por {{ .NewEmail }}. Confirma el cambio con el enlace de abajo.', 'Confirmar el cambio'),
        'zh': ('确认您的新邮箱', '您申请将 {{ .Email }} 更改为 {{ .NewEmail }}。请通过以下链接确认此更改。', '确认更改'),
    },
}
FOOTER = {
    'fr': ('Si vous n’êtes pas à l’origine de cette demande, ignorez ce message : rien ne changera sur votre compte.', 'Le bouton ne s’ouvre pas ? Copiez ce lien dans votre navigateur :'),
    'en': ('If you did not make this request, ignore this message: nothing will change on your account.', 'Button not working? Copy this link into your browser:'),
    'es': ('Si no hiciste esta solicitud, ignora este mensaje: nada cambiará en tu cuenta.', '¿El botón no funciona? Copia este enlace en tu navegador:'),
    'zh': ('如果这不是您本人的操作，请忽略此邮件：您的账户不会有任何变化。', '按钮无法打开？请将此链接复制到浏览器中：'),
}
TAGLINE = {'fr': 'Apprends. Révise. Progresse.', 'en': 'Learn. Review. Progress.', 'es': 'Aprende. Repasa. Progresa.', 'zh': '学习。复习。进步。'}


def keep_vars(text: str) -> str:
    """Échappe le texte en gardant intactes les variables Go de Supabase."""
    out, i = [], 0
    while (j := text.find('{{', i)) != -1:
        k = text.index('}}', j) + 2
        out += [escape(text[i:j]), text[j:k]]
        i = k
    return ''.join(out + [escape(text[i:])])


def block(kind: str, lang: str) -> str:
    title, body, cta = TEXT[kind][lang]
    note, fallback = FOOTER[lang]
    return f'''
<tr><td style="padding:28px 32px 8px;font-family:Poppins,Segoe UI,Arial,sans-serif;font-size:22px;font-weight:700;color:#003562;line-height:1.3">{escape(title)}</td></tr>
<tr><td style="padding:0 32px 24px;font-family:Segoe UI,Arial,sans-serif;font-size:15px;line-height:1.6;color:#0e2238">{keep_vars(body)}</td></tr>
<tr><td style="padding:0 32px 28px"><a href="{{{{ .ConfirmationURL }}}}" style="display:inline-block;background:#003562;color:#ffffff;font-family:Segoe UI,Arial,sans-serif;font-size:15px;font-weight:600;text-decoration:none;padding:13px 22px;border-radius:6px">{escape(cta)}</a></td></tr>
<tr><td style="padding:0 32px 24px;font-family:Segoe UI,Arial,sans-serif;font-size:13px;line-height:1.5;color:#4a5c70">{escape(note)}<br><br>{escape(fallback)}<br><a href="{{{{ .ConfirmationURL }}}}" style="color:#0b5f86;word-break:break-all">{{{{ .ConfirmationURL }}}}</a></td></tr>
<tr><td style="padding:16px 32px 24px;border-top:1px solid #d5dde7;font-family:Segoe UI,Arial,sans-serif;font-size:12px;color:#4a5c70">CHERCHE &amp; DIAGNOSTIC — {escape(TAGLINE[lang])}</td></tr>'''


def template(kind: str) -> str:
    branches = []
    for n, lang in enumerate(LANGS[1:]):
        branches.append(('{{ if' if n == 0 else '{{ else if') + f' eq .Data.language_code "{lang}" }}}}' + block(kind, lang))
    rows = ''.join(branches) + '{{ else }}' + block(kind, 'fr') + '{{ end }}'
    return f'''<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CHERCHE &amp; DIAGNOSTIC</title></head>
<body style="margin:0;padding:0;background:#f1f4f8">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f4f8;padding:24px 12px"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border:1px solid #d5dde7;border-radius:6px">
<tr><td style="padding:24px 32px 18px;border-bottom:4px double #003562"><img src="{SITE}/brand/logo-horizontal.png" width="220" alt="CHERCHE &amp; DIAGNOSTIC" style="display:block;width:220px;height:auto;border:0"></td></tr>
{rows}
</table></td></tr></table>
</body></html>
'''


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for kind in TEXT:
        (OUT / f'{kind}.html').write_text(template(kind))
    (OUT / 'subjects.json').write_text(json.dumps({k: v['subject'] for k, v in TEXT.items()}, ensure_ascii=False, indent=2) + '\n')
    print('Modèles écrits dans', OUT.relative_to(ROOT))


if __name__ == '__main__':
    main()

// Fonction Vercel : renvoie le pays estimé du visiteur (en-tête ajouté par Vercel), sans rien enregistrer.
export default function handler(req, res) {
  const country = req.headers['x-vercel-ip-country'] || null;
  res.setHeader('Cache-Control', 'private, max-age=3600');
  res.status(200).json({ country });
}

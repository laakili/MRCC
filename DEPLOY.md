# Déploiement de MRCC sur un serveur

## 1. Cloner le repo

```bash
git clone https://github.com/laakili/MRCC.git
cd MRCC
```

## 2. Créer le fichier `.env`

Copie-colle tout le bloc ci-dessous en une seule fois dans le terminal, puis appuie sur Entrée :

```bash
cat > .env << 'EOF'
FLASK_SECRET_KEY=mrcc-maroc-secret-key-2024
FLASK_APP_SECRET_KEY=b7d3f1cbb4f14c53a1c9a0b0458f2e7a
DB_HOST=db
DB_PORT=5432
DB_NAME=geoportal
DB_USER=postgres
DB_PASSWORD=mdpmater_pstgs
MAIL_SERVER=smtp-relay.brevo.com
MAIL_PORT=587
MAIL_USERNAME=82f193001@smtp-brevo.com
MAIL_PASSWORD=2yIm8MzYBJ96c0NC
MAIL_DEFAULT_SENDER=soufiomario@gmail.com
GEOSERVER_URL=http://smartdef.ddns.net:8888/georisque
GEOSERVER_USER=admin
GEOSERVER_PASSWORD=geoserver
BASE_URL=http://localhost:5052/
EOF
```

Vérifier :
```bash
cat .env
```

## 3. Installer Docker (si besoin) et lancer la stack

```bash
sudo ./deploy-docker.sh
```

Ce script installe Docker automatiquement s'il est absent (Ubuntu/Debian), puis lance `docker compose up -d --build` (app Flask + PostgreSQL/PostGIS conteneurisés).

Sur **Mac ou Windows**, installer Docker Desktop manuellement au préalable, puis lancer directement :
```bash
docker compose up -d --build
```

## 4. Vérifier que ça tourne

```bash
curl -I http://localhost:5052/
curl -I http://localhost:5052/recherche-balises
```

Les deux doivent répondre `200 OK`.

## Commandes utiles

```bash
docker compose ps                # état des conteneurs
docker compose logs app -f       # logs de l'app en direct
docker compose down              # arrêter la stack
docker compose up -d              # redémarrer (sans rebuild)
```

## Notes

- Le repo est actuellement **public** sur GitHub (facilite le clone sans authentification). Pour le repasser en privé : `gh repo edit laakili/MRCC --visibility private`.
- `DB_NAME=geoportal` : uniformisé (le code source avait une incohérence historique entre `geoportal` et `geoportal_v1`).
- Pour copier les données de la base distante (`geoai-solutions.ddns.net`) vers la base locale conteneurisée :
  ```bash
  pg_dump -h geoai-solutions.ddns.net -p 4706 -U postgres -d geoportal -Fp --no-owner --no-privileges \
    | docker compose exec -T db psql -U postgres -d geoportal
  ```

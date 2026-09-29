#!/usr/bin/env bash
# Déploiement de l'app MRCC sur un serveur Ubuntu/Debian neuf.
#
# Usage :
#   sudo ./deploy.sh                  # installe deps système + venv + requirements
#   sudo ./deploy.sh --with-local-db  # + installe Postgres/PostGIS local et crée la base "geoportal"
#
# Ce script est idempotent : on peut le relancer sans risque.

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WITH_LOCAL_DB=false
[[ "${1:-}" == "--with-local-db" ]] && WITH_LOCAL_DB=true

if [[ "$EUID" -ne 0 ]]; then
  echo "Lance ce script avec sudo (il installe des paquets système)." >&2
  exit 1
fi

echo "==> Dossier de l'app : $APP_DIR"

echo "==> Installation des dépendances système"
apt-get update
apt-get install -y \
  python3.12 python3.12-venv python3-pip \
  build-essential libpq-dev \
  gdal-bin libgdal-dev \
  libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
  postgresql-client

if [[ "$WITH_LOCAL_DB" == true ]]; then
  echo "==> Installation de PostgreSQL + PostGIS en local"
  apt-get install -y postgresql postgresql-contrib postgis

  DB_PASSWORD="${DB_PASSWORD:?Définis DB_PASSWORD dans l'environnement avant de lancer ce script, ex: DB_PASSWORD=xxx sudo -E ./deploy.sh --with-local-db}"
  sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='postgres'" | grep -q 1 || true
  sudo -u postgres psql -c "ALTER ROLE postgres WITH PASSWORD '${DB_PASSWORD}';"
  sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='geoportal'" | grep -q 1 \
    || sudo -u postgres createdb -O postgres geoportal
  sudo -u postgres psql -d geoportal -c "CREATE EXTENSION IF NOT EXISTS postgis;"

  echo "==> Base locale 'geoportal' prête sur localhost:5432."
  echo "    Pour y copier les données depuis le serveur distant :"
  echo "    pg_dump -h geoai-solutions.ddns.net -p 4706 -U postgres -d geoportal -Fp --no-owner --no-privileges \\"
  echo "      | psql -h localhost -U postgres -d geoportal"
  echo "    Puis mets à jour DB_HOST/DB_PORT dans app.py."
fi

echo "==> Création du venv Python"
cd "$APP_DIR"
python3.12 -m venv venv
source venv/bin/activate

echo "==> Installation des dépendances Python"
pip install --upgrade pip
if [[ -f requirements-freeze.txt ]]; then
  pip install -r requirements-freeze.txt
else
  pip install -r requirements.txt
fi

echo "==> Installation terminée."
echo ""
echo "Lancement rapide (dev) :"
echo "  source venv/bin/activate && python app.py"
echo ""
echo "Lancement production (recommandé) :"
echo "  source venv/bin/activate && gunicorn -k gevent -w 4 -b 0.0.0.0:5052 app:app"
echo ""
echo "Service systemd persistant :"
echo "  sudo cp mrcc.service /etc/systemd/system/mrcc.service"
echo "  sudo systemctl daemon-reload && sudo systemctl enable --now mrcc"

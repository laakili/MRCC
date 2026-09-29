#!/usr/bin/env bash
# Déploiement Docker complet de l'app MRCC sur un serveur Ubuntu/Debian neuf.
# Installe Docker s'il n'est pas déjà présent, puis lance la stack (app + PostGIS).
#
# Usage :
#   sudo ./deploy-docker.sh
#
# Idempotent : peut être relancé sans risque (Docker n'est réinstallé que s'il manque).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$EUID" -ne 0 ]]; then
  echo "Lance ce script avec sudo (installation de Docker + gestion des services)." >&2
  exit 1
fi

if ! command -v docker &> /dev/null; then
  echo "==> Docker non trouvé, installation via le script officiel..."
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
  rm -f /tmp/get-docker.sh
  systemctl enable --now docker
else
  echo "==> Docker déjà installé ($(docker --version))"
fi

if ! docker compose version &> /dev/null; then
  echo "ERREUR: le plugin 'docker compose' n'est pas disponible après installation." >&2
  exit 1
fi

REAL_USER="${SUDO_USER:-$USER}"
if ! id -nG "$REAL_USER" | grep -qw docker; then
  echo "==> Ajout de $REAL_USER au groupe docker (effectif à la prochaine session)"
  usermod -aG docker "$REAL_USER"
fi

cd "$SCRIPT_DIR"

if [[ ! -f .env ]]; then
  echo "ERREUR: fichier .env manquant. Crée-le à partir de .env.example avant de relancer :" >&2
  echo "  cp .env.example .env && nano .env" >&2
  exit 1
fi

echo "==> Lancement de la stack Docker (app + PostGIS)..."
docker compose up -d --build

echo ""
echo "==> Statut des conteneurs :"
docker compose ps

echo ""
echo "==> Terminé. Vérifie avec :"
echo "  curl -I http://localhost:5052/"
echo "  curl -I http://localhost:5052/recherche-balises"

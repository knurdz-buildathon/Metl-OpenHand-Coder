#!/bin/bash
set -euo pipefail

echo "============================================"
echo " Metl Coding Agent - Server Initialization   "
echo "============================================"
echo ""

# --- Step 1: Update system packages ---
echo "[1/6] Updating system packages..."
apt-get update -y
apt-get upgrade -y

# --- Step 2: Install prerequisites ---
echo "[2/6] Installing prerequisites (Docker, Git, curl)..."
apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    ufw

# --- Step 3: Install Docker ---
echo "[3/6] Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sh /tmp/get-docker.sh
    rm /tmp/get-docker.sh
else
    echo "Docker already installed, skipping."
fi

# --- Step 4: Install Docker Compose plugin ---
echo "[4/6] Installing Docker Compose plugin..."
apt-get install -y docker-compose-plugin || {
    DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
    mkdir -p "$DOCKER_CONFIG/cli-plugins"
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o "$DOCKER_CONFIG/cli-plugins/docker-compose"
    chmod +x "$DOCKER_CONFIG/cli-plugins/docker-compose"
}

# --- Step 5: Add current user to docker group ---
echo "[5/6] Configuring Docker permissions..."
if [ -n "${SUDO_USER:-}" ]; then
    usermod -aG docker "$SUDO_USER"
    echo "Added $SUDO_USER to docker group. You may need to log out and back in."
fi

# --- Step 6: Create acme.json for Traefik SSL ---
echo "[6/6] Creating Traefik acme.json for Let's Encrypt..."
touch /root/acme.json
chmod 600 /root/acme.json

echo ""
echo "============================================"
echo " Initialisation complete!                   "
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Clone the repository:"
echo "     git clone https://github.com/your-org/metl-coding-agent.git"
echo "     cd metl-coding-agent"
echo ""
echo "  2. Configure environment:"
echo "     cp .env.example .env"
echo "     nano .env"
echo ""
echo "  3. Deploy:"
echo "     docker compose up -d --build"
echo ""
echo "  4. Initialize database:"
echo "     docker compose exec agent-api alembic upgrade head"
echo ""
echo "  5. Verify at: https://code.metl.run"
echo ""
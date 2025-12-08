#!/bin/bash
set -e

echo "🚀 Installing n8n..."

# Check if already installed
if docker ps | grep -q n8n; then
    echo "✅ n8n already running, skipping installation"
    exit 0
fi

# Remove old container if exists (but not running)
docker rm n8n 2>/dev/null || true

# Update system
export DEBIAN_FRONTEND=noninteractive
apt update
apt upgrade -y

# Install Docker if needed
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    systemctl start docker
    systemctl enable docker
    rm get-docker.sh
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose V2 plugin if needed
if ! docker compose version &> /dev/null; then
    echo "📦 Installing Docker Compose V2..."
    DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
    mkdir -p $DOCKER_CONFIG/cli-plugins
    curl -SL https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64 \
        -o $DOCKER_CONFIG/cli-plugins/docker-compose
    chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
else
    echo "✅ Docker Compose already installed"
fi

# Create directory
mkdir -p /opt/n8n/data

# Fix permissions for n8n user (UID 1000)
chown -R 1000:1000 /opt/n8n/data
chmod -R 755 /opt/n8n/data

# Create .env file with password
cat > /opt/n8n/.env <<'EOF'
N8N_PASSWORD={{N8N_PASSWORD}}
EOF

# Create docker-compose.yml
cat > /opt/n8n/docker-compose.yml <<'EOF'
version: '3.8'

services:
  n8n:
    image: n8nio/n8n:latest
    container_name: n8n
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=${N8N_PASSWORD}
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - N8N_PROTOCOL=http
      - N8N_SECURE_COOKIE=false
      - GENERIC_TIMEZONE=UTC
      - N8N_LOG_LEVEL=info
    volumes:
      - ./data:/home/node/.n8n
EOF

# Start n8n
cd /opt/n8n
docker compose up -d

# Wait for n8n to start
echo "⏳ Waiting for n8n to start..."
sleep 15

# Check if running
if docker ps | grep -q n8n; then
    echo "✅ n8n started successfully"
else
    echo "❌ n8n failed to start"
    docker logs n8n
    exit 1
fi

# Configure firewall if ufw installed
if command -v ufw &> /dev/null; then
    ufw allow 5678/tcp
    ufw allow 22/tcp
    echo "y" | ufw enable || true
fi

echo "✅ n8n installation complete!"
echo "Access at: http://$(curl -s ifconfig.me):5678"
echo "Username: admin"
echo "Password: {{N8N_PASSWORD}}"

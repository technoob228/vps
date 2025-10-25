#!/bin/bash
set -e

echo "🚀 Installing Vaultwarden..."

# Check if already installed
if docker ps | grep -q vaultwarden; then
    echo "✅ Vaultwarden already running, skipping installation"
    exit 0
fi

# Remove old container
docker rm vaultwarden 2>/dev/null || true

# Update system
export DEBIAN_FRONTEND=noninteractive
apt update
apt upgrade -y

# Install Docker
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

# Create directory
mkdir -p /opt/vaultwarden/data

# Save admin token
echo "{{ADMIN_TOKEN}}" > /opt/vaultwarden/admin_token.txt

# Run Vaultwarden container
echo "🐳 Starting Vaultwarden container..."
docker run -d \
  --name=vaultwarden \
  --restart=unless-stopped \
  -e DOMAIN={{DOMAIN}} \
  -e ADMIN_TOKEN={{ADMIN_TOKEN}} \
  -e SIGNUPS_ALLOWED=true \
  -e INVITATIONS_ALLOWED=true \
  -e WEBSOCKET_ENABLED=true \
  -e LOG_LEVEL=info \
  -p 8080:80 \
  -v /opt/vaultwarden/data:/data \
  vaultwarden/server:latest

# Wait for container to start
echo "⏳ Waiting for Vaultwarden to start..."
sleep 10

# Check if running
if docker ps | grep -q vaultwarden; then
    echo "✅ Vaultwarden started successfully"
else
    echo "❌ Vaultwarden failed to start"
    docker logs vaultwarden
    exit 1
fi

# Configure firewall
if command -v ufw &> /dev/null; then
    ufw allow 8080/tcp
    ufw allow 22/tcp
    echo "y" | ufw enable || true
fi

echo "✅ Vaultwarden installation complete!"
echo "Access at: {{DOMAIN}}"
echo "Admin panel: {{DOMAIN}}/admin"
echo "Admin token: {{ADMIN_TOKEN}}"
echo ""
echo "Next steps:"
echo "1. Create your account at the main URL"
echo "2. Install Bitwarden browser extension"
echo "3. Point extension to your server URL"
echo "4. Access admin panel with the token for advanced settings"

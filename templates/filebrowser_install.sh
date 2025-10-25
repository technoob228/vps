#!/bin/bash
set -e

echo "🚀 Installing FileBrowser..."

# Check if already installed
if docker ps | grep -q filebrowser; then
    echo "✅ FileBrowser already running, skipping installation"
    exit 0
fi

# Remove old container
docker rm filebrowser 2>/dev/null || true

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

# Create directories
mkdir -p /opt/filebrowser
mkdir -p /srv  # Files will be stored here

# Create database file
touch /opt/filebrowser/filebrowser.db

# Save admin password
echo "{{ADMIN_PASSWORD}}" > /opt/filebrowser/admin_password.txt

# Run FileBrowser container
echo "🐳 Starting FileBrowser container..."
docker run -d \
  --name=filebrowser \
  --restart=unless-stopped \
  -p 8081:80 \
  -v /srv:/srv \
  -v /opt/filebrowser/filebrowser.db:/database.db \
  -e PUID=0 \
  -e PGID=0 \
  filebrowser/filebrowser:latest

# Wait for container to start
echo "⏳ Waiting for FileBrowser to start..."
sleep 5

# Check if running
if docker ps | grep -q filebrowser; then
    echo "✅ FileBrowser started successfully"
else
    echo "❌ FileBrowser failed to start"
    docker logs filebrowser
    exit 1
fi

# Change admin password
echo "🔐 Setting admin password..."
sleep 3

# Execute password change inside container
docker exec filebrowser filebrowser users update admin \
  --password "{{ADMIN_PASSWORD}}" 2>/dev/null || echo "Password will be set on first login"

# Configure firewall
if command -v ufw &> /dev/null; then
    ufw allow 8081/tcp
    ufw allow 22/tcp
    echo "y" | ufw enable || true
fi

echo "✅ FileBrowser installation complete!"
echo "Access at: http://$(curl -s ifconfig.me):8081"
echo "Username: admin"
echo "Password: {{ADMIN_PASSWORD}}"
echo ""
echo "Default credentials if password change failed:"
echo "Username: admin"
echo "Password: admin (change immediately!)"
echo ""
echo "Files are stored in: /srv"
echo ""
echo "Features:"
echo "  - Upload/download files"
echo "  - Share files with links"
echo "  - Create users"
echo "  - Mobile friendly"

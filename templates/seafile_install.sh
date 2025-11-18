#!/bin/bash
set -e

echo "🚀 Installing Seafile..."

# Check if already installed
if docker ps | grep -q seafile; then
    echo "✅ Seafile already running, skipping installation"
    exit 0
fi

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

# Install Docker Compose V2
if ! docker compose version &> /dev/null; then
    echo "📦 Installing Docker Compose V2..."
    DOCKER_CONFIG=${DOCKER_CONFIG:-$HOME/.docker}
    mkdir -p $DOCKER_CONFIG/cli-plugins
    curl -SL https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64 \
        -o $DOCKER_CONFIG/cli-plugins/docker-compose
    chmod +x $DOCKER_CONFIG/cli-plugins/docker-compose
fi

# Create directories
mkdir -p /opt/seafile/data
mkdir -p /opt/seafile/mysql

# Save credentials
cat > /opt/seafile/credentials.txt <<EOF
{{ADMIN_EMAIL}}
{{ADMIN_PASSWORD}}
EOF

# Create docker-compose.yml
cat > /opt/seafile/docker-compose.yml <<'EOF'
version: '3.8'

services:
  db:
    image: mariadb:10.11
    container_name: seafile-mysql
    restart: unless-stopped
    environment:
      - MYSQL_ROOT_PASSWORD={{DB_PASSWORD}}
      - MYSQL_LOG_CONSOLE=true
      - MARIADB_AUTO_UPGRADE=1
    volumes:
      - ./mysql:/var/lib/mysql
    networks:
      - seafile-net

  memcached:
    image: memcached:1.6-alpine
    container_name: seafile-memcached
    restart: unless-stopped
    entrypoint: memcached -m 256
    networks:
      - seafile-net

  seafile:
    image: seafileltd/seafile-mc:latest
    container_name: seafile
    restart: unless-stopped
    ports:
      - "8000:80"
    volumes:
      - ./data:/shared
    environment:
      - DB_HOST=db
      - DB_ROOT_PASSWD={{DB_PASSWORD}}
      - TIME_ZONE=Etc/UTC
      - SEAFILE_ADMIN_EMAIL={{ADMIN_EMAIL}}
      - SEAFILE_ADMIN_PASSWORD={{ADMIN_PASSWORD}}
      - SEAFILE_SERVER_LETSENCRYPT=false
      - SEAFILE_SERVER_HOSTNAME={{DOMAIN}}
    depends_on:
      - db
      - memcached
    networks:
      - seafile-net

networks:
  seafile-net:
    driver: bridge
EOF

# Start services
echo "🐳 Starting Seafile services (MariaDB + Memcached + Seafile)..."
cd /opt/seafile
docker compose up -d

# Wait for database to initialize
echo "⏳ Waiting for database to initialize (60 seconds)..."
sleep 60

# Wait for Seafile to start
echo "⏳ Waiting for Seafile to start (this can take 2-3 minutes)..."
sleep 90

# Check if running
if docker ps | grep -q seafile; then
    echo "✅ Seafile started successfully"
else
    echo "❌ Seafile failed to start"
    docker logs seafile
    exit 1
fi

# Fix Seafile configuration for file uploads
echo "🔧 Configuring Seafile for proper file uploads..."

# Wait a bit more for Seafile to fully initialize
sleep 30

# Configure FILE_SERVER_ROOT in seahub_settings.py
docker exec seafile bash -c "cat >> /opt/seafile/conf/seahub_settings.py << 'EOFPY'

# File upload configuration
FILE_SERVER_ROOT = 'http://{{SERVER_IP}}:8000/seafhttp'
MAX_UPLOAD_FILE_SIZE = 53687091200  # 50GB in bytes
FILE_UPLOAD_MAX_MEMORY_SIZE = 209715200  # 200MB in bytes
EOFPY"

# Fix nginx configuration - remove http:// from server_name
docker exec seafile bash -c "sed -i 's|server_name http://{{SERVER_IP}}|server_name {{SERVER_IP}}|g' /etc/nginx/sites-enabled/seafile.nginx.conf || true"

# Increase nginx upload size limit to 50GB
docker exec seafile bash -c "sed -i 's|client_max_body_size.*|client_max_body_size 50G;|g' /etc/nginx/sites-enabled/seafile.nginx.conf || true"

# Reload nginx inside container
docker exec seafile bash -c "nginx -s reload || true"

echo "✅ Seafile configuration updated!"
echo "   - FILE_SERVER_ROOT configured"
echo "   - Max upload size: 50GB"
echo "   - Nginx reloaded"

# Configure firewall
if command -v ufw &> /dev/null; then
    ufw allow 8000/tcp
    ufw allow 22/tcp
    echo "y" | ufw enable || true
fi

echo "✅ Seafile installation complete!"
echo ""
echo "Web Interface: {{DOMAIN}}"
echo "Email: {{ADMIN_EMAIL}}"
echo "Password: {{ADMIN_PASSWORD}}"
echo ""
echo "📱 Mobile Apps (FREE):"
echo "iOS: https://apps.apple.com/app/seafile-pro/id639202512"
echo "Android: https://play.google.com/store/apps/details?id=com.seafile.seadroid2"
echo ""
echo "Next steps:"
echo "1. Login to web interface"
echo "2. Download mobile app"
echo "3. Add server: {{DOMAIN}}"
echo "4. Enable auto photo upload in app"
echo ""
echo "Note: First startup takes 2-3 minutes. If not accessible, wait and try again."

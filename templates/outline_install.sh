#!/bin/bash
set -e

echo "🚀 Installing Outline..."

# Check if already installed
if docker ps | grep -q outline; then
    echo "✅ Outline already running, skipping installation"
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

# Create directory
mkdir -p /opt/outline

# Create .env file
cat > /opt/outline/.env <<EOF
SECRET_KEY={{SECRET_KEY}}
UTILS_SECRET={{UTILS_SECRET}}
DATABASE_URL=postgres://outline:outline@postgres:5432/outline
DATABASE_URL_TEST=postgres://outline:outline@postgres:5432/outline-test
PGSSLMODE=disable
REDIS_URL=redis://redis:6379
URL=http://{{SERVER_IP}}:3000
PORT=3000
# For production, configure SMTP:
# SMTP_HOST=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your-email@gmail.com
# SMTP_PASSWORD=your-app-password
# SMTP_FROM_EMAIL=your-email@gmail.com
# SMTP_SECURE=true
EOF

# Create docker-compose.yml
cat > /opt/outline/docker-compose.yml <<'EOF'
version: '3.8'

services:
  outline:
    image: outlinewiki/outline:latest
    container_name: outline
    restart: unless-stopped
    ports:
      - "3000:3000"
    env_file:
      - .env
    depends_on:
      - postgres
      - redis
    volumes:
      - ./data:/var/lib/outline/data

  postgres:
    image: postgres:15-alpine
    container_name: outline-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: outline
      POSTGRES_PASSWORD: outline
      POSTGRES_DB: outline
    volumes:
      - ./postgres-data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    container_name: outline-redis
    restart: unless-stopped
    volumes:
      - ./redis-data:/data
EOF

# Start services
echo "🐳 Starting Outline services (PostgreSQL + Redis + Outline)..."
cd /opt/outline
docker compose up -d

# Wait for services to start
echo "⏳ Waiting for services to start (this can take 2-3 minutes)..."
sleep 60

# Check if running
if docker ps | grep -q outline; then
    echo "✅ Outline started successfully"
else
    echo "❌ Outline failed to start"
    docker logs outline
    exit 1
fi

# Configure firewall
if command -v ufw &> /dev/null; then
    ufw allow 3000/tcp
    ufw allow 22/tcp
    echo "y" | ufw enable || true
fi

echo "✅ Outline installation complete!"
echo "Access at: http://{{SERVER_IP}}:3000"
echo ""
echo "⚠️  IMPORTANT: Outline uses magic link authentication"
echo "To login:"
echo "1. Visit the URL and enter your email"
echo "2. Without SMTP configured, check magic link in logs:"
echo "   docker logs outline | grep 'token='"
echo ""
echo "For production use, configure SMTP in /opt/outline/.env"

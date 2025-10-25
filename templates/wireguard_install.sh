#!/bin/bash
set -e

echo "🚀 Installing WireGuard UI..."

# Check if already installed
if docker ps | grep -q wireguard-ui; then
    echo "✅ WireGuard UI already running, skipping installation"
    exit 0
fi

# Remove old container if exists
docker rm wireguard-ui 2>/dev/null || true

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

# Install WireGuard kernel module
echo "📦 Installing WireGuard kernel module..."
apt install -y wireguard wireguard-tools

# Create directories
mkdir -p /opt/wireguard-ui
mkdir -p /etc/wireguard

# Generate random password if not exists
if [ ! -f /opt/wireguard-ui/admin_password.txt ]; then
    ADMIN_PASSWORD=$(openssl rand -base64 16)
    echo $ADMIN_PASSWORD > /opt/wireguard-ui/admin_password.txt
else
    ADMIN_PASSWORD=$(cat /opt/wireguard-ui/admin_password.txt)
fi

echo "🐳 Starting WireGuard UI container..."

# Run WireGuard UI container
docker run -d \
  --name=wireguard-ui \
  --restart=unless-stopped \
  --cap-add=NET_ADMIN \
  --cap-add=SYS_MODULE \
  -e WGUI_USERNAME=admin \
  -e WGUI_PASSWORD=$ADMIN_PASSWORD \
  -e WG_CONF_TEMPLATE=wg_confs/wg0.conf \
  -p 5000:5000 \
  -p 51820:51820/udp \
  -v /opt/wireguard-ui:/app/db \
  -v /etc/wireguard:/etc/wireguard \
  ngoduykhanh/wireguard-ui:latest

# Wait for container to start
echo "⏳ Waiting for WireGuard UI to start..."
sleep 10

# Check if running
if docker ps | grep -q wireguard-ui; then
    echo "✅ WireGuard UI started successfully"
else
    echo "❌ WireGuard UI failed to start"
    docker logs wireguard-ui
    exit 1
fi

# Configure firewall
if command -v ufw &> /dev/null; then
    ufw allow 5000/tcp
    ufw allow 51820/udp
    ufw allow 22/tcp
    echo "y" | ufw enable || true
fi

# Enable IP forwarding
echo "🌐 Enabling IP forwarding..."
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
    sysctl -p
fi

echo "✅ WireGuard UI installation complete!"
echo "Access at: http://$(curl -s ifconfig.me):5000"
echo "Username: admin"
echo "Password: $ADMIN_PASSWORD"
echo ""
echo "Note: Configure WireGuard interface in the UI before creating clients"

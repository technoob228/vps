#!/bin/bash
set -e

echo "🚀 Installing 3X-UI VPN Panel..."

# Check if already installed
if systemctl is-active --quiet x-ui 2>/dev/null; then
    echo "✅ 3X-UI already running, skipping installation"
    exit 0
fi

# Update system
export DEBIAN_FRONTEND=noninteractive
apt update
apt upgrade -y

# Install required packages
apt install -y curl wget tar

# Create directory
mkdir -p /opt/3x-ui

# Download and install 3X-UI
echo "📦 Downloading 3X-UI..."
cd /tmp

# Get latest version
LATEST_VERSION=$(curl -s https://api.github.com/repos/MHSanaei/3x-ui/releases/latest | grep tag_name | cut -d '"' -f 4)

# Detect architecture
ARCH=$(uname -m)
case $ARCH in
    x86_64)
        ARCH_TYPE="amd64"
        ;;
    aarch64)
        ARCH_TYPE="arm64"
        ;;
    *)
        echo "❌ Unsupported architecture: $ARCH"
        exit 1
        ;;
esac

# Download
wget -q https://github.com/MHSanaei/3x-ui/releases/download/${LATEST_VERSION}/x-ui-linux-${ARCH_TYPE}.tar.gz

# Extract
tar -xzf x-ui-linux-${ARCH_TYPE}.tar.gz -C /usr/local/

# Create systemd service
cat > /etc/systemd/system/x-ui.service <<'EOF'
[Unit]
Description=3X-UI Panel
After=network.target

[Service]
Type=simple
WorkingDirectory=/usr/local/x-ui
ExecStart=/usr/local/x-ui/x-ui
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd
systemctl daemon-reload

# Enable and start service
systemctl enable x-ui
systemctl start x-ui

# Wait for service to start
echo "⏳ Waiting for 3X-UI to start..."
sleep 10

# Set admin credentials
echo "🔐 Setting admin credentials..."
cd /usr/local/x-ui

# Use x-ui command to set username and password
./x-ui setting -username {{ADMIN_USERNAME}} 2>/dev/null || true
./x-ui setting -password {{ADMIN_PASSWORD}} 2>/dev/null || true

# Save credentials
cat > /opt/3x-ui/credentials.txt <<EOF
{{ADMIN_USERNAME}}
{{ADMIN_PASSWORD}}
EOF

# Check if service is running
if systemctl is-active --quiet x-ui; then
    echo "✅ 3X-UI started successfully"
else
    echo "❌ 3X-UI failed to start"
    systemctl status x-ui
    exit 1
fi

# Configure firewall
if command -v ufw &> /dev/null; then
    ufw allow 54321/tcp  # Panel port
    ufw allow 22/tcp
    # Open common VPN ports
    ufw allow 443/tcp
    ufw allow 10000:20000/tcp
    ufw allow 10000:20000/udp
    echo "y" | ufw enable || true
fi

# Enable BBR for better performance
echo "⚡ Enabling BBR congestion control..."
if ! grep -q "net.core.default_qdisc=fq" /etc/sysctl.conf; then
    echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
    echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
    sysctl -p
fi

echo "✅ 3X-UI installation complete!"
echo "Panel URL: http://$(curl -s ifconfig.me):54321"
echo "Username: {{ADMIN_USERNAME}}"
echo "Password: {{ADMIN_PASSWORD}}"
echo ""
echo "Supported protocols:"
echo "  - VMess (recommended for China/Russia)"
echo "  - VLESS (recommended for Iran)"
echo "  - Trojan"
echo "  - Shadowsocks"
echo ""
echo "Next steps:"
echo "1. Login to the panel"
echo "2. Go to 'Inbounds' and create new connection"
echo "3. Choose protocol (VMess or VLESS recommended)"
echo "4. Generate QR code or link for clients"
echo "5. Install v2rayN (Windows), v2rayNG (Android), or Shadowrocket (iOS)"

# Clean up
cd /
rm -rf /tmp/x-ui-linux-${ARCH_TYPE}.tar.gz

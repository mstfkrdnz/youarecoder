#!/bin/bash
# Traefik v2.10 Installation Script for YouAreCoder.com
# Server: 37.27.21.167

set -e

echo "=== YouAreCoder Traefik Installation ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root"
    exit 1
fi

# Variables
TRAEFIK_VERSION="2.10.7"
TRAEFIK_URL="https://github.com/traefik/traefik/releases/download/v${TRAEFIK_VERSION}/traefik_v${TRAEFIK_VERSION}_linux_amd64.tar.gz"

echo "📦 Installing Traefik v${TRAEFIK_VERSION}..."

# Download Traefik
cd /tmp
curl -L "${TRAEFIK_URL}" -o traefik.tar.gz
tar -xzf traefik.tar.gz
mv traefik /usr/local/bin/
chmod +x /usr/local/bin/traefik
rm traefik.tar.gz

# Verify installation
traefik version

# Create directories
echo "📁 Creating Traefik directories..."
mkdir -p /etc/traefik/config
mkdir -p /var/log/traefik
chmod 755 /etc/traefik
chmod 755 /etc/traefik/config
chmod 755 /var/log/traefik

# Create acme.json for Let's Encrypt
touch /etc/traefik/acme.json
chmod 600 /etc/traefik/acme.json

# Copy configuration files
echo "⚙️  Installing configuration files..."
cp traefik.yml /etc/traefik/
cp config/flask-app.yml /etc/traefik/config/
cp config/workspaces.yml /etc/traefik/config/

# Install systemd service
echo "🔧 Installing systemd service..."
cp traefik.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable traefik.service

# Start Traefik
echo "🚀 Starting Traefik..."
systemctl start traefik.service

# Check status
echo "✅ Traefik installation complete!"
echo ""
systemctl status traefik.service --no-pager

echo ""
echo "🔍 Next Steps:"
echo "1. Update DNS: Point *.youarecoder.com to this server (37.27.21.167)"
echo "2. Wait for Let's Encrypt SSL certificates to be issued"
echo "3. Check logs: journalctl -u traefik.service -f"
echo "4. Start Flask app on port 5000"

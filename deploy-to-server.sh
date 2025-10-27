#!/bin/bash
# Automated deployment script for YouAreCoder
# Run this on the production server (37.27.21.167)

set -e

echo "=== YouAreCoder Deployment Script ==="
echo "Server: $(hostname)"
echo "Date: $(date)"
echo ""

# 1. Install Traefik
echo "📦 Step 1: Installing Traefik v2.10.7..."
cd /tmp
if [ ! -f /usr/local/bin/traefik ]; then
    curl -L https://github.com/traefik/traefik/releases/download/v2.10.7/traefik_v2.10.7_linux_amd64.tar.gz -o traefik.tar.gz
    tar -xzf traefik.tar.gz
    mv traefik /usr/local/bin/
    chmod +x /usr/local/bin/traefik
    rm traefik.tar.gz
    echo "✅ Traefik installed"
else
    echo "✅ Traefik already installed"
fi

traefik version

# 2. Create directories
echo ""
echo "📁 Step 2: Creating directories..."
mkdir -p /etc/traefik/config
mkdir -p /var/log/traefik
mkdir -p /var/log/youarecoder
chmod 755 /etc/traefik /etc/traefik/config /var/log/traefik /var/log/youarecoder

touch /etc/traefik/acme.json
chmod 600 /etc/traefik/acme.json
echo "✅ Directories created"

# 3. Copy Traefik configurations
echo ""
echo "⚙️  Step 3: Installing Traefik configurations..."
cp traefik/traefik.yml /etc/traefik/
cp traefik/config/flask-app.yml /etc/traefik/config/
cp traefik/config/workspaces.yml /etc/traefik/config/
cp traefik/traefik.service /etc/systemd/system/
echo "✅ Configurations copied"

# 4. Start Traefik
echo ""
echo "🚀 Step 4: Starting Traefik..."
systemctl daemon-reload
systemctl enable traefik.service
systemctl restart traefik.service
sleep 2
systemctl status traefik.service --no-pager
echo "✅ Traefik started"

# 5. Install Python dependencies
echo ""
echo "🐍 Step 5: Installing Python dependencies..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
echo "✅ Python dependencies installed"

# 6. Create .env file
echo ""
echo "📝 Step 6: Creating .env file..."
if [ ! -f ".env" ]; then
    cat > .env << 'ENV_FILE'
FLASK_APP=app
FLASK_ENV=production
SECRET_KEY=$(openssl rand -hex 32)
DATABASE_URL=postgresql://youarecoder_user:YouAreCoderDB2025@localhost:5432/youarecoder
WORKSPACE_PORT_RANGE_START=8001
WORKSPACE_PORT_RANGE_END=8100
WORKSPACE_BASE_DIR=/workspaces
ENV_FILE
    echo "✅ .env created"
else
    echo "✅ .env already exists"
fi

# 7. Run database migrations
echo ""
echo "💾 Step 7: Running database migrations..."
source venv/bin/activate
export FLASK_APP=app
flask db upgrade
echo "✅ Database migrated"

# 8. Create Flask systemd service
echo ""
echo "🔧 Step 8: Creating Flask systemd service..."
cat > /etc/systemd/system/youarecoder.service << 'SERVICE_FILE'
[Unit]
Description=YouAreCoder Flask Application
After=network.target postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/youarecoder
Environment="PATH=/root/youarecoder/venv/bin"
ExecStart=/root/youarecoder/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile /var/log/youarecoder/access.log \
    --error-logfile /var/log/youarecoder/error.log \
    "app:create_app()"

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SERVICE_FILE
echo "✅ Service file created"

# 9. Start Flask application
echo ""
echo "🚀 Step 9: Starting Flask application..."
systemctl daemon-reload
systemctl enable youarecoder.service
systemctl restart youarecoder.service
sleep 3
systemctl status youarecoder.service --no-pager
echo "✅ Flask application started"

# 10. Verification
echo ""
echo "🔍 Step 10: Verification..."
echo ""
echo "Traefik status:"
systemctl is-active traefik.service

echo ""
echo "Flask status:"
systemctl is-active youarecoder.service

echo ""
echo "SSL Certificate (wait 1-2 minutes for Let's Encrypt):"
ls -lh /etc/traefik/acme.json

echo ""
echo "Test local Flask:"
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000 || echo "Flask not responding yet"

echo ""
echo "=== ✅ Deployment Complete! ==="
echo ""
echo "Next steps:"
echo "1. Wait 1-2 minutes for SSL certificate"
echo "2. Visit: https://youarecoder.com"
echo "3. Register first user"
echo ""
echo "Monitor logs:"
echo "  journalctl -u traefik.service -f"
echo "  journalctl -u youarecoder.service -f"

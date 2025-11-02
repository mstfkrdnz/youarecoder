#!/bin/bash
#
# Install base runtimes on production server
# Installs: Python 3.11, Node.js 20 LTS, Go 1.21, build-essential
#
# Usage: sudo bash install_base_runtimes.sh

set -e  # Exit on error

echo "========================================"
echo "Installing Base Runtimes"
echo "========================================"

# Update package list
echo "Updating package list..."
apt-get update

# Install build-essential (gcc, g++, make, etc.)
echo ""
echo "Installing build-essential..."
apt-get install -y build-essential

# Install Python 3.11 (if not already installed)
echo ""
echo "Installing Python 3.11..."
if ! command -v python3.11 &> /dev/null; then
    apt-get install -y software-properties-common
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update
    apt-get install -y python3.11 python3.11-venv python3.11-dev python3-pip
    echo "Python 3.11 installed successfully"
else
    echo "Python 3.11 already installed"
fi

# Install Node.js 20 LTS (if not already installed)
echo ""
echo "Installing Node.js 20 LTS..."
if ! command -v node &> /dev/null || [[ $(node -v | cut -d'v' -f2 | cut -d'.' -f1) -lt 20 ]]; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs
    echo "Node.js 20 installed successfully"
else
    echo "Node.js 20+ already installed"
fi

# Install Go 1.21 (if not already installed)
echo ""
echo "Installing Go 1.21..."
if ! command -v go &> /dev/null || [[ $(go version | grep -oP 'go\K[0-9.]+' | cut -d'.' -f2) -lt 21 ]]; then
    GO_VERSION="1.21.13"
    wget -q "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" -O /tmp/go.tar.gz
    rm -rf /usr/local/go
    tar -C /usr/local -xzf /tmp/go.tar.gz
    rm /tmp/go.tar.gz

    # Add Go to PATH if not already there
    if ! grep -q "/usr/local/go/bin" /etc/profile; then
        echo 'export PATH=$PATH:/usr/local/go/bin' >> /etc/profile
    fi

    export PATH=$PATH:/usr/local/go/bin
    echo "Go 1.21 installed successfully"
else
    echo "Go 1.21+ already installed"
fi

# Verify installations
echo ""
echo "========================================"
echo "Verification"
echo "========================================"

echo ""
echo "Build tools:"
gcc --version | head -n1
g++ --version | head -n1
make --version | head -n1

echo ""
echo "Python:"
python3.11 --version
pip3 --version

echo ""
echo "Node.js & npm:"
node --version
npm --version

echo ""
echo "Go:"
/usr/local/go/bin/go version

echo ""
echo "========================================"
echo "Base runtimes installation complete!"
echo "========================================"

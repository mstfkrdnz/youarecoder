#!/bin/bash
#
# Enable disk quotas on the root filesystem for user workspace quota enforcement
#
# IMPORTANT: This script requires a system reboot to take effect
#
# Usage: sudo bash enable_disk_quotas.sh

set -e  # Exit on error

echo "========================================"
echo "Enable Disk Quotas for Workspace System"
echo "========================================"

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "ERROR: This script must be run as root (use sudo)"
   exit 1
fi

# Step 1: Install quota package
echo ""
echo "[1/5] Installing quota package..."
if ! command -v quotacheck &> /dev/null; then
    apt-get update
    apt-get install -y quota quotatool
    echo "✓ Quota package installed"
else
    echo "✓ Quota package already installed"
fi

# Step 2: Check filesystem type
echo ""
echo "[2/5] Checking filesystem configuration..."
ROOT_FILESYSTEM=$(df / | tail -1 | awk '{print $1}')
FS_TYPE=$(df -T / | tail -1 | awk '{print $2}')
echo "Root filesystem: $ROOT_FILESYSTEM ($FS_TYPE)"

if [[ "$FS_TYPE" != "ext4" ]]; then
    echo "WARNING: Filesystem is not ext4. Quota support may vary."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 3: Backup /etc/fstab
echo ""
echo "[3/5] Backing up /etc/fstab..."
cp /etc/fstab /etc/fstab.backup.$(date +%Y%m%d_%H%M%S)
echo "✓ Backup created at /etc/fstab.backup.$(date +%Y%m%d_%H%M%S)"

# Step 4: Enable quotas in /etc/fstab
echo ""
echo "[4/5] Configuring /etc/fstab for user quotas..."

# Find the root filesystem entry in fstab
FSTAB_LINE=$(grep -E "^$ROOT_FILESYSTEM\s+/\s+" /etc/fstab || true)

if [[ -z "$FSTAB_LINE" ]]; then
    # Try with UUID
    ROOT_UUID=$(blkid -s UUID -o value $ROOT_FILESYSTEM)
    FSTAB_LINE=$(grep -E "^UUID=$ROOT_UUID\s+/\s+" /etc/fstab || true)
fi

if [[ -z "$FSTAB_LINE" ]]; then
    echo "ERROR: Could not find root filesystem entry in /etc/fstab"
    echo "Please manually add 'usrquota' option to root filesystem mount options"
    exit 1
fi

# Check if usrquota is already present
if echo "$FSTAB_LINE" | grep -q "usrquota"; then
    echo "✓ usrquota already enabled in /etc/fstab"
else
    echo "Current fstab entry:"
    echo "$FSTAB_LINE"
    echo ""
    echo "Adding usrquota option..."

    # Add usrquota to mount options (4th column)
    # This handles both "errors=remount-ro" and "defaults" style options
    sed -i.bak "s|\(^[^#].*\s/\s.*\s\)\([^ ]*\)\(\s.*\)|\1\2,usrquota\3|" /etc/fstab

    echo "✓ Updated /etc/fstab with usrquota option"
    echo "New fstab entry:"
    grep -E "^[^#].*\s/\s+" /etc/fstab || true
fi

# Step 5: Initialize quota database
echo ""
echo "[5/5] Creating quota database files..."
echo ""
echo "IMPORTANT NOTES:"
echo "1. The system MUST be rebooted for quota changes to take effect"
echo "2. After reboot, run the following commands as root:"
echo ""
echo "   # Initialize quota database"
echo "   quotacheck -cugm /"
echo ""
echo "   # Enable quotas"
echo "   quotaon -v /"
echo ""
echo "   # Verify quotas are active"
echo "   quotaon -p /"
echo ""
echo "========================================"
echo "Setup Complete - REBOOT REQUIRED"
echo "========================================"
echo ""
read -p "Would you like to reboot now? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting system in 5 seconds..."
    sleep 5
    reboot
else
    echo "Please remember to reboot the system manually for changes to take effect."
    echo "After reboot, run the quota initialization commands shown above."
fi

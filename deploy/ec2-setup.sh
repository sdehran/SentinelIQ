#!/bin/bash
# ══════════════════════════════════════════════════════════
# SentinelIQ — EC2 Instance Setup Script
# Instance: c7i-flex.large (2 vCPU, 4 GB RAM, Ubuntu 22.04)
# Cost: ~$0.09/hr on-demand
# Run ONCE after launching the instance
# Usage: chmod +x ec2-setup.sh && sudo ./ec2-setup.sh
# ══════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════"
echo "  SentinelIQ — EC2 Setup"
echo "  Instance: c7i-flex.large (2 vCPU, 4 GB)"
echo "═══════════════════════════════════════════"

# ── System Update ──
echo ""
echo "📦 Updating system packages..."
apt-get update -y
apt-get upgrade -y

# ── Install Docker ──
echo ""
echo "🐳 Installing Docker..."
apt-get install -y ca-certificates curl gnupg lsb-release git

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

systemctl start docker
systemctl enable docker
usermod -aG docker ubuntu

# ── Install Docker Compose (standalone binary) ──
echo ""
echo "📦 Installing Docker Compose..."
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d '"' -f 4)
curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# ── Create application directory ──
echo ""
echo "📁 Creating application directory..."
mkdir -p /opt/sentineliq
chown ubuntu:ubuntu /opt/sentineliq

# ── Create 1 GB swap (safety net) ──
echo ""
echo "💾 Creating 1 GB swap (safety net)..."
if [ ! -f /swapfile ]; then
    dd if=/dev/zero of=/swapfile bs=128M count=8
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile swap swap defaults 0 0' >> /etc/fstab
    echo "   ✓ Swap enabled (1 GB)"
else
    echo "   ✓ Swap already exists"
fi

# ── Verify ──
echo ""
echo "🔍 Verifying installation..."
docker --version
docker-compose --version

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ Setup Complete!"
echo "═══════════════════════════════════════════"
echo ""
echo "  Instance: c7i-flex.large"
echo "  RAM: 4 GB + 1 GB swap"
echo "  OS: Ubuntu 22.04"
echo ""
echo "  Security Group (set in AWS Console):"
echo "   ┌─────────┬──────┬─────────────────┐"
echo "   │ Type    │ Port │ Source          │"
echo "   ├─────────┼──────┼─────────────────┤"
echo "   │ SSH     │ 22   │ Your IP only    │"
echo "   │ HTTP    │ 80   │ 0.0.0.0/0      │"
echo "   └─────────┴──────┴─────────────────┘"
echo ""
echo "  Next steps:"
echo "  ─────────────────────────────────────"
echo "  1. Log out and back in (docker group):"
echo "     exit"
echo ""
echo "  2. Clone your repo:"
echo "     cd /opt/sentineliq"
echo "     git clone https://github.com/<you>/sentineliq.git ."
echo ""
echo "  3. Create .env file:"
echo "     cp .env.example .env"
echo "     nano .env"
echo ""
echo "  4. Deploy:"
echo "     docker-compose up -d --build"
echo ""
echo "  5. Open in browser:"
echo "     http://<your-ec2-public-ip>"
echo ""
echo "═══════════════════════════════════════════"

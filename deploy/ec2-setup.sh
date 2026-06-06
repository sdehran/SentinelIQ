#!/bin/bash
# ══════════════════════════════════════════════════════════
# SentinelIQ — EC2 Instance Setup Script
# Run this ONCE on a fresh Amazon Linux 2023 / Ubuntu 22.04 EC2 instance
# Usage: chmod +x ec2-setup.sh && sudo ./ec2-setup.sh
# ══════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════"
echo "  SentinelIQ — EC2 Environment Setup"
echo "═══════════════════════════════════════════"

# ── Detect OS ──
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "❌ Cannot detect OS. Exiting."
    exit 1
fi

echo "📦 Detected OS: $OS"

# ── Install Docker ──
echo ""
echo "🐳 Installing Docker..."

if [ "$OS" = "amzn" ]; then
    # Amazon Linux 2023
    dnf update -y
    dnf install -y docker git
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ec2-user

elif [ "$OS" = "ubuntu" ]; then
    # Ubuntu 22.04
    apt-get update -y
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
else
    echo "❌ Unsupported OS: $OS"
    exit 1
fi

# ── Install Docker Compose (standalone) ──
echo ""
echo "📦 Installing Docker Compose..."
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep tag_name | cut -d '"' -f 4)
curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# ── Create application directory ──
echo ""
echo "📁 Creating application directory..."
mkdir -p /opt/sentineliq
chown $(whoami):$(whoami) /opt/sentineliq

# ── Setup firewall (allow HTTP on port 80) ──
echo ""
echo "🔥 Note: Ensure your EC2 Security Group allows:"
echo "   - Inbound: TCP 80 (HTTP) from 0.0.0.0/0"
echo "   - Inbound: TCP 22 (SSH) from your IP only"
echo "   - Outbound: All traffic"

# ── Summary ──
echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ Setup Complete!"
echo "═══════════════════════════════════════════"
echo ""
echo "  Next steps:"
echo "  1. Log out and back in (for docker group)"
echo "  2. Clone your repo:"
echo "     cd /opt/sentineliq"
echo "     git clone <your-repo-url> ."
echo "  3. Create .env file:"
echo "     cp .env.example .env"
echo "     nano .env  (fill in your keys)"
echo "  4. Start the app:"
echo "     docker-compose up -d --build"
echo "  5. Check status:"
echo "     docker-compose ps"
echo "     docker-compose logs -f"
echo ""
echo "  App will be available at: http://<your-ec2-public-ip>"
echo "═══════════════════════════════════════════"

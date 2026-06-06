#!/bin/bash
# ══════════════════════════════════════════════════════════
# SentinelIQ — Deploy / Update Script
# Run this from the project root (/opt/sentineliq) to deploy or update
# Usage: chmod +x deploy/deploy.sh && ./deploy/deploy.sh
# ══════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════"
echo "  SentinelIQ — Deploying..."
echo "═══════════════════════════════════════════"

# ── Pull latest code ──
echo "📥 Pulling latest code..."
git pull origin main

# ── Check .env exists ──
if [ ! -f .env ]; then
    echo "❌ .env file not found! Create it first:"
    echo "   cp .env.example .env && nano .env"
    exit 1
fi

# ── Build and restart containers ──
echo "🐳 Building and restarting containers..."
docker-compose down
docker-compose up -d --build

# ── Wait for health check ──
echo "⏳ Waiting for health check..."
sleep 10

if docker-compose ps | grep -q "healthy"; then
    echo ""
    echo "═══════════════════════════════════════════"
    echo "  ✅ Deployment Successful!"
    echo "═══════════════════════════════════════════"
    echo ""
    docker-compose ps
else
    echo ""
    echo "⚠️  Container may still be starting..."
    echo "   Check logs: docker-compose logs -f"
    docker-compose ps
fi

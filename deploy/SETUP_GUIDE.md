# SentinelIQ — AWS EC2 Deployment Guide

Complete step-by-step guide to deploy SentinelIQ from scratch on AWS EC2.

---

## Prerequisites

Before you begin, ensure you have:

- An AWS account
- A GitHub account with read access to the SentinelIQ repository
- A Google Gemini API key (for LLM scoring)
- A Gmail account with App Password enabled (for email alerts)
- An SSH client (Terminal on Mac/Linux, PuTTY or Windows Terminal on Windows)

---

## Step 1: Launch an EC2 Instance

### 1.1 Open AWS Console

Go to: https://console.aws.amazon.com/ec2/

### 1.2 Click "Launch Instance"

### 1.3 Configure the Instance

| Setting | Value |
|---------|-------|
| Name | `SentinelIQ` |
| AMI | Amazon Linux 2023 |
| Instance Type | `c7i-flex.large` (2 vCPU, 4 GB RAM) or `t3.medium` |
| Key Pair | Create new or select existing `.pem` key |
| Storage | 20 GB gp3 |

### 1.4 Configure Security Group

Create a new security group with these inbound rules:

| Type | Port | Source | Purpose |
|------|------|--------|---------|
| SSH | 22 | My IP | Remote access |
| HTTP | 80 | 0.0.0.0/0 | Web access |

Leave outbound as "All traffic".

### 1.5 Launch the Instance

Click **Launch Instance** and wait for it to show "Running" status.
Note down the **Public IPv4 address** (e.g., `52.66.123.45`).

---

## Step 2: Connect to EC2 via SSH

```bash
chmod 400 your-key.pem
ssh -i your-key.pem ec2-user@<your-public-ip>
```

Example:
```bash
ssh -i sentineliq-key.pem ec2-user@52.66.123.45
```

---

## Step 3: Install Docker & Docker Compose

Run the following commands one by one:

```bash
# Update system
sudo dnf update -y

# Install Docker and Git
sudo dnf install -y docker git

# Start Docker and enable on boot
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (avoids needing sudo for docker)
sudo usermod -aG docker ec2-user

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-Linux-x86_64" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

**Important:** Log out and back in for the docker group to take effect:

```bash
exit
ssh -i your-key.pem ec2-user@<your-public-ip>
```

Verify installation:

```bash
docker --version
docker-compose --version
```

---

## Step 4: Clone the Repository

```bash
# Create application directory
sudo mkdir -p /opt/sentineliq
sudo chown ec2-user:ec2-user /opt/sentineliq
cd /opt/sentineliq

# Clone the repo
git clone https://github.com/sdehran/SentinelIQ.git .
```

If the repository is private, use a Personal Access Token:

```bash
git clone https://<your-github-username>:<your-token>@github.com/sdehran/SentinelIQ.git .
```

---

## Step 5: Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in the values:

```env
# Google Gemini API Key (required for LLM fraud scoring)
GEMINI_API_KEY=AIzaSy-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Gmail SMTP (required for email alerts)
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop

# AWS Configuration (optional — only if using S3/SES)
AWS_ACCESS_KEY_ID=AKIA-EXAMPLE-KEY
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=ap-south-1
```

Save: `Ctrl+O` → `Enter` → `Ctrl+X`

### How to Get These Values

**Gemini API Key:**
1. Go to: https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key (starts with `AIzaSy`)

**Gmail App Password:**
1. Go to: https://myaccount.google.com/apppasswords
2. Select app: "Mail", device: "Other" → name it "SentinelIQ"
3. Copy the 16-character password
4. Note: You must have 2-Step Verification enabled on your Google account

**AWS Keys (optional):**
1. Go to: https://console.aws.amazon.com/iam/ → Users → Your User
2. Security credentials → Create access key
3. Copy Access Key ID and Secret Access Key

---

## Step 6: Build the Docker Image

```bash
cd /opt/sentineliq
docker build -t sentineliq-app .
```

This takes 3-5 minutes on first build (downloads Python packages).

---

## Step 7: Start the Application

```bash
docker-compose up -d
```

Verify it's running:

```bash
docker-compose ps
```

Expected output:
```
NAME              IMAGE            STATUS                    PORTS
sentineliq-app   sentineliq-app   Up 30 seconds (healthy)   0.0.0.0:80->8501/tcp
```

---

## Step 8: Access the Application

Open your browser and go to:

```
http://<your-ec2-public-ip>
```

Example: `http://52.66.123.45`

You should see the SentinelIQ Investigation Dashboard.

---

## Common Operations

### View Logs

```bash
docker-compose logs -f
```

(`Ctrl+C` to exit)

### Restart the App

```bash
docker-compose restart
```

### Stop the App

```bash
docker-compose down
```

### Update to Latest Code

```bash
cd /opt/sentineliq
git pull origin main
docker build -t sentineliq-app .
docker-compose down
docker-compose up -d
```

---

## Troubleshooting

### App not accessible in browser

- Check Security Group has port 80 open (inbound HTTP from 0.0.0.0/0)
- Verify container is running: `docker-compose ps`
- Check logs: `docker-compose logs`

### Container keeps restarting

- Check logs for errors: `docker-compose logs sentineliq-app`
- Verify `.env` file has correct values: `cat .env`
- Common issue: invalid GEMINI_API_KEY

### Out of memory

- Check memory: `free -h`
- Add swap if needed:
  ```bash
  sudo dd if=/dev/zero of=/swapfile bs=128M count=16
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  ```

### Docker permission denied

- Make sure you logged out and back in after `usermod -aG docker ec2-user`
- Or prefix commands with `sudo`

---

## Cost Estimate

| Resource | Monthly Cost (approx.) |
|----------|----------------------|
| c7i-flex.large (on-demand, 24/7) | ~$65 |
| 20 GB gp3 storage | ~$1.60 |
| Data transfer (minimal) | ~$1-2 |
| **Total** | **~$68/month** |

To save costs:
- Stop the instance when not in use (AWS Console → Instance → Stop)
- Consider using Spot Instances for ~60-70% savings
- Use a smaller instance (t3.micro) for demo purposes

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              EC2 Instance                    │
│  ┌───────────────────────────────────────┐  │
│  │         Docker Container              │  │
│  │  ┌─────────────────────────────────┐  │  │
│  │  │     Streamlit (Port 8501)       │  │  │
│  │  │  ┌───────────┐  ┌───────────┐  │  │  │
│  │  │  │ LangGraph │  │  FAISS    │  │  │  │
│  │  │  │ Workflow   │  │  RAG      │  │  │  │
│  │  │  └───────────┘  └───────────┘  │  │  │
│  │  │  ┌───────────┐  ┌───────────┐  │  │  │
│  │  │  │  Gemini   │  │  Pattern  │  │  │  │
│  │  │  │  LLM API  │  │  Memory   │  │  │  │
│  │  │  └───────────┘  └───────────┘  │  │  │
│  │  └─────────────────────────────────┘  │  │
│  └───────────────────────────────────────┘  │
│                Port 80 → 8501               │
└─────────────────────────────────────────────┘
```

---

## Security Notes

- Never commit `.env` to Git (it's in `.gitignore`)
- Restrict SSH access to your IP only in the Security Group
- Rotate your Gemini API key and Gmail App Password periodically
- Consider using AWS Secrets Manager for production credentials

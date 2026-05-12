# ShelfLife AI — Coolify Setup Guide (Step by Step)

> Follow this after running `infra/setup-server.sh` on your Hetzner server.
> Every step tells you exactly what to click and what to type.

---

## What You Need Before Starting

- [ ] Hetzner server IP address (e.g. `65.21.xx.xx`)
- [ ] Domain name (e.g. `yourdomain.com`) pointed to the server IP
- [ ] GitHub account with the shelflife-ai repo
- [ ] GitHub Personal Access Token (PAT) with `write:packages` scope

---

## Phase 1 — Coolify Initial Setup

### Step 1: Access Coolify
```
Open browser → http://YOUR_HETZNER_IP:8000
```

### Step 2: Create Admin Account
```
Email:    your@email.com
Password: use a strong password (save it!)
Click: Register
```

### Step 3: Add Your Domain
```
Top-right → Settings → Instance Settings
  Domain: https://coolify.yourdomain.com
  Click: Save
```

> Coolify now serves its UI at coolify.yourdomain.com (with SSL)

---

## Phase 2 — Connect GitHub

### Step 4: Add GitHub as Source
```
Left menu → Sources → Add a new Source
  Type: GitHub App
  Click: Register Now
  → GitHub opens → Install the Coolify GitHub App
  → Select your repository (shelflife-ai)
  → Click: Install & Authorize
  → Back in Coolify → Click: Save
```

---

## Phase 3 — Create Server & Project

### Step 5: Add Your Hetzner Server
```
Left menu → Servers → Add New Server
  Name:       hetzner-cx32
  IP Address: YOUR_HETZNER_IP
  Port:       22
  User:       root
  Type:       Remote Server
  Click: Save

→ Click: Validate Server
→ Wait for green "Connected" status
```

### Step 6: Create a Project
```
Left menu → Projects → Add New Project
  Name: shelflife-ai
  Description: ShelfLife AI Platform
  Click: Save
```

---

## Phase 4 — Shared Services (PostgreSQL + Redis + MLflow)

> These are shared across API and Dashboard. Set up once.

### Step 7: Add PostgreSQL
```
Project: shelflife-ai → Add New Resource → Database → PostgreSQL

  Name:             shelflife-postgres
  Server:           hetzner-cx32
  Version:          16
  DB Name:          shelflife
  DB User:          shelflife
  DB Password:      [generate a strong password — SAVE THIS]

  Click: Create & Start

→ Copy the "Internal Connection String" — you will need it
  Format: postgresql://shelflife:PASSWORD@postgres:5432/shelflife
```

### Step 8: Add Redis
```
Project: shelflife-ai → Add New Resource → Database → Redis

  Name:    shelflife-redis
  Server:  hetzner-cx32
  Version: 7

  Click: Create & Start

→ Copy Internal URL: redis://redis:6379/0
```

### Step 9: Add MLflow
```
Project: shelflife-ai → Add New Resource → Docker Compose (or Service)

  Name:   shelflife-mlflow
  Image:  ghcr.io/mlflow/mlflow:v3.10.1
  Port:   5000
  Domain: mlflow.yourdomain.com

  Command:
    mlflow server --host 0.0.0.0 --port 5000
    --backend-store-uri sqlite:///mlflow/mlflow.db
    --default-artifact-root /mlflow/artifacts

  Volume: mlflow_data:/mlflow

  Click: Save & Deploy
```

---

## Phase 5 — Deploy the API

### Step 10: Create API Application
```
Project: shelflife-ai → Add New Resource → Application

  Source:       GitHub (your source from Step 4)
  Repository:   shelflife-ai
  Branch:       main
  Dockerfile:   Dockerfile      ← important (not Dockerfile.dashboard)
  Port:         8000
  Domain:       api.yourdomain.com
  Name:         shelflife-api

  Click: Save
```

### Step 11: Add API Environment Variables
```
Application: shelflife-api → Environment Variables → Add all of these:

  DATABASE_URL         = postgresql://shelflife:YOUR_DB_PASSWORD@postgres:5432/shelflife
  REDIS_URL            = redis://redis:6379/0
  MLFLOW_TRACKING_URI  = http://mlflow:5000
  API_KEY              = your-strong-api-key-here
  API_WORKERS          = 2
  CORS_ORIGINS         = https://app.yourdomain.com
  LOG_LEVEL            = INFO
  RATE_LIMIT_PER_MINUTE = 100
  DEMAND_MODEL_NAME    = shelflife-demand-forecast
  WASTE_MODEL_NAME     = shelflife-waste-risk
  MODEL_STAGE          = Production

  Click: Save
```

### Step 12: Add Model Artifacts Volume
```
Application: shelflife-api → Storages → Add Volume
  Source:      model_artifacts   (named volume)
  Destination: /app/artifacts
  Click: Save
```

### Step 13: Deploy the API
```
Application: shelflife-api → Click: Deploy

→ Wait for green "Running" status
→ Test: https://api.yourdomain.com/health
   Expected: {"status": "healthy", ...}
```

---

## Phase 6 — Deploy the Dashboard

### Step 14: Create Dashboard Application
```
Project: shelflife-ai → Add New Resource → Application

  Source:       GitHub (same as Step 4)
  Repository:   shelflife-ai
  Branch:       main
  Dockerfile:   Dockerfile.dashboard    ← important
  Port:         8501
  Domain:       app.yourdomain.com
  Name:         shelflife-dashboard

  Click: Save
```

### Step 15: Add Dashboard Environment Variables
```
Application: shelflife-dashboard → Environment Variables:

  DATABASE_URL         = postgresql://shelflife:YOUR_DB_PASSWORD@postgres:5432/shelflife
  REDIS_URL            = redis://redis:6379/0
  MLFLOW_TRACKING_URI  = http://mlflow:5000

  Click: Save
```

### Step 16: Deploy Dashboard
```
Application: shelflife-dashboard → Click: Deploy

→ Wait for green "Running"
→ Test: https://app.yourdomain.com
```

---

## Phase 7 — First-Time Data Setup

> Run these ONCE after first deployment to seed the database and train models.

### Step 17: Seed the Database
```
In Coolify → Application: shelflife-api → Terminal (or use SSH)

  docker exec -it $(docker ps --filter name=shelflife-api -q) \
    uv run python -m db.seed
```

### Step 18: Train the Models
```
  docker exec -it $(docker ps --filter name=shelflife-api -q) \
    uv run python -m mlops.train_pipeline
```

> This takes ~5–10 minutes. After this, auto-retraining runs every Sunday at 2 AM.

---

## Phase 8 — Connect GitHub Actions for Auto-Deploy

### Step 19: Get Coolify Webhook URLs
```
Application: shelflife-api      → Settings → Webhooks → Copy URL
Application: shelflife-dashboard → Settings → Webhooks → Copy URL
```

### Step 20: Add Secrets to GitHub
```
GitHub → your repo → Settings → Secrets → Actions → New secret:

  Name:  COOLIFY_API_WEBHOOK
  Value: [paste API webhook URL from Coolify]

  Name:  COOLIFY_DASH_WEBHOOK
  Value: [paste Dashboard webhook URL from Coolify]

  Name:  GHCR_TOKEN
  Value: [your GitHub Personal Access Token with write:packages scope]
```

### Step 21: Test Auto-Deploy
```
Make a small change in your code → git push origin main

→ GitHub Actions runs: lint → test → build → push to GHCR → Coolify deploys
→ Check GitHub Actions tab for green checkmarks
→ Check Coolify dashboard for new deployment
```

---

## Phase 9 — Backups & Monitoring

### Step 22: Set Up Daily Database Backup
```
SSH into your server:
  ssh root@YOUR_HETZNER_IP

Set up cron job:
  crontab -e

Add this line (runs backup at 3 AM every day):
  0 3 * * * /root/shelflife-ai/scripts/backup_db.sh >> /var/log/shelflife-backup.log 2>&1
```

### Step 23: Set Up Free Uptime Monitoring (UptimeRobot)
```
1. Go to: https://uptimerobot.com (free account)
2. Add Monitor:
     Type:     HTTPS
     URL:      https://api.yourdomain.com/health
     Interval: Every 5 minutes
     Alert:    your@email.com
3. Add second monitor for: https://app.yourdomain.com
```

---

## Final Checklist

- [ ] Server created on Hetzner (CX32)
- [ ] Domain DNS → Hetzner IP
- [ ] Coolify installed and accessible
- [ ] GitHub source connected
- [ ] PostgreSQL running
- [ ] Redis running
- [ ] MLflow running at mlflow.yourdomain.com
- [ ] API running at api.yourdomain.com/health → healthy
- [ ] Dashboard running at app.yourdomain.com
- [ ] Database seeded (db.seed)
- [ ] Models trained (mlops.train_pipeline)
- [ ] GitHub Actions secrets added
- [ ] Auto-deploy tested (push to main → deploys)
- [ ] Daily backup cron active
- [ ] UptimeRobot monitoring active

---

## URLs After Setup

| Service | URL |
|---------|-----|
| API | https://api.yourdomain.com |
| API Docs | https://api.yourdomain.com/docs |
| Dashboard | https://app.yourdomain.com |
| MLflow | https://mlflow.yourdomain.com |
| Coolify Admin | https://coolify.yourdomain.com |

---

## Domain Setup — chotulab.com + www.chotulab.com

> Symptom: `www.chotulab.com` loads but `chotulab.com` shows "no available server."
> Root cause: either the bare-domain DNS A record is missing, or Coolify only has
> `www.chotulab.com` configured as a domain for the landing service.

### Step A — GoDaddy DNS (do this first)

Log in to GoDaddy → DNS → chotulab.com → Manage DNS

| Type  | Name | Value                 | TTL  |
|-------|------|-----------------------|------|
| A     | @    | YOUR_HETZNER_IP       | 600  |
| CNAME | www  | chotulab.com          | 1 hr |

> The `@` A record is what makes the bare domain resolve.
> After saving, DNS propagation takes 1–10 minutes (sometimes up to 1 hr).
> Verify with: `nslookup chotulab.com` — should return your Hetzner IP.

### Step B — Coolify: add both domains to the landing service

```
Coolify → Project: shelflife-ai → landing service → Settings → Domains

Add:
  chotulab.com
  www.chotulab.com

Click: Save → Redeploy (or Restart Proxy)
```

> Coolify/Traefik will request two separate SSL certificates (one per domain).
> Both will redirect to HTTPS automatically.

### Step C — How the redirect works (code side)

The file `chotulab-hub/nginx.conf` is mounted into the Nginx container.
It does two things:

1. Any request arriving with `Host: chotulab.com` → 301 permanent redirect to `www.chotulab.com`
2. `www.chotulab.com` (and any unknown host) → serves `index.html`

So the full request chain is:
```
User visits chotulab.com
  → Traefik (port 443, TLS) → routes to landing container
    → Nginx sees Host: chotulab.com → 301 → www.chotulab.com
      → Traefik routes to landing container again
        → Nginx serves index.html  ✓
```

### Step D — Quick verification after redeploy

```bash
# 1. DNS resolves for both
nslookup chotulab.com      # → Hetzner IP
nslookup www.chotulab.com  # → Hetzner IP

# 2. Root redirects to www
curl -I https://chotulab.com
# Expected: HTTP/2 301  location: https://www.chotulab.com/

# 3. www serves 200
curl -I https://www.chotulab.com
# Expected: HTTP/2 200
```

---

## Troubleshooting

**API returns 503 "Model not available"**
→ Models not trained yet. Run Step 18.

**Dashboard shows no data**
→ Database not seeded. Run Step 17.

**Deploy fails in GitHub Actions**
→ Check GHCR_TOKEN has `write:packages` scope.
→ Check COOLIFY_API_WEBHOOK is correct.

**Container keeps restarting**
→ Coolify → Application → Logs → check error message.
→ Usually an env var is missing or wrong.

**Out of disk space**
→ `df -h` on server.
→ `docker system prune -af` cleans unused images.
→ Check /var/backups/shelflife — reduce BACKUP_RETENTION_DAYS if needed.

**chotulab.com shows "no available server" but www works**
→ Step A: make sure GoDaddy has an A record for `@` pointing to Hetzner IP.
→ Step B: make sure Coolify has BOTH `chotulab.com` AND `www.chotulab.com` as domains on the landing service.
→ Step D: run the curl checks above to pinpoint where it breaks.

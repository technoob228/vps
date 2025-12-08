# VPS Provisioner v2.1.1

Automated VPS provisioning service for deploying self-hosted applications.

## 🚀 Features

### ✨ NEW: Universal Provisioner (v2.1.0)
- **Install ANY Docker application** - not limited to pre-configured apps
- **3 source types**: docker-compose URL, Docker image, or GitHub repository
- **Automatic resource checking** - checks RAM/disk/CPU BEFORE installation
- **Smart safety limits** - prevents apps from killing your server
- **Port conflict detection** - refuses installation if ports are taken
- **See [UNIVERSAL_PROVISIONER_GUIDE.md](UNIVERSAL_PROVISIONER_GUIDE.md) for details**

### Classic Features
- **One-click deployment** of popular open-source applications
- **7 pre-configured apps**: n8n, WireGuard, Outline, Vaultwarden, 3X-UI, FileBrowser, Seafile
- **Async job processing** with real-time status tracking
- **Persistent storage** with SQLite (easy to migrate to PostgreSQL/Redis later)
- **API authentication** with API keys
- **Idempotent installations** - safe to re-run if something fails
- **Production-ready** with Gunicorn support

## 📋 Supported Applications

| App | Description | RAM Usage | Perfect For |
|-----|-------------|-----------|-------------|
| **n8n** | Workflow automation (Zapier alternative) | ~300MB | Automation, integrations |
| **WireGuard** | Modern VPN with UI | ~50MB | Privacy, remote access |
| **Outline** | Wiki/docs (Notion alternative) | ~500MB | Documentation, knowledge base |
| **Vaultwarden** | Password manager (Bitwarden) | ~30MB | Password security |
| **3X-UI** | Advanced VPN panel (VMess, VLESS, Trojan) | ~100MB | Bypassing censorship |
| **FileBrowser** | Lightweight file manager | ~30MB | File sharing, storage |

## 🔧 Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
cp .env.example .env
# Edit .env and set your API_KEY
```

### 3. Run the service

**Development:**
```bash
python app.py
```

**Production (recommended):**
```bash
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

**Production with more workers:**
```bash
gunicorn -w 8 -b 0.0.0.0:5001 --timeout 1200 --access-logfile - app:app
```

### 4. Systemd service (optional but recommended)

Create `/etc/systemd/system/vps-provisioner.service`:

```ini
[Unit]
Description=VPS Provisioner Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/vps-provisioner
Environment="API_KEY=your-secret-key-here"
ExecStart=/usr/bin/gunicorn -w 4 -b 0.0.0.0:5001 --timeout 1200 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Then:
```bash
systemctl daemon-reload
systemctl enable vps-provisioner
systemctl start vps-provisioner
```

## 📡 API Usage

### Quick Start: Universal Provisioner

Install **any** Docker application:

```bash
# Example: Install Uptime Kuma monitoring
curl -X POST http://localhost:5001/provision/universal \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "ip_address": "95.179.200.45",
    "username": "root",
    "password": "server_password",
    "source_type": "docker-image",
    "source_url": "louislam/uptime-kuma:1",
    "app_name": "uptime-kuma",
    "ports": {"3001": "3001"}
  }'
```

**See [UNIVERSAL_PROVISIONER_GUIDE.md](UNIVERSAL_PROVISIONER_GUIDE.md) for complete documentation and examples.**

### Classic: Pre-configured Apps

```bash
curl -X POST http://localhost:5001/provision \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "ip_address": "95.179.200.45",
    "username": "root",
    "password": "server_password",
    "app": "n8n",
    "custom_domain": "n8n.example.com"
  }'
```

Response:
```json
{
  "job_id": "abc-123-def",
  "status": "started",
  "status_url": "/status/abc-123-def"
}
```

### 2. Check job status

```bash
curl http://localhost:5001/status/abc-123-def
```

Response (in progress):
```json
{
  "job_id": "abc-123-def",
  "status": "installing",
  "progress": 60,
  "message": "Installing n8n...",
  "ip": "95.179.200.45",
  "app": "n8n"
}
```

Response (completed):
```json
{
  "job_id": "abc-123-def",
  "status": "completed",
  "progress": 100,
  "message": "Installation completed successfully!",
  "result": {
    "status": "success",
    "app": "n8n",
    "url": "http://95.179.200.45:5678",
    "credentials": {
      "username": "admin",
      "password": "generated_password"
    },
    "notes": "n8n is ready! Login and start creating workflows."
  }
}
```

### 3. List all jobs

```bash
curl http://localhost:5001/jobs \
  -H "X-API-Key: your-api-key"
```

### 4. Get statistics

```bash
curl http://localhost:5001/stats \
  -H "X-API-Key: your-api-key"
```

### 5. Manual cleanup

```bash
curl -X POST http://localhost:5001/cleanup \
  -H "X-API-Key: your-api-key"
```

## 🔐 Security

### API Key Authentication

All write endpoints require `X-API-Key` header:

```bash
curl -H "X-API-Key: your-secret-key" ...
```

**IMPORTANT:** Change the default API key in production:

```bash
export API_KEY="your-super-secret-key-here"
```

### Firewall

The service should NOT be exposed to the public internet directly. Use:

1. **Nginx reverse proxy** with HTTPS
2. **VPN/Tailscale** for private access
3. **Firewall rules** to restrict access

Example nginx config:

```nginx
server {
    listen 80;
    server_name provisioner.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 1200s;
    }
}
```

## 📦 Project Structure

```
vps-provisioner/
├── app.py                      # Main Flask application
├── config.py                   # Configuration
├── storage.py                  # SQLite job storage
├── validation.py               # Input validation
├── auth.py                     # API key authentication
├── ssh_utils.py                # SSH utilities
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── provisioners/               # App provisioners
│   ├── __init__.py
│   ├── n8n.py
│   ├── wireguard.py
│   ├── outline.py
│   ├── vaultwarden.py
│   ├── x3ui.py
│   └── filebrowser.py
└── templates/                  # Installation scripts
    ├── n8n_install.sh
    ├── wireguard_install.sh
    ├── outline_install.sh
    ├── vaultwarden_install.sh
    ├── 3x-ui_install.sh
    └── filebrowser_install.sh
```

## 🎯 Example Workflow

### Provision n8n for a customer

```python
import requests

API_URL = "http://localhost:5001"
API_KEY = "your-api-key"

# 1. Start provisioning
response = requests.post(
    f"{API_URL}/provision",
    headers={"X-API-Key": API_KEY},
    json={
        "ip_address": "95.179.200.45",
        "username": "root",
        "password": "server_pass",
        "app": "n8n"
    }
)

job_id = response.json()["job_id"]
print(f"Job started: {job_id}")

# 2. Poll status until complete
import time

while True:
    status = requests.get(f"{API_URL}/status/{job_id}").json()
    print(f"Status: {status['status']} - {status.get('message', '')}")
    
    if status['status'] in ['completed', 'failed']:
        break
    
    time.sleep(10)

# 3. Get result
if status['status'] == 'completed':
    result = status['result']
    print(f"✅ Success!")
    print(f"URL: {result['url']}")
    print(f"Credentials: {result['credentials']}")
else:
    print(f"❌ Failed: {status.get('error')}")
```

## 🐛 Troubleshooting

### Installation logs

All installations save detailed logs in `/tmp/`:

```bash
ls -la /tmp/*_install_*.log
cat /tmp/n8n_install_95_179_200_45.log
```

### Job database

Jobs are stored in `jobs.db` (SQLite):

```bash
sqlite3 jobs.db "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10;"
```

### Check service status

```bash
systemctl status vps-provisioner
journalctl -u vps-provisioner -f
```

### Common issues

**SSH timeout:**
- Server might not be ready yet (wait 5-10 minutes after VPS creation)
- Wrong credentials
- Firewall blocking SSH

**Docker installation fails:**
- Server has old Linux kernel
- Not enough disk space

**Container won't start:**
- Port already in use
- Not enough RAM
- Check container logs: `docker logs <container_name>`

## 🔄 Upgrading

```bash
cd /opt/vps-provisioner
git pull
pip install -r requirements.txt --upgrade
systemctl restart vps-provisioner
```

## 📊 Server Requirements

### For running the provisioner:

- **RAM:** 512MB minimum
- **CPU:** 1 core
- **Disk:** 5GB
- **OS:** Ubuntu 20.04+

### For target VPS servers (what you provision):

| Tier | vCPU | RAM | Disk | Price | Apps |
|------|------|-----|------|-------|------|
| **LITE** | 2-3 | 4-8GB | 50-150GB | $5-10 | 2-4 apps |
| **PRO** | 4-6 | 8-16GB | 200-400GB | $15-25 | 5-10 apps |
| **BUSINESS** | 8+ | 16GB+ | 400GB+ | $30-50 | 10+ apps |

## 🎓 Adding New Apps

1. Create provisioner in `provisioners/your_app.py`
2. Create install script in `templates/your_app_install.sh`
3. Add to `PROVISIONERS` dict in `app.py`
4. Add to `SUPPORTED_APPS` in `config.py`

Example provisioner template:

```python
def setup_your_app(ip, username, password, custom_domain=None, job_id=None):
    ssh = create_ssh_client(ip, username, password)
    
    try:
        # Check if already installed
        if check_container_running(ssh, 'your_app'):
            return {...}
        
        # Upload and run install script
        # ...
        
        return {
            "status": "success",
            "app": "your_app",
            "url": url,
            "credentials": {...}
        }
    finally:
        ssh.close()
```

## 📝 License

MIT

## 🤝 Contributing

PRs welcome! Please test thoroughly before submitting.

## 💬 Support

- GitHub Issues for bugs
- Telegram: @your_support_channel (if you have one)

---

**Built for VPS reselling businesses.** Deploy apps in minutes, not hours. 🚀

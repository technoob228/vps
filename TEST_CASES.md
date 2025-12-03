# VPS Provisioner - Comprehensive Test Cases

## 📋 Test Environment Setup

### Prerequisites
```bash
# 1. Test server (VPS) requirements
- OS: Ubuntu 20.04+ or Debian 10+
- RAM: минимум 2GB
- Disk: минимум 10GB свободного
- SSH доступ (root или sudo user)
- Открыт порт 22 (SSH)

# 2. Provisioner server requirements
- Python 3.8+
- Установленные dependencies из requirements.txt
- API_KEY настроен в .env
```

### Setup Steps

#### Step 1: Подготовка Provisioner
```bash
# 1.1 Clone repository
cd /opt
git clone <repo-url> vps-provisioner
cd vps-provisioner

# 1.2 Install dependencies
pip install -r requirements.txt

# 1.3 Configure environment
cp .env.example .env
nano .env  # Set API_KEY=your-test-key-123

# 1.4 Start service
python app.py

# Expected output:
# ============================================================
# 🚀 VPS Provisioner v2.1 - Universal Edition
# ============================================================
# 🌐 Server starting on http://0.0.0.0:5001
```

#### Step 2: Подготовка Test VPS
```bash
# 2.1 Получить credentials
IP_ADDRESS=95.179.200.45  # Ваш VPS IP
USERNAME=root
PASSWORD=your_vps_password

# 2.2 Проверить SSH доступ
ssh root@95.179.200.45
# Должен подключиться без ошибок

# 2.3 (Optional) Очистить VPS от старых контейнеров
docker ps -a
docker rm -f $(docker ps -aq)  # Удалить все контейнеры
docker system prune -a --volumes -f  # Очистить всё
```

#### Step 3: Setup Test Environment Variables
```bash
export PROVISIONER_URL="http://localhost:5001"
export API_KEY="your-test-key-123"
export TEST_VPS_IP="95.179.200.45"
export TEST_VPS_USER="root"
export TEST_VPS_PASS="your_vps_password"
```

---

## 🧪 TEST SUITE 1: Core Functionality

### TEST 1.1: Health Check
**Purpose:** Verify service is running

**Steps:**
```bash
curl http://localhost:5001/health
```

**Expected Result:**
```json
{
  "status": "healthy",
  "version": "2.0",
  "supported_apps": ["n8n", "wireguard", "outline", "vaultwarden", "3x-ui", "seafile", "filebrowser"]
}
```

**Pass Criteria:**
- ✅ Status code: 200
- ✅ Response contains "healthy"
- ✅ Version present
- ✅ Supported apps list present

---

### TEST 1.2: API Authentication
**Purpose:** Verify API key validation

**Test 1.2.1: Valid API Key**
```bash
curl -X POST http://localhost:5001/provision \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**Expected Result:**
- Status code: 400 (validation error, but NOT 401/403)
- Response contains validation errors (not auth errors)

**Test 1.2.2: Invalid API Key**
```bash
curl -X POST http://localhost:5001/provision \
  -H "X-API-Key: wrong-key" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Result:**
```json
{
  "error": "Invalid API key",
  "message": "The provided API key is incorrect"
}
```
- Status code: 403

**Test 1.2.3: Missing API Key**
```bash
curl -X POST http://localhost:5001/provision \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Result:**
```json
{
  "error": "Missing API key",
  "message": "Include X-API-Key header in your request"
}
```
- Status code: 401

**Pass Criteria:**
- ✅ Valid key works
- ✅ Invalid key rejected with 403
- ✅ Missing key rejected with 401

---

## 🧪 TEST SUITE 2: Pre-configured Apps (Classic Provisioner)

### TEST 2.1: Install n8n
**Purpose:** Test pre-configured app installation

**Steps:**
```bash
# 1. Create job
curl -X POST http://localhost:5001/provision \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "app": "n8n"
  }' | jq .

# Save job_id from response
JOB_ID=<job_id_from_response>
```

**Expected Response:**
```json
{
  "job_id": "abc-123-def",
  "status": "started",
  "status_url": "/status/abc-123-def"
}
```

**Steps 2-5: Monitor Installation**
```bash
# 2. Check status (repeat every 30 seconds)
while true; do
  curl http://localhost:5001/status/$JOB_ID | jq .
  sleep 30
done

# Expected progression:
# - status: "waiting_ssh" (0-2 minutes)
# - status: "installing" (2-8 minutes)
# - status: "completed" (final)
```

**Expected Final Result:**
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
      "password": "<generated_password>"
    },
    "notes": "n8n is ready! Login and start creating workflows."
  }
}
```

**Verification Steps:**
```bash
# 3. Verify on VPS
ssh root@$TEST_VPS_IP

# Check container running
docker ps | grep n8n
# Expected: Container "n8n" with status "Up X minutes"

# Check container health
docker logs n8n --tail 50
# Expected: No errors, server started

# Check port listening
ss -tulpn | grep 5678
# Expected: Port 5678 LISTEN

# Exit SSH
exit

# 4. Verify HTTP access
curl -I http://$TEST_VPS_IP:5678
# Expected: HTTP 200 or 301/302 redirect

# 5. (Optional) Test login via browser
# Open http://95.179.200.45:5678
# Login with credentials from result
# Expected: Can login and see n8n dashboard
```

**Pass Criteria:**
- ✅ Job created with valid job_id
- ✅ Status progresses: started → waiting_ssh → installing → completed
- ✅ Final status is "completed"
- ✅ Container running on VPS
- ✅ Port 5678 accessible
- ✅ Can login with provided credentials

**Cleanup:**
```bash
ssh root@$TEST_VPS_IP "docker rm -f n8n && rm -rf /opt/n8n"
```

---

### TEST 2.2: Install WireGuard
**Purpose:** Test VPN installation

**Steps:** (Similar to TEST 2.1, but with app: "wireguard")
```bash
curl -X POST http://localhost:5001/provision \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "app": "wireguard"
  }' | jq .
```

**Expected Result:**
- Container "wireguard" running
- Port 51820/udp listening
- Web UI on port 51821

**Pass Criteria:**
- ✅ Installation completes successfully
- ✅ WireGuard UI accessible
- ✅ Can generate client config

---

## 🧪 TEST SUITE 3: Universal Provisioner - Docker Image

### TEST 3.1: Install from Docker Hub (Uptime Kuma)
**Purpose:** Test docker-image source type

**Steps:**
```bash
# 1. Create job
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "source_type": "docker-image",
    "source_url": "louislam/uptime-kuma:1",
    "app_name": "uptime-kuma",
    "ports": {"3001": "3001"}
  }' | jq .

JOB_ID=<save_job_id>
```

**Expected Response:**
```json
{
  "job_id": "def-456-ghi",
  "status": "started",
  "status_url": "/status/def-456-ghi"
}
```

**Monitor Progress:**
```bash
# Check status
curl http://localhost:5001/status/$JOB_ID | jq .

# Expected progression:
# - status: "waiting_ssh" (progress: 5%)
# - status: "analyzing" (progress: 20%)
# - status: "checking_server" (progress: 40%)
# - status: "installing" (progress: 60-80%)
# - status: "completed" (progress: 100%)
```

**Expected Final Result:**
```json
{
  "job_id": "def-456-ghi",
  "status": "completed",
  "progress": 100,
  "result": {
    "status": "success",
    "app": "uptime-kuma",
    "source_type": "docker-image",
    "source_url": "louislam/uptime-kuma:1",
    "ports": [3001],
    "resources_allocated": {
      "memory_limit_mb": 2048,
      "cpu_limit": 2.0
    },
    "server_status": {
      "memory_used_mb": 1234,
      "memory_available_mb": 2800
    }
  }
}
```

**Verification:**
```bash
# 1. Check container running
ssh root@$TEST_VPS_IP "docker ps | grep uptime-kuma"

# 2. Check resource limits applied
ssh root@$TEST_VPS_IP "docker inspect uptime-kuma | grep -A5 Memory"
# Expected: "Memory": 2147483648 (2GB in bytes)

# 3. Check port
curl -I http://$TEST_VPS_IP:3001
# Expected: HTTP 200

# 4. Check restart policy
ssh root@$TEST_VPS_IP "docker inspect uptime-kuma | grep -A2 RestartPolicy"
# Expected: "MaximumRetryCount": 3
```

**Pass Criteria:**
- ✅ Installation completes
- ✅ Container has memory limit (2048MB)
- ✅ Container has CPU limit (2.0)
- ✅ Restart policy is "on-failure:3"
- ✅ Port 3001 accessible
- ✅ Server status shows remaining resources

**Cleanup:**
```bash
ssh root@$TEST_VPS_IP "docker rm -f uptime-kuma"
```

---

### TEST 3.2: Resource Check - Insufficient RAM
**Purpose:** Test that system refuses installation if not enough RAM

**Steps:**
```bash
# Try to install something that needs 8GB on a 4GB server
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "source_type": "docker-image",
    "source_url": "postgres:15",
    "app_name": "postgres-huge",
    "max_memory_mb": 8192
  }' | jq .

JOB_ID=<save_job_id>

# Check status
curl http://localhost:5001/status/$JOB_ID | jq .
```

**Expected Result:**
```json
{
  "job_id": "xyz-789",
  "status": "rejected",
  "progress": 0,
  "error": "Insufficient resources:\n  ❌ Need 8192MB, only 3200MB available\n  ✅ Disk OK",
  "error_type": "insufficient_resources"
}
```

**Pass Criteria:**
- ✅ Status is "rejected" (NOT "failed")
- ✅ Error message clearly states insufficient RAM
- ✅ No container created on VPS
- ✅ Server untouched (verify no postgres container)

**Verification:**
```bash
ssh root@$TEST_VPS_IP "docker ps -a | grep postgres-huge"
# Expected: No output (container not created)
```

---

### TEST 3.3: Port Conflict Detection
**Purpose:** Test that system detects port conflicts

**Steps:**
```bash
# 1. First, install something on port 8080
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "source_type": "docker-image",
    "source_url": "nginx:alpine",
    "app_name": "nginx-first",
    "ports": {"8080": "80"}
  }' | jq .

# Wait for completion
sleep 60

# 2. Try to install another app on same port
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "source_type": "docker-image",
    "source_url": "httpd:alpine",
    "app_name": "httpd-second",
    "ports": {"8080": "80"}
  }' | jq .

JOB_ID=<save_job_id>
curl http://localhost:5001/status/$JOB_ID | jq .
```

**Expected Result:**
```json
{
  "job_id": "port-conflict-123",
  "status": "rejected",
  "error": "Ports already in use: [8080]",
  "error_type": "port_conflict"
}
```

**Pass Criteria:**
- ✅ First installation succeeds
- ✅ Second installation rejected
- ✅ Error mentions port 8080
- ✅ Only first container exists

**Cleanup:**
```bash
ssh root@$TEST_VPS_IP "docker rm -f nginx-first httpd-second"
```

---

## 🧪 TEST SUITE 4: Universal Provisioner - Docker Compose

### TEST 4.1: Install from docker-compose.yml URL
**Purpose:** Test docker-compose source type

**Setup:** Create test docker-compose.yml
```bash
# Create a simple test compose file
cat > /tmp/test-compose.yml << 'EOF'
version: '3.8'
services:
  web:
    image: nginx:alpine
    ports:
      - "8888:80"
  redis:
    image: redis:alpine
EOF

# Upload to GitHub Gist or serve via HTTP
# For testing, use raw.githubusercontent.com URL
COMPOSE_URL="https://gist.githubusercontent.com/user/xxx/raw/test-compose.yml"
```

**Steps:**
```bash
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "source_type": "docker-compose",
    "source_url": "'"$COMPOSE_URL"'",
    "app_name": "test-stack"
  }' | jq .

JOB_ID=<save_job_id>

# Monitor
curl http://localhost:5001/status/$JOB_ID | jq .
```

**Expected Result:**
```json
{
  "status": "completed",
  "result": {
    "app": "test-stack",
    "source_type": "docker-compose",
    "services": ["web", "redis"],
    "ports": [8888],
    "location": "/opt/test-stack"
  }
}
```

**Verification:**
```bash
# Check both containers running
ssh root@$TEST_VPS_IP "docker ps | grep test-stack"
# Expected: 2 containers (web, redis)

# Check compose file uploaded
ssh root@$TEST_VPS_IP "cat /opt/test-stack/docker-compose.yml"
# Expected: File exists with safety limits added

# Check memory limits were added
ssh root@$TEST_VPS_IP "docker inspect test-stack_web_1 | grep Memory"
# Expected: Memory limit present

# Check restart policy
ssh root@$TEST_VPS_IP "docker inspect test-stack_web_1 | grep -A2 RestartPolicy"
# Expected: "on-failure:3"
```

**Pass Criteria:**
- ✅ Both services started
- ✅ Safety limits added automatically
- ✅ Port 8888 accessible
- ✅ Files in /opt/test-stack/

**Cleanup:**
```bash
ssh root@$TEST_VPS_IP "cd /opt/test-stack && docker-compose down && cd ~ && rm -rf /opt/test-stack"
```

---

### TEST 4.2: Compose with Security Warnings
**Purpose:** Test security check for dangerous configurations

**Setup:** Create compose with privileged mode
```yaml
# test-dangerous-compose.yml
version: '3.8'
services:
  dangerous:
    image: alpine
    privileged: true
    network_mode: host
```

**Steps:**
```bash
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "source_type": "docker-compose",
    "source_url": "<dangerous_compose_url>",
    "app_name": "dangerous-app"
  }' | jq .
```

**Expected Behavior:**
- Installation should proceed BUT with warnings logged
- OR be rejected if security policy is strict

**Pass Criteria:**
- ✅ Security issues detected
- ✅ Warnings logged or installation rejected
- ✅ User informed of risks

---

## 🧪 TEST SUITE 5: Universal Provisioner - GitHub Repo

### TEST 5.1: Install from GitHub Repository
**Purpose:** Test github-repo source type

**Prerequisites:**
- Create test GitHub repo with Dockerfile
- Example: simple Node.js or Python app

**Steps:**
```bash
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "source_type": "github-repo",
    "source_url": "https://github.com/username/test-app",
    "app_name": "my-github-app",
    "dockerfile_path": "Dockerfile",
    "ports": {"3000": "3000"},
    "env_vars": {
      "NODE_ENV": "production",
      "PORT": "3000"
    }
  }' | jq .

JOB_ID=<save_job_id>
```

**Expected Result:**
```json
{
  "status": "completed",
  "result": {
    "app": "my-github-app",
    "source_type": "github-repo",
    "built_from": "Dockerfile",
    "location": "/opt/my-github-app",
    "ports": [3000]
  }
}
```

**Verification:**
```bash
# 1. Check repo cloned
ssh root@$TEST_VPS_IP "ls /opt/my-github-app"
# Expected: Source files present

# 2. Check image built
ssh root@$TEST_VPS_IP "docker images | grep my-github-app"
# Expected: Image "my-github-app:latest"

# 3. Check container running
ssh root@$TEST_VPS_IP "docker ps | grep my-github-app"

# 4. Check env vars
ssh root@$TEST_VPS_IP "docker inspect my-github-app | grep -A10 Env"
# Expected: NODE_ENV=production, PORT=3000

# 5. Test app
curl http://$TEST_VPS_IP:3000
# Expected: App responds
```

**Pass Criteria:**
- ✅ Repo cloned successfully
- ✅ Docker image built
- ✅ Container running
- ✅ Environment variables set
- ✅ Application accessible

**Cleanup:**
```bash
ssh root@$TEST_VPS_IP "docker rm -f my-github-app && docker rmi my-github-app:latest && rm -rf /opt/my-github-app"
```

---

## 🧪 TEST SUITE 6: Validation & Error Handling

### TEST 6.1: Missing Required Fields
**Purpose:** Test input validation

**Test 6.1.1: Missing ip_address**
```bash
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "root",
    "password": "pass",
    "source_type": "docker-image",
    "source_url": "nginx",
    "app_name": "test"
  }' | jq .
```

**Expected Result:**
```json
{
  "errors": ["Missing required field: ip_address"]
}
```
- Status code: 400

**Test 6.1.2: Invalid source_type**
```bash
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "1.2.3.4",
    "username": "root",
    "password": "pass",
    "source_type": "invalid-type",
    "source_url": "test",
    "app_name": "test"
  }' | jq .
```

**Expected Result:**
```json
{
  "errors": ["Invalid source_type. Must be one of: docker-compose, docker-image, github-repo"]
}
```

**Test 6.1.3: Invalid app_name**
```bash
# Test with uppercase (not allowed)
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "1.2.3.4",
    "username": "root",
    "password": "password",
    "source_type": "docker-image",
    "source_url": "nginx",
    "app_name": "MyApp"
  }' | jq .
```

**Expected Result:**
```json
{
  "errors": ["app_name must start with letter/number and contain only lowercase letters, numbers, hyphens, underscores"]
}
```

**Pass Criteria:**
- ✅ All validation errors caught
- ✅ Clear error messages
- ✅ Status code 400 for validation errors

---

### TEST 6.2: SSH Connection Failures
**Purpose:** Test handling of SSH timeouts

**Steps:**
```bash
# Use non-existent IP or wrong credentials
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.0.2.1",
    "username": "root",
    "password": "wrong",
    "source_type": "docker-image",
    "source_url": "nginx",
    "app_name": "test-fail"
  }' | jq .

JOB_ID=<save_job_id>

# Wait and check (should fail within ~5 minutes)
curl http://localhost:5001/status/$JOB_ID | jq .
```

**Expected Result:**
```json
{
  "status": "failed",
  "error": "SSH timeout after 15 attempts. Server not ready."
}
```

**Pass Criteria:**
- ✅ Job fails gracefully
- ✅ Error message is clear
- ✅ No partial installation
- ✅ Retry attempts visible in logs

---

### TEST 6.3: Download Failure
**Purpose:** Test handling of invalid URLs

**Steps:**
```bash
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "source_type": "docker-compose",
    "source_url": "https://example.com/non-existent.yml",
    "app_name": "test-404"
  }' | jq .

JOB_ID=<save_job_id>
curl http://localhost:5001/status/$JOB_ID | jq .
```

**Expected Result:**
```json
{
  "status": "failed",
  "error": "Failed to download compose file: 404 Not Found",
  "error_type": "source_download"
}
```

**Pass Criteria:**
- ✅ Clear error message
- ✅ No partial installation
- ✅ Server untouched

---

## 🧪 TEST SUITE 7: Concurrent Operations

### TEST 7.1: Multiple Simultaneous Installations
**Purpose:** Test thread safety and concurrent provisioning

**Steps:**
```bash
# Start 3 installations simultaneously
for i in {1..3}; do
  curl -X POST http://localhost:5001/provision/universal \
    -H "X-API-Key: your-test-key-123" \
    -H "Content-Type: application/json" \
    -d '{
      "ip_address": "'$TEST_VPS_IP'",
      "username": "'$TEST_VPS_USER'",
      "password": "'$TEST_VPS_PASS'",
      "source_type": "docker-image",
      "source_url": "redis:alpine",
      "app_name": "redis-'$i'",
      "ports": {"'$((6379+$i))'": "6379"}
    }' | jq . &
done

wait

# Monitor all jobs
curl http://localhost:5001/jobs -H "X-API-Key: your-test-key-123" | jq .
```

**Expected Result:**
- All 3 installations should proceed independently
- All should complete successfully
- No race conditions or conflicts

**Pass Criteria:**
- ✅ All 3 jobs complete
- ✅ All 3 containers running
- ✅ Different ports assigned (6380, 6381, 6382)
- ✅ No database corruption

**Cleanup:**
```bash
ssh root@$TEST_VPS_IP "docker rm -f redis-1 redis-2 redis-3"
```

---

## 🧪 TEST SUITE 8: Statistics & Management

### TEST 8.1: Job Listing
**Purpose:** Test /jobs endpoint

**Steps:**
```bash
# Run a few jobs first (from previous tests)
# Then list them

curl http://localhost:5001/jobs \
  -H "X-API-Key: your-test-key-123" | jq .
```

**Expected Result:**
```json
{
  "total": 15,
  "jobs": [
    {
      "job_id": "...",
      "status": "completed",
      "app": "uptime-kuma",
      "created_at": "..."
    },
    ...
  ]
}
```

**Pass Criteria:**
- ✅ Returns list of jobs
- ✅ Sorted by created_at (newest first)
- ✅ Contains all expected fields

---

### TEST 8.2: Statistics
**Purpose:** Test /stats endpoint

**Steps:**
```bash
curl http://localhost:5001/stats \
  -H "X-API-Key: your-test-key-123" | jq .
```

**Expected Result:**
```json
{
  "total": 15,
  "by_status": {
    "completed": 12,
    "failed": 2,
    "rejected": 1
  },
  "by_app": {
    "uptime-kuma": 3,
    "n8n": 2,
    "test-stack": 1
  }
}
```

**Pass Criteria:**
- ✅ Total matches job count
- ✅ Status breakdown correct
- ✅ App breakdown correct

---

## 🧪 TEST SUITE 9: Edge Cases

### TEST 9.1: Very Long Job (Timeout Test)
**Purpose:** Test timeout handling for very large images

**Steps:**
```bash
# Try to install very large image (e.g., Gitlab)
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "'$TEST_VPS_USER'",
    "password": "'$TEST_VPS_PASS'",
    "source_type": "docker-image",
    "source_url": "gitlab/gitlab-ce:latest",
    "app_name": "gitlab",
    "max_memory_mb": 4096
  }' | jq .
```

**Expected Behavior:**
- Should either complete (if enough resources) OR
- Fail with timeout/resource error
- Should NOT hang forever

**Pass Criteria:**
- ✅ Job doesn't hang indefinitely
- ✅ Status updates periodically
- ✅ Either completes or fails with clear error

---

### TEST 9.2: Special Characters in Passwords
**Purpose:** Test password with special characters

**Steps:**
```bash
# Password with special chars: p@$$w0rd!#%
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-test-key-123" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "'$TEST_VPS_IP'",
    "username": "root",
    "password": "p@$$w0rd!#%",
    "source_type": "docker-image",
    "source_url": "nginx",
    "app_name": "test-special-pass"
  }' | jq .
```

**Expected Result:**
- Should handle password correctly
- SSH authentication succeeds

**Pass Criteria:**
- ✅ No escaping issues
- ✅ SSH connects successfully
- ✅ Installation completes

---

## 📋 Test Execution Checklist

### Pre-Test
- [ ] Provisioner service running
- [ ] Test VPS accessible via SSH
- [ ] API_KEY configured
- [ ] Test VPS has enough resources (2GB+ RAM, 10GB+ disk)
- [ ] Docker installed on test VPS (or will be installed)

### Core Tests (Required)
- [ ] TEST 1.1: Health Check
- [ ] TEST 1.2: API Authentication
- [ ] TEST 2.1: Install n8n (pre-configured)
- [ ] TEST 3.1: Install from Docker Hub
- [ ] TEST 3.2: Resource Check - Insufficient RAM
- [ ] TEST 3.3: Port Conflict Detection
- [ ] TEST 4.1: Install from docker-compose
- [ ] TEST 5.1: Install from GitHub
- [ ] TEST 6.1: Validation errors

### Extended Tests (Recommended)
- [ ] TEST 2.2: Install WireGuard
- [ ] TEST 4.2: Security warnings
- [ ] TEST 6.2: SSH failures
- [ ] TEST 6.3: Download failures
- [ ] TEST 7.1: Concurrent operations
- [ ] TEST 8.1: Job listing
- [ ] TEST 8.2: Statistics

### Edge Cases (Optional)
- [ ] TEST 9.1: Timeout handling
- [ ] TEST 9.2: Special characters

---

## 🎯 Success Criteria Summary

### Critical (Must Pass):
1. ✅ Health check responds
2. ✅ API authentication works
3. ✅ At least one pre-configured app installs
4. ✅ Universal provisioner installs from docker-image
5. ✅ Resource checks prevent over-allocation
6. ✅ Port conflicts detected
7. ✅ Validation catches bad inputs

### Important (Should Pass):
1. ✅ Docker-compose installs work
2. ✅ GitHub repo installs work
3. ✅ Safety limits applied correctly
4. ✅ SSH failures handled gracefully
5. ✅ Multiple concurrent jobs work

### Nice to Have:
1. ✅ Security warnings shown
2. ✅ Statistics accurate
3. ✅ Edge cases handled

---

## 🐛 Reporting Issues

When reporting bugs, include:

```markdown
**Test Case:** TEST X.Y - Name
**Environment:**
  - Provisioner version: 2.1
  - Test VPS OS: Ubuntu 22.04
  - RAM: 4GB
  - Python: 3.10

**Steps to Reproduce:**
1. ...
2. ...

**Expected Result:**
...

**Actual Result:**
...

**Logs:**
```
<paste relevant logs>
```

**Job ID:** abc-123-def
**Error Type:** insufficient_resources / port_conflict / etc
```

---

## 📝 Test Automation Script

```bash
#!/bin/bash
# test_runner.sh - Automated test runner

set -e

# Config
export PROVISIONER_URL="http://localhost:5001"
export API_KEY="your-test-key-123"
export TEST_VPS_IP="95.179.200.45"
export TEST_VPS_USER="root"
export TEST_VPS_PASS="password"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

passed=0
failed=0

# Helper functions
test_case() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Running: $1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

assert_success() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $1"
        ((passed++))
    else
        echo -e "${RED}❌ FAIL${NC}: $1"
        ((failed++))
    fi
}

# Run tests
test_case "TEST 1.1: Health Check"
response=$(curl -s http://localhost:5001/health)
echo "$response" | jq -e '.status == "healthy"' > /dev/null
assert_success "Health check"

test_case "TEST 1.2: API Auth - Invalid Key"
status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:5001/provision \
    -H "X-API-Key: wrong-key")
[ "$status" = "403" ]
assert_success "Invalid API key rejected"

# ... more tests ...

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}Passed: $passed${NC}"
echo -e "${RED}Failed: $failed${NC}"
echo "Total: $((passed + failed))"

if [ $failed -eq 0 ]; then
    echo -e "\n${GREEN}🎉 ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "\n${RED}❌ SOME TESTS FAILED${NC}"
    exit 1
fi
```

---

**Ready to test!** Начинай с TEST 1.1 и двигайся по порядку. Удачи! 🚀

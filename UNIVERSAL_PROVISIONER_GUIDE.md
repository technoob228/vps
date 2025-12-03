# Universal Provisioner Guide

## 🎯 Что это?

Универсальный провижинер позволяет устанавливать **ЛЮБЫЕ** Docker-приложения на твой VPS, не требуя хардкода для каждого приложения. Просто дай ссылку на docker-compose.yml, Docker image, или GitHub репозиторий — система сама установит.

## ✨ Ключевые возможности

- ✅ **Автоматическая проверка ресурсов** - узнаешь ЗАРАНЕЕ, хватит ли RAM/disk/CPU
- ✅ **Защита от убийства сервера** - автоматические resource limits на все контейнеры
- ✅ **Проверка портов** - отказ если порт уже занят (вместо конфликта)
- ✅ **3 типа источников** - docker-compose, docker-image, github-repo
- ✅ **Понятные ошибки** - "нужно 4GB RAM, доступно 2GB" вместо "container killed"

## 🚀 Быстрый старт

### Пример 1: Установить Uptime Kuma (мониторинг)

```bash
curl -X POST http://your-server:5001/provision/universal \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "95.179.200.45",
    "username": "root",
    "password": "server_pass",
    "source_type": "docker-image",
    "source_url": "louislam/uptime-kuma:1",
    "app_name": "uptime-kuma",
    "ports": {"3001": "3001"}
  }'
```

**Ответ:**
```json
{
  "job_id": "abc-123",
  "status": "started",
  "status_url": "/status/abc-123"
}
```

**Проверить статус:**
```bash
curl http://your-server:5001/status/abc-123
```

**Результат (когда готов):**
```json
{
  "job_id": "abc-123",
  "status": "completed",
  "progress": 100,
  "result": {
    "app": "uptime-kuma",
    "source_type": "docker-image",
    "ports": [3001],
    "resources_allocated": {
      "memory_limit_mb": 2048,
      "cpu_limit": 2.0
    },
    "server_status": {
      "memory_used_mb": 2100,
      "memory_available_mb": 1924
    }
  }
}
```

## 📚 Типы источников

### 1. Docker Image (самый простой)

Используй любой публичный Docker image из Docker Hub или другого registry.

```bash
curl -X POST http://your-server:5001/provision/universal \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "95.179.200.45",
    "username": "root",
    "password": "server_pass",
    "source_type": "docker-image",
    "source_url": "netdata/netdata:latest",
    "app_name": "netdata",
    "ports": {"19999": "19999"}
  }'
```

**Популярные примеры:**
```bash
# Мониторинг
louislam/uptime-kuma:1
netdata/netdata:latest
grafana/grafana:latest

# Базы данных
postgres:15-alpine
mongo:7
redis:7-alpine

# Аналитика
matomo:latest
plausible/analytics:latest

# File sharing
filebrowser/filebrowser:latest
owncloud/server:latest

# Любой другой Docker image!
```

### 2. Docker Compose (для сложных приложений)

Используй готовые docker-compose.yml файлы из GitHub.

```bash
curl -X POST http://your-server:5001/provision/universal \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "95.179.200.45",
    "username": "root",
    "password": "server_pass",
    "source_type": "docker-compose",
    "source_url": "https://raw.githubusercontent.com/plausible/hosting/master/docker-compose.yml",
    "app_name": "plausible"
  }'
```

**Что происходит:**
1. Скачивает docker-compose.yml
2. Парсит требования (RAM, disk, ports)
3. Проверяет доступные ресурсы сервера
4. Добавляет safety limits на ВСЕ контейнеры
5. Запускает `docker-compose up -d`

**Популярные docker-compose примеры:**
```
# Plausible Analytics
https://raw.githubusercontent.com/plausible/hosting/master/docker-compose.yml

# Outline Wiki
https://raw.githubusercontent.com/outline/outline/main/docker-compose.yml

# Mattermost
https://raw.githubusercontent.com/mattermost/docker/master/docker-compose.yml

# Nextcloud
https://raw.githubusercontent.com/nextcloud/docker/master/.examples/docker-compose/with-nginx-proxy/mariadb/apache/docker-compose.yml
```

### 3. GitHub Repository (кастомные проекты)

Клонирует репо, билдит Docker image, запускает.

```bash
curl -X POST http://your-server:5001/provision/universal \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "95.179.200.45",
    "username": "root",
    "password": "server_pass",
    "source_type": "github-repo",
    "source_url": "https://github.com/awesome-selfhosted/some-app",
    "app_name": "my-app",
    "dockerfile_path": "docker/Dockerfile",
    "ports": {"8080": "80"},
    "env_vars": {
      "DATABASE_URL": "postgres://...",
      "SECRET_KEY": "xyz123"
    }
  }'
```

**Параметры:**
- `dockerfile_path` - путь к Dockerfile (опционально, по умолчанию `Dockerfile` в корне)
- `env_vars` - переменные окружения для контейнера

## 🛡️ Защита от проблем

### Проблема 1: Недостаточно RAM

**Запрос:**
```bash
# Пытаемся установить Gitlab (нужно 4GB), но на сервере только 2GB свободно
```

**Ответ:**
```json
{
  "job_id": "xyz-789",
  "status": "rejected",
  "error": "Insufficient resources:\n  ❌ Need 4096MB, only 1680MB available\n  ✅ Disk OK",
  "error_type": "insufficient_resources"
}
```

**→ Сервер НЕ тронут, ничего не установлено!**

### Проблема 2: Порт занят

**Запрос:**
```bash
# Пытаемся установить что-то на порт 80, но там уже nginx
```

**Ответ:**
```json
{
  "status": "rejected",
  "error": "Ports already in use: [80]",
  "error_type": "port_conflict"
}
```

**→ Опять сервер не сломан!**

### Проблема 3: Скачивание не удалось

**Ответ:**
```json
{
  "status": "failed",
  "error": "Failed to download compose file: 404 Not Found",
  "error_type": "source_download"
}
```

## ⚙️ Дополнительные параметры

### Ограничение ресурсов

```json
{
  "source_type": "docker-image",
  "source_url": "postgres:15",
  "app_name": "postgres",
  "max_memory_mb": 1024,  // Максимум 1GB RAM
  "max_cpu": 1.0,         // Максимум 1 CPU core
  "ports": {"5432": "5432"}
}
```

**Defaults:**
- `max_memory_mb`: 2048 (2GB)
- `max_cpu`: 2.0 (2 cores)

**Limits:**
- `max_memory_mb`: 128-16384 MB
- `max_cpu`: 0.1-32 cores

### Переменные окружения

```json
{
  "source_type": "docker-image",
  "source_url": "postgres:15",
  "app_name": "postgres",
  "env_vars": {
    "POSTGRES_PASSWORD": "secret123",
    "POSTGRES_USER": "myapp",
    "POSTGRES_DB": "myapp_db"
  }
}
```

### Маппинг портов

```json
{
  "ports": {
    "8080": "80",      // Host:Container
    "8443": "443",
    "5432": "5432"
  }
}
```

### Custom domain (для nginx/caddy reverse proxy)

```json
{
  "custom_domain": "app.example.com"
}
```

## 📊 Мониторинг установки

### Статусы

- `started` - Job создан, ждет начала
- `waiting_ssh` - Ждет доступности SSH
- `analyzing` - Анализирует source (docker-compose, etc)
- `checking_server` - Проверяет ресурсы сервера
- `installing` - Устанавливает
- `completed` - Готово! ✅
- `rejected` - Отказано из-за нехватки ресурсов/конфликта портов
- `failed` - Ошибка при установке

### Прогресс

- `0-5%` - Waiting for SSH
- `5-20%` - Analyzing source
- `20-40%` - Checking server resources
- `40-80%` - Installing
- `80-100%` - Finalizing
- `100%` - Done

## 🎓 Полные примеры

### Пример 1: Plausible Analytics (docker-compose)

```bash
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "95.179.200.45",
    "username": "root",
    "password": "server_password",
    "source_type": "docker-compose",
    "source_url": "https://raw.githubusercontent.com/plausible/hosting/master/docker-compose.yml",
    "app_name": "plausible",
    "max_memory_mb": 3072
  }'
```

**Результат через 3-5 минут:**
```json
{
  "status": "completed",
  "result": {
    "app": "plausible",
    "services": ["plausible", "plausible_db", "plausible_events_db"],
    "ports": [8000],
    "resources_allocated": {
      "memory_limit_mb": 9216,
      "cpu_limit": 2.0
    }
  }
}
```

**Доступ:** http://95.179.200.45:8000

### Пример 2: Netdata (docker-image)

```bash
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "95.179.200.45",
    "username": "root",
    "password": "server_password",
    "source_type": "docker-image",
    "source_url": "netdata/netdata:latest",
    "app_name": "netdata",
    "ports": {"19999": "19999"},
    "max_memory_mb": 512
  }'
```

**Доступ:** http://95.179.200.45:19999

### Пример 3: Твой собственный проект (GitHub)

```bash
curl -X POST http://localhost:5001/provision/universal \
  -H "X-API-Key: your-key" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "95.179.200.45",
    "username": "root",
    "password": "server_password",
    "source_type": "github-repo",
    "source_url": "https://github.com/yourusername/your-app",
    "app_name": "my-app",
    "dockerfile_path": "Dockerfile",
    "ports": {"3000": "3000"},
    "env_vars": {
      "NODE_ENV": "production",
      "PORT": "3000",
      "DATABASE_URL": "postgres://..."
    },
    "max_memory_mb": 1024,
    "max_cpu": 1.5
  }'
```

## 🔍 Проверка перед установкой

Система автоматически проверяет:

### 1. Доступные ресурсы сервера
```
RAM: 4096MB total, 3200MB available
Disk: 50GB total, 45GB available
CPU: 2 cores
Ports used: [22, 80, 443]
```

### 2. Требования приложения
```
Требуется:
  RAM: ~1500MB
  Disk: ~5GB
  Ports: [8000]
```

### 3. Вердикт
```
✅ RAM OK (need 1500MB, available 3200MB)
✅ Disk OK (need 5GB, available 45GB)
✅ Ports OK (8000 is free)
```

### 4. Добавляет safety limits
```
Added to docker-compose:
  memory: 1500m
  cpus: "2.0"
  restart: on-failure:3
```

## ⚠️ Важно знать

### Safety limits

Система ВСЕГДА добавляет resource limits, даже если в docker-compose их нет:
- `memory`: Ограничивает RAM (чтобы не убить сервер)
- `cpus`: Ограничивает CPU
- `restart: on-failure:3`: Перезапуск максимум 3 раза (не бесконечно)

### Запрещенные настройки

Система откажет если найдет:
- `privileged: true` (security risk)
- `network_mode: host` (security risk)
- Mount `/var/run/docker.sock` (security risk)
- Mount root filesystem `/:/host` (security risk)

### Минимальные требования

Сервер должен иметь:
- Минимум 256MB свободной RAM
- Минимум 2GB свободного диска
- SSH доступ
- Ubuntu 20.04+ или Debian 10+ (для Docker)

## 🆚 Сравнение с pre-configured apps

| Характеристика | Pre-configured (`/provision`) | Universal (`/provision/universal`) |
|----------------|-------------------------------|-------------------------------------|
| Количество приложений | 7 (n8n, wireguard, outline, etc) | ♾️ Любое Docker приложение |
| Проверка ресурсов | ❌ Нет | ✅ Да |
| Safety limits | ⚠️ Частично | ✅ Всегда |
| Проверка портов | ❌ Нет | ✅ Да |
| Кастомные проекты | ❌ Нет | ✅ Да |
| Простота | ✅ Проще (меньше параметров) | ⚠️ Больше параметров |

## 📝 API Reference

### Endpoint

```
POST /provision/universal
```

### Headers

```
X-API-Key: your-api-key
Content-Type: application/json
```

### Request Body

```json
{
  // REQUIRED
  "ip_address": "95.179.200.45",
  "username": "root",
  "password": "server_password",
  "source_type": "docker-compose" | "docker-image" | "github-repo",
  "source_url": "URL to source",
  "app_name": "my-app",

  // OPTIONAL
  "custom_domain": "app.example.com",
  "max_memory_mb": 2048,
  "max_cpu": 2.0,
  "ports": {"8080": "80"},
  "env_vars": {"KEY": "value"},
  "dockerfile_path": "docker/Dockerfile"
}
```

### Response (202 Accepted)

```json
{
  "job_id": "uuid",
  "status": "started",
  "status_url": "/status/{job_id}"
}
```

### Status Response (200 OK)

```json
{
  "job_id": "uuid",
  "status": "completed|failed|rejected",
  "progress": 100,
  "message": "...",
  "result": {
    "app": "app-name",
    "source_type": "...",
    "ports": [8000],
    "resources_allocated": {...},
    "server_status": {...}
  }
}
```

### Error Response (400 Bad Request)

```json
{
  "errors": [
    "Missing required field: source_url",
    "Invalid source_type. Must be one of: docker-compose, docker-image, github-repo"
  ]
}
```

## 💡 Best Practices

1. **Всегда указывай max_memory_mb** для продакшн приложений
2. **Проверяй статус** регулярно (каждые 10-30 секунд)
3. **Используй конкретные версии** вместо `latest` (например `postgres:15` вместо `postgres:latest`)
4. **Оставляй буфер** - не используй 100% доступной RAM (система оставляет 20% автоматически)
5. **Тестируй на dev сервере** сначала

## 🐛 Troubleshooting

### "SSH timeout"
- Подожди 5-10 минут после создания VPS
- Проверь firewall (должен быть открыт порт 22)
- Проверь credentials

### "Insufficient resources"
- Удали ненужные контейнеры: `docker ps -a` → `docker rm`
- Уменьши `max_memory_mb`
- Upgrade VPS

### "Port conflict"
- Проверь занятые порты: `ss -tulpn`
- Останови конфликтующий сервис
- Используй другие порты

### "Docker build failed"
- Проверь что Dockerfile валиден
- Проверь что есть интернет на сервере
- Проверь логи: `docker logs <container>`

## 🎉 Заключение

Универсальный провижинер дает тебе **неограниченную гибкость** при сохранении **безопасности** и **простоты использования**.

Больше не нужно хардкодить каждое приложение - просто дай ссылку и система сделает всё сама!

---

**Документация:** См. также README.md, QUICKSTART.md
**Support:** GitHub Issues
**Version:** 2.1

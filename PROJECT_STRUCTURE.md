# Полная структура проекта VPS Provisioner v2.0

```
vps-provisioner/
│
├── 📄 app.py                          # Главный Flask приложение
│   └── Endpoints: /provision, /status, /jobs, /stats, /cleanup, /health
│
├── 📄 config.py                       # Конфигурация (API key, timeouts, etc)
│
├── 📄 storage.py                      # SQLite хранилище для джобов
│   └── JobStorage class: save_job, get_job, list_jobs, cleanup_old_jobs
│
├── 📄 validation.py                   # Валидация входных данных
│   └── validate_provision_request, validate_ip, validate_app, etc
│
├── 📄 auth.py                         # API key authentication
│   └── @require_api_key decorator
│
├── 📄 ssh_utils.py                    # SSH утилиты
│   └── wait_for_ssh, create_ssh_client, exec_command_with_output, etc
│
├── 📁 provisioners/                   # Провизионеры для каждого приложения
│   ├── __init__.py
│   ├── n8n.py                         # n8n automation
│   ├── wireguard.py                   # WireGuard VPN
│   ├── outline.py                     # Outline wiki/docs
│   ├── vaultwarden.py                 # Vaultwarden password manager
│   ├── x3ui.py                        # 3X-UI VPN panel
│   └── filebrowser.py                 # FileBrowser file manager
│
├── 📁 templates/                      # Bash скрипты установки
│   ├── n8n_install.sh
│   ├── wireguard_install.sh
│   ├── outline_install.sh
│   ├── vaultwarden_install.sh
│   ├── 3x-ui_install.sh
│   └── filebrowser_install.sh
│
├── 📄 requirements.txt                # Python зависимости
│
├── 📄 .env.example                    # Пример environment variables
│
├── 📄 vps-provisioner.service         # Systemd service файл
│
├── 📄 test_api.py                     # Тестовый скрипт
│
├── 📄 README.md                       # Полная документация
│
├── 📄 QUICKSTART.md                   # Быстрый старт (на русском)
│
└── 📄 jobs.db                         # SQLite база (создаётся автоматически)
```

---

## 📊 Что делает каждый файл

### 🔹 app.py
- Главный Flask сервер
- REST API endpoints
- Фоновые воркеры для провизионинга
- Автоочистка старых джобов

**Endpoints:**
```
POST   /provision      - Создать джоб установки (требует API key)
GET    /status/<id>    - Проверить статус джоба
GET    /jobs           - Список всех джобов (требует API key)
GET    /stats          - Статистика (требует API key)
POST   /cleanup        - Очистить старые джобы (требует API key)
GET    /health         - Health check
```

### 🔹 config.py
Конфигурация через environment variables:
- `API_KEY` - ключ для защиты API
- `DATABASE_PATH` - путь к SQLite базе
- `MAX_JOB_AGE_HOURS` - срок жизни завершённых джобов
- `SSH_TIMEOUT`, `SSH_MAX_RETRIES` - настройки SSH
- `INSTALL_TIMEOUT` - максимальное время установки
- `SUPPORTED_APPS` - список поддерживаемых приложений

### 🔹 storage.py
SQLite база данных для джобов:
```sql
CREATE TABLE jobs (
    job_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    progress INTEGER,
    ip TEXT,
    app TEXT,
    message TEXT,
    result TEXT,
    error TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

**Методы:**
- `save_job()` - сохранить/обновить джоб
- `get_job()` - получить джоб по ID
- `list_jobs()` - список джобов (с фильтрами)
- `cleanup_old_jobs()` - удалить старые
- `get_stats()` - статистика

### 🔹 validation.py
Валидация входных данных:
- IP адрес (IPv4/IPv6)
- Имя приложения (из списка поддерживаемых)
- Username/password (минимальная длина)
- Custom domain (опционально)

### 🔹 auth.py
API key authentication через header:
```
X-API-Key: your-secret-key
```

Декоратор `@require_api_key` для защиты endpoints.

### 🔹 ssh_utils.py
Утилиты для работы с SSH:
- `wait_for_ssh()` - ждёт SSH с exponential backoff
- `create_ssh_client()` - создаёт SSH клиент
- `exec_command_with_output()` - выполняет команду и стримит output
- `check_docker_installed()` - проверяет Docker
- `check_container_running()` - проверяет контейнер
- `get_container_logs()` - получает логи контейнера

### 🔹 provisioners/*.py
Каждый provisioner:
1. Читает bash скрипт из templates/
2. Заменяет переменные (пароли, IP, etc)
3. Подключается по SSH
4. Проверяет не установлено ли уже (idempotency)
5. Загружает скрипт на сервер
6. Запускает установку
7. Ждёт завершения
8. Проверяет что всё работает
9. Возвращает результат с URL и кредами

**Возвращаемый формат:**
```json
{
  "status": "success",
  "app": "n8n",
  "url": "http://95.179.200.45:5678",
  "credentials": {
    "username": "admin",
    "password": "generated_password"
  },
  "notes": "Additional info",
  "installation_log": "/tmp/n8n_install_*.log"
}
```

### 🔹 templates/*.sh
Bash скрипты установки. Каждый скрипт:
1. ✅ Проверяет не установлено ли уже
2. 📦 Устанавливает Docker (если нужно)
3. 🐳 Запускает контейнер (или systemd service для 3X-UI)
4. ⏳ Ждёт пока запустится
5. ✅ Проверяет что работает
6. 🔥 Настраивает firewall
7. 📝 Выводит креды и URL

**Важно:** Скрипты идемпотентны - можно перезапускать.

---

## 🎯 Поток данных

### 1. Клиент делает запрос:
```
POST /provision
{
  "ip_address": "95.179.200.45",
  "username": "root",
  "password": "server_pass",
  "app": "n8n"
}
```

### 2. API валидирует и создаёт джоб:
```python
validate_provision_request()  # validation.py
job_id = uuid.uuid4()
storage.save_job(job_id, {...})  # storage.py
```

### 3. Стартует фоновый воркер:
```python
threading.Thread(target=provision_worker, ...)
```

### 4. Воркер выполняет установку:
```python
wait_for_ssh()  # ssh_utils.py
setup_n8n()     # provisioners/n8n.py
  ├── Читает templates/n8n_install.sh
  ├── Заменяет {{N8N_PASSWORD}}
  ├── Загружает на сервер
  ├── Запускает bash n8n_install.sh
  ├── Стримит output
  └── Возвращает result
storage.save_job(job_id, result)
```

### 5. Клиент проверяет статус:
```
GET /status/<job_id>
→ storage.get_job(job_id)
→ return {status, progress, result}
```

---

## 🔧 Как добавить новое приложение

### Пример: добавляем Seafile

**1. Создай provisioner:**
`provisioners/seafile.py`:
```python
def setup_seafile(ip, username, password, custom_domain=None, job_id=None):
    # Твой код
    pass
```

**2. Создай install script:**
`templates/seafile_install.sh`:
```bash
#!/bin/bash
# Установка Seafile
```

**3. Добавь в app.py:**
```python
from provisioners.seafile import setup_seafile

PROVISIONERS = {
    ...
    'seafile': setup_seafile,
}
```

**4. Добавь в config.py:**
```python
SUPPORTED_APPS = [..., 'seafile']
```

**5. Тестируй:**
```bash
python test_api.py 95.179.200.45 root pass seafile
```

---

## 📈 Масштабирование

### Для 10-50 серверов:
- ✅ Текущая архитектура отлично работает
- SQLite справляется
- 4-8 Gunicorn воркеров достаточно

### Для 50-200 серверов:
- Замени SQLite на PostgreSQL (меняй только storage.py)
- Увеличь воркеры до 16
- Добавь Redis для кэша статусов
- Может понадобится nginx балансер

### Для 200+ серверов:
- PostgreSQL обязательно
- Redis для очереди джобов (вместо threading)
- Celery workers вместо фоновых тредов
- Kubernetes для горизонтального масштабирования
- Prometheus + Grafana для мониторинга

Но для твоего бизнеса (цель 50-100 клиентов в первый год) текущая архитектура идеальна!

---

## 🚀 Деплой в продакшн

### Шаг 1: Подготовь сервер
```bash
# Ubuntu 22.04 рекомендуется
apt update && apt upgrade -y
apt install -y python3 python3-pip git
```

### Шаг 2: Клонируй код
```bash
cd /opt
# Загрузи все файлы в /opt/vps-provisioner
```

### Шаг 3: Установи зависимости
```bash
cd /opt/vps-provisioner
pip3 install -r requirements.txt
```

### Шаг 4: Настрой .env
```bash
cp .env.example .env
nano .env
# Поставь свой API_KEY
```

### Шаг 5: Создай systemd service
```bash
cp vps-provisioner.service /etc/systemd/system/
nano /etc/systemd/system/vps-provisioner.service
# Поставь свой API_KEY в Environment=

systemctl daemon-reload
systemctl enable vps-provisioner
systemctl start vps-provisioner
```

### Шаг 6: Проверь что работает
```bash
systemctl status vps-provisioner
curl http://localhost:5001/health
```

### Шаг 7: Настрой firewall (важно!)
```bash
# НЕ открывай наружу!
# Используй VPN/Tailscale или nginx с auth
ufw allow 22/tcp
ufw allow from YOUR_IP to any port 5001
ufw enable
```

---

## 💡 Полезные команды

```bash
# Смотреть логи в реальном времени
journalctl -u vps-provisioner -f

# Рестарт сервиса
systemctl restart vps-provisioner

# Посмотреть базу джобов
sqlite3 /opt/vps-provisioner/jobs.db "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10"

# Очистить старые джобы
curl -X POST http://localhost:5001/cleanup -H "X-API-Key: твой-ключ"

# Посмотреть статистику
curl http://localhost:5001/stats -H "X-API-Key: твой-ключ"

# Посмотреть логи установки
ls -lah /tmp/*_install_*.log
tail -100 /tmp/n8n_install_95_179_200_45.log
```

---

## ✅ Что получилось

1. ✅ **Production-ready** сервис
2. ✅ **6 приложений** из коробки
3. ✅ **Все улучшения** из code review
4. ✅ **Полная документация** (README + QUICKSTART)
5. ✅ **Тестовый скрипт** для проверки
6. ✅ **Systemd service** для автозапуска
7. ✅ **Idempotent скрипты** - можно перезапускать
8. ✅ **Детальные логи** для отладки
9. ✅ **Защищённый API** с ключами
10. ✅ **SQLite база** которая не теряется

---

**Готово к использованию!** 🎉

Начни с:
```bash
cd /opt/vps-provisioner
python app.py
```

Протестируй:
```bash
python test_api.py 95.179.200.45 root password n8n
```

Задеплой в продакшн:
```bash
systemctl start vps-provisioner
```

**И начинай зарабатывать! 💰**

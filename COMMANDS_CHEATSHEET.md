# 🚀 Шпаргалка команд

## Быстрый старт за 5 минут

```bash
# 1. Перейди в директорию
cd /opt/vps-provisioner

# 2. Установи зависимости
pip install -r requirements.txt

# 3. Скопируй .env
cp .env.example .env

# 4. Измени API key
nano .env
# Поставь: API_KEY=твой-секретный-ключ

# 5. Запусти
python app.py
```

---

## Тестирование всех приложений

```bash
# n8n (автоматизация)
python test_api.py 95.179.200.45 root password n8n

# WireGuard (VPN)
python test_api.py 95.179.200.45 root password wireguard

# Outline (wiki/документация)
python test_api.py 95.179.200.45 root password outline

# Vaultwarden (пароли)
python test_api.py 95.179.200.45 root password vaultwarden

# 3X-UI (продвинутый VPN)
python test_api.py 95.179.200.45 root password 3x-ui

# Seafile (облако + мобильные приложения) ⭐
python test_api.py 95.179.200.45 root password seafile

# FileBrowser (простое хранилище)
python test_api.py 95.179.200.45 root password filebrowser
```

---

## API команды (curl)

### Health check
```bash
curl http://localhost:5001/health
```

### Создать задачу установки
```bash
curl -X POST http://localhost:5001/provision \
  -H "X-API-Key: твой-ключ" \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "95.179.200.45",
    "username": "root",
    "password": "server_password",
    "app": "seafile"
  }'

# Вернёт job_id
```

### Проверить статус
```bash
curl http://localhost:5001/status/JOB_ID
```

### Список всех задач
```bash
curl http://localhost:5001/jobs \
  -H "X-API-Key: твой-ключ"
```

### Статистика
```bash
curl http://localhost:5001/stats \
  -H "X-API-Key: твой-ключ"
```

### Очистить старые задачи
```bash
curl -X POST http://localhost:5001/cleanup \
  -H "X-API-Key: твой-ключ"
```

---

## Production deployment

### Systemd service
```bash
# Скопируй service файл
cp vps-provisioner.service /etc/systemd/system/

# Отредактируй (поставь свой API_KEY)
nano /etc/systemd/system/vps-provisioner.service

# Перезагрузи systemd
systemctl daemon-reload

# Запусти
systemctl enable vps-provisioner
systemctl start vps-provisioner

# Проверь статус
systemctl status vps-provisioner

# Смотри логи
journalctl -u vps-provisioner -f
```

### Gunicorn (без systemd)
```bash
# 4 воркера
gunicorn -w 4 -b 0.0.0.0:5001 --timeout 1200 app:app

# 8 воркеров
gunicorn -w 8 -b 0.0.0.0:5001 --timeout 1200 app:app

# С логами
gunicorn -w 4 -b 0.0.0.0:5001 --timeout 1200 \
  --access-logfile - --error-logfile - app:app
```

---

## Мониторинг и отладка

### Логи сервиса
```bash
# Real-time
journalctl -u vps-provisioner -f

# Последние 100 строк
journalctl -u vps-provisioner -n 100

# За сегодня
journalctl -u vps-provisioner --since today
```

### Логи установки приложений
```bash
# Список всех логов
ls -lah /tmp/*_install_*.log

# Последняя установка n8n
tail -100 /tmp/n8n_install_*.log

# Seafile
tail -100 /tmp/seafile_install_*.log
```

### База данных задач
```bash
# Посмотреть все задачи
sqlite3 jobs.db "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 10"

# Только failed
sqlite3 jobs.db "SELECT * FROM jobs WHERE status='failed'"

# Статистика
sqlite3 jobs.db "SELECT status, COUNT(*) FROM jobs GROUP BY status"

# Очистить старые
sqlite3 jobs.db "DELETE FROM jobs WHERE created_at < date('now', '-7 days')"
```

### Проверка серверов
```bash
# Проверить SSH доступ
ssh root@95.179.200.45

# Проверить Docker
ssh root@95.179.200.45 'docker ps'

# Проверить контейнер
ssh root@95.179.200.45 'docker logs seafile'

# Проверить порты
ssh root@95.179.200.45 'netstat -tulpn | grep LISTEN'
```

---

## Firewall настройка

### На сервере provisioner (не открывать наружу!)
```bash
# Разрешить только с твоего IP
ufw allow from ТВО_IP to any port 5001

# SSH
ufw allow 22/tcp

# Включить
ufw enable
```

### На VPS клиента (после установки приложений)
```bash
# Проверить какие порты открыты
ssh root@CLIENT_IP 'ufw status numbered'

# Открыть вручную если нужно
ssh root@CLIENT_IP 'ufw allow 8000/tcp'  # Seafile
```

---

## Резервное копирование

### База данных задач
```bash
# Бэкап
cp jobs.db jobs_backup_$(date +%Y%m%d).db

# Автоматический бэкап (cron)
crontab -e
# Добавь:
0 2 * * * cp /opt/vps-provisioner/jobs.db /opt/vps-provisioner/backups/jobs_$(date +\%Y\%m\%d).db
```

### Логи
```bash
# Архивировать старые логи
tar -czf logs_$(date +%Y%m%d).tar.gz /tmp/*_install_*.log

# Удалить старые (старше 30 дней)
find /tmp -name "*_install_*.log" -mtime +30 -delete
```

---

## Производительность

### Проверить нагрузку
```bash
# CPU и RAM
htop

# Процессы Python
ps aux | grep gunicorn

# Количество воркеров
pgrep -a gunicorn | wc -l
```

### Оптимизация
```bash
# Больше воркеров для большой нагрузки
# Формула: (2 * CPU cores) + 1
# Для 4 cores = 9 воркеров
gunicorn -w 9 -b 0.0.0.0:5001 --timeout 1200 app:app

# Увеличить timeout для медленных установок
gunicorn -w 4 -b 0.0.0.0:5001 --timeout 1800 app:app
```

---

## Обновление

```bash
# Остановить сервис
systemctl stop vps-provisioner

# Обновить код
cd /opt/vps-provisioner
# (загрузи новые файлы)

# Обновить зависимости
pip install -r requirements.txt --upgrade

# Запустить
systemctl start vps-provisioner

# Проверить
systemctl status vps-provisioner
```

---

## Troubleshooting

### Сервис не запускается
```bash
# Проверить синтаксис Python
python app.py
# Если ошибка - исправь

# Проверить порт
lsof -i :5001
# Если занят - убей процесс или измени порт
```

### SSH timeout при установке
```bash
# Увеличить таймауты в config.py
SSH_TIMEOUT=60
SSH_MAX_RETRIES=20
INSTALL_TIMEOUT=1800
```

### База данных повреждена
```bash
# Восстановить из бэкапа
cp jobs_backup_20250101.db jobs.db

# Или создать новую
rm jobs.db
python app.py  # Создаст новую
```

### Контейнер не запускается на клиентском VPS
```bash
# Зайти на VPS
ssh root@CLIENT_IP

# Проверить Docker
docker ps -a

# Логи контейнера
docker logs CONTAINER_NAME

# Рестарт
docker restart CONTAINER_NAME

# Проверить ресурсы
free -h
df -h
```

---

## Полезные алиасы (добавь в ~/.bashrc)

```bash
# Alias для provisioner
alias prov='cd /opt/vps-provisioner'
alias provlog='journalctl -u vps-provisioner -f'
alias provstatus='systemctl status vps-provisioner'
alias provrestart='systemctl restart vps-provisioner'

# Alias для тестирования
alias test-n8n='python /opt/vps-provisioner/test_api.py'

# Alias для логов установки
alias instlog='ls -lah /tmp/*_install_*.log'

# Alias для БД
alias jobsdb='sqlite3 /opt/vps-provisioner/jobs.db'
```

Перезагрузи shell:
```bash
source ~/.bashrc
```

Теперь можешь:
```bash
prov              # перейти в директорию
provlog           # смотреть логи
provstatus        # проверить статус
provrestart       # рестарт
instlog           # список логов установки
```

---

## 🎯 Ежедневные команды

### Утром (проверка):
```bash
provstatus        # Сервис работает?
provlog           # Ошибки за ночь?
```

### Новый клиент:
```bash
# 1. Заказать VPS у SpaceCore
# 2. Подождать 5 минут
# 3. Запустить установку
python test_api.py IP root PASSWORD seafile

# 4. Проверить статус
curl http://localhost:5001/status/JOB_ID

# 5. Отправить клиенту креды
```

### Вечером (cleanup):
```bash
# Очистить старые задачи
curl -X POST http://localhost:5001/cleanup -H "X-API-Key: ключ"

# Проверить место на диске
df -h

# Архивировать старые логи
tar -czf logs_$(date +%Y%m%d).tar.gz /tmp/*_install_*.log
find /tmp -name "*_install_*.log" -mtime +7 -delete
```

---

## 📱 Seafile специфичные команды

### На VPS клиента:
```bash
# Проверить Seafile
ssh root@CLIENT_IP 'docker ps | grep seafile'

# Логи Seafile
ssh root@CLIENT_IP 'docker logs seafile'

# Рестарт всех сервисов Seafile
ssh root@CLIENT_IP 'cd /opt/seafile && docker compose restart'

# Проверить БД
ssh root@CLIENT_IP 'docker exec seafile-mysql mysql -uroot -pPASSWORD -e "SHOW DATABASES;"'
```

### Креды Seafile:
```bash
# Посмотреть сохранённые креды
ssh root@CLIENT_IP 'cat /opt/seafile/credentials.txt'
```

---

**Сохрани этот файл - пригодится каждый день!** 📌

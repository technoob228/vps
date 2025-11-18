# ✅ Исправления - Быстрая справка

## Что исправлено

### 1. Outline ✅
**Проблема:** Ошибка "database does not support SSL connections"  
**Решение:** Добавлен `PGSSLMODE=disable` в `.env`

### 2. Seafile ✅  
**Проблема 1:** Network error при загрузке файлов  
**Проблема 2:** Неправильный nginx конфиг (`server_name http://IP`)  
**Проблема 3:** Лимит 1MB на файл

**Решение:** Автоматическая конфигурация:
- `FILE_SERVER_ROOT = 'http://IP:8000/seafhttp'`
- Nginx исправлен (убран `http://` из `server_name`)
- Лимит увеличен до 50GB

---

## 🧪 Быстрый тест

### Outline
```bash
python test_api.py YOUR_IP root password outline
# Открой URL → должна быть форма для email (БЕЗ ошибки)
```

### Seafile
```bash
python test_api.py YOUR_IP root password seafile
# Открой URL → залогинься → загрузи файл (должен загрузиться БЕЗ Network error)
```

---

## 🔧 Ручное исправление (если нужно)

### Если Outline не работает:
```bash
ssh root@YOUR_IP
echo "PGSSLMODE=disable" >> /opt/outline/.env
cd /opt/outline && docker compose restart outline
```

### Если Seafile не грузит файлы:
```bash
ssh root@YOUR_IP

# Добавь FILE_SERVER_ROOT
docker exec seafile bash -c "echo \"FILE_SERVER_ROOT = 'http://YOUR_IP:8000/seafhttp'\" >> /opt/seafile/conf/seahub_settings.py"
docker exec seafile bash -c "echo \"MAX_UPLOAD_FILE_SIZE = 53687091200\" >> /opt/seafile/conf/seahub_settings.py"

# Исправь nginx
docker exec seafile sed -i 's|server_name http://YOUR_IP|server_name YOUR_IP|g' /etc/nginx/sites-enabled/seafile.nginx.conf
docker exec seafile sed -i 's|client_max_body_size.*|client_max_body_size 50G;|g' /etc/nginx/sites-enabled/seafile.nginx.conf

# Перезапусти
docker exec seafile nginx -s reload
cd /opt/seafile && docker compose restart seafile
```

---

## ✅ Готово!

Теперь:
- Outline работает без ошибок SSL
- Seafile загружает файлы до 50GB
- Всё настроено автоматически при установке

**Можно тестировать на клиентах! 🎉**

# 🐛 Bug Fixes - Outline & Seafile

## ✅ Что исправлено

### 1. **Outline - PostgreSQL SSL Error**

**Проблема:**
```
The database does not support SSL connections. 
Set the `PGSSLMODE` environment variable to `disable`
```

**Решение:**
Добавлена переменная `PGSSLMODE=disable` в файл `.env`

**Где изменено:**
- `templates/outline_install.sh` - строка 48

**Изменения:**
```bash
DATABASE_URL=postgres://outline:outline@postgres:5432/outline
DATABASE_URL_TEST=postgres://outline:outline@postgres:5432/outline-test
+PGSSLMODE=disable  # ← ДОБАВЛЕНО
REDIS_URL=redis://redis:6379
```

---

### 2. **Seafile - File Upload Errors**

**Проблема 1: Network error при загрузке файлов**
- Браузер отправляет файл на `/seafhttp`
- Seafile не знает правильный URL для fileserver
- Результат: Network error

**Проблема 2: Неправильная nginx конфигурация**
- `server_name http://IP` (не должно быть `http://`)

**Проблема 3: Ограничение размера файла**
- По умолчанию nginx разрешает только 1MB
- Нужно до 50GB

**Решение:**
Автоматическая конфигурация после установки:

1. **FILE_SERVER_ROOT** в `/opt/seafile/conf/seahub_settings.py`:
```python
FILE_SERVER_ROOT = 'http://IP:8000/seafhttp'
MAX_UPLOAD_FILE_SIZE = 53687091200  # 50GB
FILE_UPLOAD_MAX_MEMORY_SIZE = 209715200  # 200MB
```

2. **Nginx исправления** в `/etc/nginx/sites-enabled/seafile.nginx.conf`:
```nginx
server_name IP;  # без http://
client_max_body_size 50G;  # увеличен лимит
```

3. **Nginx reload** внутри контейнера

**Где изменено:**
- `templates/seafile_install.sh` - строки 122-150

**Добавленные команды:**
```bash
# Configure FILE_SERVER_ROOT
docker exec seafile bash -c "cat >> /opt/seafile/conf/seahub_settings.py << 'EOFPY'
FILE_SERVER_ROOT = 'http://{{SERVER_IP}}:8000/seafhttp'
MAX_UPLOAD_FILE_SIZE = 53687091200
FILE_UPLOAD_MAX_MEMORY_SIZE = 209715200
EOFPY"

# Fix nginx
docker exec seafile sed -i 's|server_name http://IP|server_name IP|g' /etc/nginx/...
docker exec seafile sed -i 's|client_max_body_size.*|client_max_body_size 50G;|g' ...
docker exec seafile nginx -s reload
```

---

## 🧪 Как протестировать

### Тест 1: Outline

```bash
# 1. Установка
python test_api.py YOUR_IP root password outline

# 2. Дождись завершения (10-15 минут)

# 3. Открой URL в браузере
# Должно открыться БЕЗ ошибки про SSL

# 4. Введи email
# Должна появиться форма для email (не ошибка)

# 5. Проверь логи на magic link
docker logs outline | grep "token="
```

**Ожидаемый результат:**
- ✅ Страница открывается
- ✅ Можно ввести email
- ✅ Нет ошибок про PostgreSQL SSL

---

### Тест 2: Seafile - Загрузка файлов

```bash
# 1. Установка
python test_api.py YOUR_IP root password seafile

# 2. Дождись завершения (10-15 минут)

# 3. Открой URL в браузере
http://YOUR_IP:8000

# 4. Залогинься (email + password из ответа API)

# 5. Создай новую библиотеку
Нажми "New Library" → введи имя → Create

# 6. Загрузи тестовый файл
Нажми "Upload" → выбери любой файл → Upload

# 7. Загрузи БОЛЬШОЙ файл (100MB+)
Создай файл: dd if=/dev/zero of=testfile.bin bs=1M count=100
Загрузи через Seafile web interface
```

**Ожидаемый результат:**
- ✅ Маленькие файлы загружаются успешно
- ✅ Большие файлы (100MB+) загружаются успешно
- ✅ Нет "Network error"
- ✅ Файлы появляются в библиотеке

---

### Тест 3: Seafile - Мобильное приложение

```bash
# На телефоне:

# 1. Скачай приложение
iOS: Seafile Pro (App Store)
Android: Seafile (Google Play)

# 2. Добавь сервер
- URL: http://YOUR_IP:8000
- Email: admin@seafile.local
- Password: (из API response)

# 3. Включи автозагрузку фото
Settings → Camera Upload → Enable

# 4. Сделай фотку на телефоне

# 5. Проверь на сервере через браузер
Зайди в библиотеку "My Photos"
Фотка должна появиться автоматически
```

**Ожидаемый результат:**
- ✅ Приложение подключается к серверу
- ✅ Видны все библиотеки
- ✅ Автозагрузка фото работает
- ✅ Фото появляются на сервере

---

## 🔍 Как проверить конфигурацию вручную

### Проверка Outline

```bash
ssh root@YOUR_IP

# Проверь .env файл
cat /opt/outline/.env | grep PGSSLMODE

# Должен вернуть:
# PGSSLMODE=disable
```

### Проверка Seafile

```bash
ssh root@YOUR_IP

# Проверь seahub_settings.py
docker exec seafile cat /opt/seafile/conf/seahub_settings.py | tail -10

# Должен содержать:
# FILE_SERVER_ROOT = 'http://YOUR_IP:8000/seafhttp'
# MAX_UPLOAD_FILE_SIZE = 53687091200
# FILE_UPLOAD_MAX_MEMORY_SIZE = 209715200

# Проверь nginx конфиг
docker exec seafile cat /etc/nginx/sites-enabled/seafile.nginx.conf | grep server_name

# Должен вернуть:
# server_name YOUR_IP;  (БЕЗ http://)

# Проверь upload limit
docker exec seafile cat /etc/nginx/sites-enabled/seafile.nginx.conf | grep client_max_body_size

# Должен вернуть:
# client_max_body_size 50G;
```

---

## 📝 Если что-то не работает

### Outline не открывается

```bash
# Проверь логи
docker logs outline

# Проверь PostgreSQL
docker logs outline-postgres

# Перезапусти контейнер
cd /opt/outline
docker compose restart outline
```

### Seafile - файлы не загружаются

```bash
# Проверь логи
docker logs seafile

# Проверь nginx статус
docker exec seafile nginx -t

# Применить конфигурацию вручную:
docker exec seafile bash -c "cat >> /opt/seafile/conf/seahub_settings.py << 'EOF'

FILE_SERVER_ROOT = 'http://YOUR_IP:8000/seafhttp'
MAX_UPLOAD_FILE_SIZE = 53687091200
FILE_UPLOAD_MAX_MEMORY_SIZE = 209715200
EOF"

docker exec seafile bash -c "sed -i 's|server_name http://YOUR_IP|server_name YOUR_IP|g' /etc/nginx/sites-enabled/seafile.nginx.conf"

docker exec seafile bash -c "sed -i 's|client_max_body_size.*|client_max_body_size 50G;|g' /etc/nginx/sites-enabled/seafile.nginx.conf"

docker exec seafile nginx -s reload

# Перезапусти контейнер
cd /opt/seafile
docker compose restart seafile
```

---

## ✅ Checklist финального теста

- [ ] Outline открывается без ошибок
- [ ] Outline показывает форму для email
- [ ] Seafile открывается в браузере
- [ ] Seafile позволяет логин
- [ ] Можно создать новую библиотеку
- [ ] Маленькие файлы загружаются (<1MB)
- [ ] Большие файлы загружаются (>100MB)
- [ ] Мобильное приложение подключается
- [ ] Автозагрузка фото работает

---

## 🎉 После успешного теста

Если всё работает:

1. ✅ Закоммить изменения в git
2. ✅ Обновить документацию
3. ✅ Протестировать на production сервере
4. ✅ Начать использовать для клиентов!

**Готово к запуску! 🚀**

# Развёртывание GroupBuy Bot вместе с Mattermost на одном сервере

Данное руководство описывает, как запустить собственный сервер Mattermost и бота
совместных закупок (GroupBuy Bot) на одном сервере с помощью Docker Compose.

## Содержание

1. [Требования к серверу](#1-требования-к-серверу)
2. [Подготовка окружения](#2-подготовка-окружения)
3. [Первый запуск и настройка Mattermost](#3-первый-запуск-и-настройка-mattermost)
4. [Создание учётной записи бота](#4-создание-учётной-записи-бота)
5. [Настройка исходящего вебхука](#5-настройка-исходящего-вебхука)
6. [Финальная настройка .env и запуск всех сервисов](#6-финальная-настройка-env-и-запуск-всех-сервисов)
7. [Проверка работоспособности](#7-проверка-работоспособности)
8. [Настройка SSL и публичный доступ](#8-настройка-ssl-и-публичный-доступ)
9. [Резервное копирование](#9-резервное-копирование)
10. [Обновление Mattermost](#10-обновление-mattermost)
11. [Устранение неполадок](#11-устранение-неполадок)

---

## Архитектура развёртывания

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Host                              │
│                                                                 │
│  ┌──────────────── groupbuy-network ──────────────────────────┐ │
│  │                                                             │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────────────┐ │ │
│  │  │  core    │  │   bot    │  │   mattermost-adapter     │ │ │
│  │  │  :8000   │  │  :8001   │  │   :8002 (webhook)        │ │ │
│  │  └────┬─────┘  └────┬─────┘  └────────────┬─────────────┘ │ │
│  │       │              │                      │               │ │
│  │  ┌────┴──────┐  ┌────┴─────┐               │               │ │
│  │  │ postgres  │  │  redis   │               │               │ │
│  │  │  :5432    │  │  :6379   │               │               │ │
│  │  └───────────┘  └──────────┘               │               │ │
│  └─────────────────────────────────────────────┼───────────────┘ │
│                                                │                 │
│  ┌──────────────── mattermost-network ──────────┼───────────────┐ │
│  │                                             │               │ │
│  │  ┌──────────────────────┐   ┌───────────────┴─────────────┐ │ │
│  │  │  mattermost-postgres │   │         mattermost          │ │ │
│  │  │  (internal only)     │◄─►│         :8065               │ │ │
│  │  └──────────────────────┘   └─────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

`mattermost-adapter` находится в **обеих** сетях: получает вебхуки от Mattermost
и пересылает команды боту GroupBuy.

---

## 1. Требования к серверу

### Минимальные характеристики

| Ресурс | Минимум     | Рекомендуется |
|--------|-------------|---------------|
| CPU    | 2 ядра      | 4 ядра        |
| RAM    | 4 ГБ        | 8 ГБ          |
| Диск   | 40 ГБ SSD   | 80 ГБ SSD     |
| ОС     | Ubuntu 22.04 LTS / Debian 12 | — |

> Суммарное потребление RAM при запуске всех сервисов — около 2–3 ГБ.

### Необходимое программное обеспечение

```bash
docker --version          # нужен Docker 24+
docker compose version    # нужен Docker Compose 2.20+
git --version
```

Если Docker не установлен:

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
```

### Порты, которые должны быть открыты

| Порт  | Сервис              | Публичный доступ?             |
|-------|---------------------|-------------------------------|
| 8065  | Mattermost          | Да (для пользователей)        |
| 8000  | GroupBuy API        | По необходимости              |
| 3000  | GroupBuy Frontend   | По необходимости              |
| 8002  | Mattermost Adapter  | Нет (только внутри Docker)    |
| 80/443| Nginx (опционально) | Да (HTTPS)                    |

---

## 2. Подготовка окружения

### 2.1 Клонирование репозитория

```bash
git clone https://github.com/MixaByk1996/mattermost.git
cd mattermost/mattermost-master
```

### 2.2 Создание файла переменных окружения

```bash
cp .env.example .env
nano .env
```

На этом этапе заполните базовые переменные. Токены Mattermost (`MATTERMOST_BOT_TOKEN`,
`MATTERMOST_WEBHOOK_SECRET`) будут получены позже — после первоначальной настройки
сервера Mattermost через веб-интерфейс:

```env
# ── База данных GroupBuy ─────────────────────────────────────────
DB_NAME=groupbuy
DB_USER=postgres
DB_PASSWORD=ВашНадёжныйПароль123

# ── База данных Mattermost (отдельный экземпляр PostgreSQL) ──────
MM_DB_PASSWORD=ДругойНадёжныйПароль456

# ── Публичный URL Mattermost ─────────────────────────────────────
# Для локального тестирования:
MATTERMOST_SITE_URL=http://localhost:8065
# Для продакшена с доменом (заменить после настройки SSL):
# MATTERMOST_SITE_URL=https://mattermost.yourdomain.com

# ── Mattermost токены (заполним после шага 4–5) ──────────────────
MATTERMOST_BOT_TOKEN=
MATTERMOST_TEAM_ID=
MATTERMOST_CHANNEL_ID=
MATTERMOST_WEBHOOK_SECRET=

# ── GroupBuy ─────────────────────────────────────────────────────
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
JWT_SECRET=случайная-строка-минимум-32-символа
LOG_LEVEL=INFO
RUST_LOG=info,groupbuy_api=debug
```

---

## 3. Первый запуск и настройка Mattermost

На первом шаге запустим только Mattermost и его базу данных, чтобы пройти
начальную настройку через веб-интерфейс.

### 3.1 Запуск Mattermost

```bash
docker compose up -d mattermost-postgres mattermost
```

Дождитесь перехода контейнера в состояние `healthy` (30–90 секунд при первом запуске):

```bash
# Следить за статусом (Ctrl+C для выхода)
watch docker compose ps mattermost
```

### 3.2 Создание учётной записи администратора

Откройте в браузере: **http://localhost:8065** (или `http://ВАШ_IP_СЕРВЕРА:8065`).

Mattermost предложит создать первую учётную запись — она автоматически получит
права системного администратора:

- **Email:** admin@example.com
- **Имя пользователя:** admin
- **Пароль:** надёжный пароль (минимум 12 символов)

> Запишите эти данные — они нужны для дальнейшей настройки.

### 3.3 Создание команды (Team)

После регистрации Mattermost предложит создать команду (аналог workspace в Slack):

- **Название команды:** GroupBuy (или любое другое)
- **URL команды:** groupbuy (только латиница, без пробелов)

Нажмите **Finish**.

### 3.4 Получение ID команды

Идентификатор команды нужен для переменной `MATTERMOST_TEAM_ID`.

**Через системную консоль:**

1. Нажмите на значок меню (≡ слева вверху) → **System Console**
2. Перейдите в **User Management** → **Teams**
3. Нажмите на название вашей команды
4. В адресной строке браузера скопируйте ID команды из URL:
   `/admin_console/user_management/teams/**ВОТ_ЭТОТ_ID**`

**Через API (если установлен curl):**

```bash
# Сначала получите токен сессии администратора
TOKEN=$(curl -si http://localhost:8065/api/v4/users/login \
  -d '{"login_id":"admin","password":"ВАШ_ПАРОЛЬ"}' \
  | grep -i 'token:' | awk '{print $2}' | tr -d '\r')

# Получите список команд
curl -s http://localhost:8065/api/v4/teams \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Поле `"id"` в выводе — это и есть `MATTERMOST_TEAM_ID`.

### 3.5 Получение ID канала (опционально)

Если бот должен публиковать объявления в конкретный канал:

1. Откройте нужный канал в Mattermost
2. Нажмите на название канала в заголовке → **View Info**
3. Скопируйте значение поля **Channel ID**

---

## 4. Создание учётной записи бота

Бот-аккаунт позволяет адаптеру отправлять сообщения от имени бота, а не
от имени реального пользователя.

### 4.1 Включение Bot Accounts

1. Откройте **System Console** (≡ → System Console)
2. Перейдите в **Integrations** → **Bot Accounts**
3. Установите **Enable Bot Account Creation** → **true**
4. Нажмите **Save**

### 4.2 Создание бот-аккаунта

1. Перейдите в **Integrations** → **Bot Accounts** → **Add Bot Account**
2. Заполните форму:

| Поле         | Значение                              |
|--------------|---------------------------------------|
| Username     | `groupbuy-bot`                        |
| Display Name | GroupBuy Bot                          |
| Description  | Бот для управления совместными закупками |
| Role         | Member                                |

3. Нажмите **Create Bot Account**

### 4.3 Сохранение токена бота

После создания Mattermost **один раз** покажет токен доступа. Скопируйте его немедленно —
повторно он показан не будет:

```
Token: xoxb-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Это значение нужно будет указать в `MATTERMOST_BOT_TOKEN`.

> Если токен был утерян: **Integrations** → **Bot Accounts** →
> найдите `groupbuy-bot` → **Create New Token**.

### 4.4 Добавление бота в команду и канал

Бот-аккаунт нужно вручную добавить в команду:

1. **System Console** → **User Management** → **Teams** → ваша команда → **Manage Members**
2. Введите `groupbuy-bot` → **Add**

Добавление бота в канал:

1. Откройте нужный канал
2. Нажмите на название канала → **Add Members**
3. Найдите `groupbuy-bot` → **Add**

---

## 5. Настройка исходящего вебхука

Исходящий вебхук заставляет Mattermost отправлять сообщения пользователей
в адаптер GroupBuy Bot, который затем передаёт их боту.

### 5.1 Включение исходящих вебхуков

1. **System Console** → **Integrations** → **Integration Management**
2. Убедитесь, что **Enable Outgoing Webhooks** = **true**
3. Нажмите **Save**

### 5.2 Создание исходящего вебхука

1. Перейдите в **Integrations** → **Outgoing Webhooks** → **Add Outgoing Webhook**
2. Заполните форму:

| Поле           | Значение                                          |
|----------------|---------------------------------------------------|
| Title          | GroupBuy Bot                                      |
| Content Type   | `application/json`                                |
| Channel        | Нужный канал (или пусто — для всех каналов)       |
| Trigger Words  | `/buy` (или другие команды бота, через запятую)   |
| Trigger When   | First word of a message matches a trigger word    |
| Callback URLs  | `http://mattermost-adapter:8002/webhook`          |
| Username       | groupbuy-bot                                      |

> **Важно:** Callback URL использует имя Docker-сервиса `mattermost-adapter` —
> это работает потому, что Mattermost и адаптер находятся в одной Docker-сети
> (`mattermost-network`). При развёртывании на разных серверах укажите
> реальный IP/домен адаптера.

3. Нажмите **Save**

### 5.3 Сохранение секретного токена вебхука

После сохранения вебхука Mattermost показывает **Token**. Скопируйте его —
он будет указан в переменной `MATTERMOST_WEBHOOK_SECRET`.

---

## 6. Финальная настройка .env и запуск всех сервисов

### 6.1 Обновление .env

Откройте `.env` и заполните ранее оставленные пустыми переменные:

```bash
nano .env
```

```env
# Токен бот-аккаунта из шага 4.3
MATTERMOST_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ID команды из шага 3.4
MATTERMOST_TEAM_ID=abcdef1234567890abcdef1234567890

# ID канала для объявлений из шага 3.5 (опционально)
MATTERMOST_CHANNEL_ID=zyxwvu9876543210zyxwvu98765432

# Секретный токен вебхука из шага 5.3
MATTERMOST_WEBHOOK_SECRET=токен-из-настроек-вебхука
```

### 6.2 Запуск всех сервисов

```bash
docker compose up -d
```

### 6.3 Проверка статуса контейнеров

```bash
docker compose ps
```

Ожидаемый результат — все сервисы в состоянии `running` или `healthy`:

```
NAME                                    STATUS      PORTS
...-core-1                              healthy     0.0.0.0:8000->8000/tcp
...-bot-1                               running     0.0.0.0:8001->8001/tcp
...-mattermost-adapter-1                running     0.0.0.0:8002->8002/tcp
...-mattermost-1                        healthy     0.0.0.0:8065->8065/tcp
...-mattermost-postgres-1               healthy
...-postgres-1                          healthy     0.0.0.0:5432->5432/tcp
...-redis-1                             healthy     0.0.0.0:6379->6379/tcp
...-frontend-react-1                    running     0.0.0.0:3000->3000/tcp
...-websocket-server-1                  running     0.0.0.0:8765->8765/tcp
```

---

## 7. Проверка работоспособности

### 7.1 Проверка Mattermost API

```bash
curl -s http://localhost:8065/api/v4/system/ping | python3 -m json.tool
# Ожидается: {"status": "OK", ...}
```

### 7.2 Проверка адаптера GroupBuy

```bash
curl -s http://localhost:8002/health
# Ожидается: {"status": "healthy"}
```

### 7.3 Проверка GroupBuy API

```bash
curl -s http://localhost:8000/api/users/ | head -c 200
```

### 7.4 Тестирование бота в Mattermost

1. Войдите в Mattermost и перейдите в настроенный канал
2. Напишите сообщение с триггерным словом, например: `/buy`
3. Бот должен ответить

Если ответа нет — проверьте логи:

```bash
# Логи адаптера (принимает вебхуки от Mattermost)
docker compose logs -f mattermost-adapter

# Логи бот-сервиса (обрабатывает команды)
docker compose logs -f bot
```

### 7.5 Проверка связи адаптера с Mattermost

```bash
docker compose exec mattermost-adapter \
  curl -s http://mattermost:8065/api/v4/system/ping
# Ожидается: {"status":"OK"}
```

---

## 8. Настройка SSL и публичный доступ

Для продакшена рекомендуется использовать HTTPS. Стандартный подход —
вынести Mattermost за Nginx с SSL-терминацией через Let's Encrypt.

### 8.1 Установка Nginx и получение сертификата

```bash
sudo apt install nginx certbot python3-certbot-nginx

# Получить сертификат
sudo certbot --nginx -d mattermost.yourdomain.com \
  --email admin@yourdomain.com --agree-tos --non-interactive
```

### 8.2 Конфигурация Nginx для Mattermost

Создайте файл `/etc/nginx/sites-available/mattermost`:

```nginx
upstream mattermost_backend {
    server localhost:8065;
    keepalive 32;
}

server {
    listen 80;
    server_name mattermost.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mattermost.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/mattermost.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mattermost.yourdomain.com/privkey.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://mattermost_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400s;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/mattermost /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### 8.3 Обновление MATTERMOST_SITE_URL

После настройки HTTPS обновите `.env`:

```env
MATTERMOST_SITE_URL=https://mattermost.yourdomain.com
```

Перезапустите Mattermost, чтобы применить изменение:

```bash
docker compose restart mattermost
```

### 8.4 Автообновление SSL-сертификата (cron)

```bash
echo "0 3 1 * * certbot renew --quiet && systemctl reload nginx" | sudo crontab -
```

---

## 9. Резервное копирование

### 9.1 Резервное копирование баз данных

```bash
# База данных GroupBuy
docker compose exec -T postgres \
  pg_dump -U postgres groupbuy | gzip > backup_groupbuy_$(date +%Y%m%d).sql.gz

# База данных Mattermost
docker compose exec -T mattermost-postgres \
  pg_dump -U mmuser mattermost | gzip > backup_mattermost_$(date +%Y%m%d).sql.gz
```

### 9.2 Резервное копирование файлов Mattermost

Загруженные пользователями файлы хранятся в Docker volume `mattermost_data`:

```bash
mkdir -p backups

docker run --rm \
  -v mattermost-master_mattermost_data:/source:ro \
  -v $(pwd)/backups:/dest \
  alpine tar czf /dest/mattermost_data_$(date +%Y%m%d).tar.gz -C /source .
```

### 9.3 Автоматическое резервное копирование (cron)

```bash
# crontab -e
0 3 * * * cd /opt/mattermost/mattermost-master && \
  docker compose exec -T postgres \
    pg_dump -U postgres groupbuy | gzip > /backups/groupbuy_$(date +\%Y\%m\%d).sql.gz && \
  docker compose exec -T mattermost-postgres \
    pg_dump -U mmuser mattermost | gzip > /backups/mattermost_$(date +\%Y\%m\%d).sql.gz
```

---

## 10. Обновление Mattermost

> **Внимание:** Mattermost не поддерживает обновление через несколько мажорных
> версий сразу. Обновляйте последовательно: 9.x → 10.x → 11.x.

### 10.1 Проверка текущей версии

```bash
docker compose exec mattermost \
  cat /mattermost/VERSION
```

### 10.2 Обновление образа

1. Создайте резервную копию (см. раздел 9)

2. Измените тег образа в `docker-compose.yml`:
   ```yaml
   image: mattermost/mattermost-team-edition:10.0
   ```

3. Потяните новый образ и перезапустите:
   ```bash
   docker compose pull mattermost
   docker compose up -d mattermost
   ```

4. Проверьте логи на наличие ошибок миграций:
   ```bash
   docker compose logs mattermost | tail -50
   ```

---

## 11. Устранение неполадок

### Mattermost не запускается — ошибка подключения к БД

```bash
# Проверить статус базы данных Mattermost
docker compose ps mattermost-postgres
docker compose logs mattermost-postgres

# Проверить строку подключения
docker compose exec mattermost \
  env | grep MM_SQL
```

### Адаптер не может подключиться к Mattermost

```bash
# Проверить доступность Mattermost из контейнера адаптера
docker compose exec mattermost-adapter \
  curl -v http://mattermost:8065/api/v4/system/ping

# Убедиться, что адаптер находится в обеих сетях
docker inspect $(docker compose \
  ps -q mattermost-adapter) | python3 -m json.tool | grep -A 5 '"Networks"'
```

### Бот не отвечает на сообщения

```bash
# 1. Проверить, что токен бота корректен
docker compose exec mattermost-adapter \
  sh -c 'curl -s -H "Authorization: Bearer $MATTERMOST_BOT_TOKEN" \
    http://mattermost:8065/api/v4/users/me | python3 -m json.tool'

# 2. Убедиться, что вебхук настроен правильно
# В Mattermost: Integrations → Outgoing Webhooks
# Callback URL должен быть: http://mattermost-adapter:8002/webhook

# 3. Следить за логами в реальном времени и отправить тестовое сообщение
docker compose logs -f mattermost-adapter bot
```

### Ошибка "Invalid webhook token" в логах адаптера

Убедитесь, что значение `MATTERMOST_WEBHOOK_SECRET` в `.env` совпадает с Token,
который показан в настройках исходящего вебхука (**Integrations** → **Outgoing Webhooks**
→ ваш вебхук → поле **Token**).

### Ошибка прав доступа к файлам Mattermost (permission denied)

Официальный образ Mattermost использует UID/GID 2000. Если volume был создан
с неправильными правами:

```bash
docker run --rm \
  -v mattermost-master_mattermost_data:/data \
  -v mattermost-master_mattermost_config:/config \
  -v mattermost-master_mattermost_logs:/logs \
  alpine sh -c "chown -R 2000:2000 /data /config /logs"
```

### Полный сброс Mattermost (удаление всех данных)

> **Внимание:** все данные Mattermost будут удалены безвозвратно.

```bash
docker compose stop mattermost mattermost-postgres mattermost-adapter
docker compose rm -f mattermost mattermost-postgres

docker volume rm \
  mattermost-master_mattermost_data \
  mattermost-master_mattermost_config \
  mattermost-master_mattermost_logs \
  mattermost-master_mattermost_plugins \
  mattermost-master_mattermost_client_plugins \
  mattermost-master_mattermost_bleve_indexes \
  mattermost-master_mattermost_postgres_data

# Запустить заново с чистого листа
docker compose up -d mattermost-postgres mattermost
```

### Просмотр всех логов

```bash
# Все сервисы сразу
docker compose logs -f

# Конкретный сервис
docker compose logs -f mattermost
docker compose logs -f mattermost-adapter
docker compose logs -f bot
```

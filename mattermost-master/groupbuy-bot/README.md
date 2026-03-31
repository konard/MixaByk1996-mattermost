# GroupBuy Bot

A multi-platform group purchasing bot with support for Telegram, WhatsApp, and WebSocket-based chat.

## Features

- **Multi-platform support**: Telegram, WebSocket (extensible to WhatsApp, VK)
- **User management**: Registration with 3 roles (Buyer, Organizer, Supplier)
- **Procurement system**: Create, join, and manage group purchases
- **Real-time chat**: WebSocket-based chat for each procurement
- **Payment integration**: YooKassa payment processing
- **Scalable architecture**: Microservices-based design

## Architecture

```
+-------------------+     +-------------------+
|   Telegram Bot    |     |   WebSocket Chat  |
+-------------------+     +-------------------+
         |                         |
         v                         v
+-------------------------------------------+
|           Message Router / Bot Service    |
+-------------------------------------------+
                    |
                    v
+-------------------------------------------+
|              Core API (Django)            |
|  - Users  - Procurements  - Payments      |
+-------------------------------------------+
         |                    |
         v                    v
+----------------+    +----------------+
|   PostgreSQL   |    |     Redis      |
+----------------+    +----------------+
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)
- YooKassa account (for payments)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd groupbuy-bot
```

2. Copy environment file and configure:
```bash
cp .env.example .env
# Edit .env with your settings
```

3. Start the services (migrations run automatically):
```bash
docker-compose up -d
```

Note: Database migrations are applied automatically when the core service starts.

5. Create admin user:
```bash
docker-compose exec core python manage.py createsuperuser
```

## Development

### Local Development Setup

1. Create virtual environments for each service:
```bash
# Core API
cd core && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Bot
cd ../bot && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

2. Start PostgreSQL and Redis:
```bash
docker-compose up -d postgres redis
```

3. Run Core API:
```bash
cd core
python manage.py migrate
python manage.py runserver
```

4. Run Bot (in another terminal):
```bash
cd bot
python main.py
```

### Running Tests

```bash
# Core API tests
cd core
pytest

# Bot tests
cd bot
pytest ../tests/test_bot_commands.py
```

## Production Deployment

### Single Server Deployment

Use the production Docker Compose file:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Two-Server Deployment

For high-load scenarios, the application supports a two-server architecture:
- **Server 1 (Chat)**: Handles real-time WebSocket connections
- **Server 2 (API/Bot)**: Handles business logic and data

On Server 1 (Chat):
```bash
docker-compose -f docker-compose.two-server.yml up -d websocket-server redis-chat nginx-chat
```

On Server 2 (API):
```bash
docker-compose -f docker-compose.two-server.yml up -d core bot telegram-adapter postgres redis-api nginx-api
```

Configure `CORE_API_URL` on Server 1 to point to Server 2's API endpoint.

### SSL Configuration

1. Place SSL certificates in `infrastructure/nginx/ssl/`
2. Update nginx configuration files to use HTTPS (uncomment SSL sections)

## Web Frontend

The application includes a Telegram-like web frontend accessible at the root URL (`/`).

Features:
- Responsive design matching Telegram's look and feel
- Real-time chat via WebSocket
- Personal cabinet for each role (Buyer, Organizer, Supplier)
- Procurement browsing with horizontal slider
- Dark/light theme support

## API Documentation

API documentation is available at `/api/docs/` when the server is running.

### Key Endpoints

#### Users
- `POST /api/users/` - Register user
- `GET /api/users/{id}/` - Get user details
- `GET /api/users/by_platform/` - Get user by platform

#### Procurements
- `GET /api/procurements/` - List procurements
- `POST /api/procurements/` - Create procurement
- `POST /api/procurements/{id}/join/` - Join procurement
- `GET /api/procurements/user/{user_id}/` - User's procurements

#### Payments
- `POST /api/payments/` - Create payment
- `GET /api/payments/{id}/status/` - Check payment status

#### Chat
- `GET /api/chat/messages/` - List messages
- `POST /api/chat/messages/` - Send message
- `WebSocket /ws/procurement/{id}/` - Real-time chat

## Bot Commands

### General
- `/start` - Start/register
- `/help` - Show help
- `/profile` - View profile
- `/balance` - Check balance

### Procurements
- `/procurements` - List active procurements
- `/my_procurements` - Your procurements
- `/create_procurement` - Create new (organizers only)

### Payments
- `/deposit` - Deposit to balance

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_TOKEN` | Telegram Bot API token |
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL user |
| `DB_PASSWORD` | PostgreSQL password |
| `DJANGO_SECRET_KEY` | Django secret key |
| `YOOKASSA_SHOP_ID` | YooKassa shop ID |
| `YOOKASSA_SECRET_KEY` | YooKassa secret key |
| `JWT_SECRET` | JWT secret for WebSocket auth |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License

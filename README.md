<div align="center">

# 🤖 Telegram E-Commerce Bot

**🌐 Choose language / Выберите язык:**
[🇺🇸 English](#english) • [🇷🇺 Русский](#russian)

</div>

---

<a id="english"></a>
## 🇺🇸 English

A professional, fully functional asynchronous Telegram bot designed for selling digital products (online courses, lectures, materials). Built with **Python 3.14** and **Aiogram 3**.

### 🚀 Key Features

*   **Clean Inline UI:** No clunky reply keyboards. All navigation is done via inline buttons with automatic chat cleanup (deleting previous bot messages) to keep the interface tidy.
*   **Multi-Payment Gateway Integration:**
    *   💳 **Platega API:** Ready for card/SBP payments via REST API and asynchronous Webhook handling. Includes a graceful fallback: if API keys are missing, the button remains active but shows a user-friendly "Payment temporarily unavailable" message.
    *   🪙 **CryptoBot (Crypto Pay):** Fully integrated using `aiosend` for crypto payments.
    *   💸 **Manual SBP:** A built-in moderation system for manual bank transfers with instant admin notifications and one-click approval.
*   **Referral System:** Users get a unique invite link. When a referred friend makes a purchase, the referrer automatically receives a 30% discount for their next buy.
*   **Admin Panel (FSM):** Add, edit, hide, or delete products. Broadcast messages (news or specific product announcements) to all users with delay handling to respect Telegram API limits.
*   **Smart Content Delivery:** The bot delivers private links to materials (e.g., Yandex/Google Drive) after a successful purchase.
*   **Async Webhook Server:** Built-in `aiohttp` server to listen for payment status callbacks from payment providers.

### 🛠️ Tech Stack
*   **Language:** Python 3.14
*   **Framework:** Aiogram 3 (Fully asynchronous)
*   **Database:** SQLite (via `aiosqlite` for async queries)
*   **Web Server:** `aiohttp` (for handling payment webhooks)
*   **Integrations:** `aiosend` (CryptoBot API)

### 📂 Architecture

```text
├── main.py                 # Entry point (polling + webhook server)
├── app/
│   ├── config.py           # Environment configuration
│   ├── database.py         # Async DB operations
│   ├── keyboards.py        # Inline keyboards and menus
│   ├── payments.py         # Payment gateway logic
│   ├── tracker.py          # Message cleanup utility
│   ├── webhook.py          # aiohttp server for callbacks
│   ├── main_state.py       # Global bot state for webhooks
│   └── handlers/
│       ├── user.py         # User commands & flows
│       ├── admin.py        # Admin FSM & broadcast
│       ├── crypto.py       # CryptoBot handlers
│       └── manual.py       # Manual SBP handlers
└── .env.example            # Environment variables template
```
⚙️ Quick Start
1. Clone the repository.

2. Install dependencies:

pip install -r requirements.txt

3. Rename .env.example to .env and fill in your credentials (Bot Token, Admin IDs, Payment Tokens).

4. Run the bot:

python main.py

<a id="russian"></a>

🇷🇺 Русский
Профессиональный, полностью функциональный асинхронный Telegram-бот для продажи цифровых товаров (онлайн-курсов, лекций, материалов). Написан на Python 3.14 и Aiogram 3.

🚀 Ключевые особенности
Чистый Inline-интерфейс: Никаких громоздких нижних панелей. Вся навигация через инлайн-кнопки с автоматической очисткой чата (удаление предыдущих сообщений бота) для поддержания аккуратного вида.

Интеграция множества платежных систем:

💳 Platega API: Готов к приему оплаты картами/СБП через REST API и асинхронные Webhook-уведомления. Включает защиту от сбоев: если API-ключи не заданы, кнопка остается активной, но показывает вежливое сообщение «Оплата временно недоступна».

🪙 CryptoBot (Crypto Pay): Полная интеграция через библиотеку aiosend для приема криптовалюты.

💸 Ручной СБП: Встроенная система модерации ручных переводов с мгновенными уведомлениями админу и подтверждением в один клик.

Реферальная система: Пользователи получают уникальную ссылку. Когда приглашенный друг совершает покупку, пригласивший автоматически получает скидку 30% на следующую покупку.

Админ-панель (FSM): Добавление, редактирование, скрытие и удаление товаров. Создание рассылок (новости или анонсы товаров) с задержками для соблюдения лимитов Telegram API.

Умная выдача контента: Бот выдает приватные ссылки на материалы (например, Яндекс/Google Диск) после успешной покупки.

Асинхронный Webhook-сервер: Встроенный сервер aiohttp для прослушивания статусов оплаты от платежных провайдеров.

🛠️ Технологии
Язык: Python 3.14

Фреймворк: Aiogram 3 (Полностью асинхронный)

База данных: SQLite (через aiosqlite для асинхронных запросов)

Веб-сервер: aiohttp (для обработки платежных вебхуков)

Интеграции: aiosend (CryptoBot API)

📂 Архитектура

├── main.py                 # Точка входа (polling + webhook сервер)
├── app/
│   ├── config.py           # Конфигурация окружения
│   ├── database.py         # Асинхронная работа с БД
│   ├── keyboards.py        # Инлайн-клавиатуры и меню
│   ├── payments.py         # Логика платежных шлюзов
│   ├── tracker.py          # Утилита очистки сообщений
│   ├── webhook.py          # aiohttp сервер для колбеков
│   ├── main_state.py       # Глобальное состояние бота для вебхуков
│   └── handlers/
│       ├── user.py         # Команды и сценарии пользователей
│       ├── admin.py        # FSM и рассылки админа
│       ├── crypto.py       # Обработчики CryptoBot
│       └── manual.py       # Обработчики ручного СБП
└── .env.example            # Шаблон переменных окружения

⚙️ Быстрый старт
1. Склонируйте репозиторий.

2. Установите зависимости:

pip install -r requirements.txt

3. Переименуйте .env.example в .env и заполните своими данными (Токен бота, ID админов, Токены платежных систем).

4. Запустите бота:

python main.py


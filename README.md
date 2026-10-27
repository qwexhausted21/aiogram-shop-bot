# 🤖 Telegram E-Commerce Bot (Course Selling)

A fully functional, asynchronous Telegram bot designed for selling digital products (online courses, lectures, materials). Built with **Python 3.14** and **Aiogram 3**.

## 🚀 Key Features

*   **User-Friendly Inline UI:** No clunky reply keyboards. All navigation is done via clean inline buttons with automatic message cleanup to keep the chat tidy.
*   **Multi-Payment Gateway Integration:**
    *   💳 **Platega API:** Ready for card/SBP payments via REST API and asynchronous Webhook handling.
    *   🪙 **CryptoBot (Crypto Pay):** Fully integrated using `aiosend` for crypto payments.
    *   💸 **Manual SBP:** A built-in moderation system for manual bank transfers with instant admin notifications.
*   **Referral System:** Users get a unique link. When a referred friend makes a purchase, the referrer receives a 30% discount for their next buy.
*   **Admin Panel (FSM):** Add, edit, hide, or delete products. Broadcast messages (news or specific product announcements) to all users.
*   **Smart Content Delivery:** The bot delivers private links to materials (e.g., Yandex/Google Drive). *Previously supported automated one-time Telegram channel invites.*
*   **Async Webhook Server:** Built-in `aiohttp` server to listen for payment status callbacks from payment providers.

## 🛠️ Tech Stack

*   **Language:** Python 3.14
*   **Framework:** Aiogram 3 (Fully asynchronous)
*   **Database:** SQLite (via `aiosqlite` for async queries)
*   **Web Server:** `aiohttp` (for handling payment webhooks)
*   **Integrations:** `aiosend` (CryptoBot API)

## 📂 Architecture

The project follows a modular structure for maintainability:

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
 Quick Start
Clone the repository.

Install dependencies:
pip install -r requirements.txt

Rename .env.example to .env and fill in your credentials (Bot Token, Admin IDs, Payment Tokens).

Run the bot:
python main.py

📌 Note on Payment Integrations
CryptoBot works out of the box (requires token from @CryptoBot).

Platega requires a valid MERCHANT_ID and SECRET, as well as a public HTTPS webhook URL (e.g., deployed on a VPS). The bot includes a graceful fallback: if API keys are missing, the button remains clickable but shows a user-friendly "Payment temporarily unavailable" message.
# NancyAI v2.1🤖

A Telegram bot that:
- 💬 Acts as a chat assistant powered by Llama 3.1
- ✨ Rewrites media captions with smart hyperlinks
- 🎬 Fetches movie/series details (OMDb) and appends poster link
- 📢 Sends a copy of every processed message to a log channel
- 🌐 Runs as an aiohttp webhook server (port 8000)
- 📄 Serves live logs at “/” (shows BOT_LOG_FILE)

## Requirements ✅
- Python ≥ 3.9 (for local dev) or Docker
- Telegram Bot Token
- OMDb API key
- GROQ API key

## Environment variables 🔐
Set via .env or .env.dev (both auto-loaded; .env.dev overrides):
- BOT_TOKEN: Telegram bot token
- GROQ_API_KEY: Your Groq key (optional)
- OMDB_API_KEY: OMDb API key
- LOG_CHANNEL_ID: Channel ID (e.g., -1001234567890) or @username to receive log copies
- BOT_LOG_FILE: Path to log file (default: bot.log)
- WEBHOOK_HOST: Public HTTPS URL Telegram can reach (e.g., https://your-ngrok-subdomain.ngrok-free.app)

Never commit real secrets. Use placeholders in VCS.

## Quick start (Poetry) 📦

1) Install Poetry 2.1.4:
```bash
curl -sSL https://install.python-poetry.org | python3 - --version 2.1.4
```

2) Add Poetry to PATH and persist it:
```bash
export PATH="/home/user/.local/bin:$PATH"
# You should add this line to your shell's configuration file (e.g., ~/.bashrc)
echo 'export PATH="/home/user/.local/bin:$PATH"' >> ~/.bashrc
```

3) Verify installation:
```bash
poetry --version
# Expect: Poetry (version 2.1.4)
```

4) Install dependencies:
```bash
poetry install
```

5) Run the bot:
```bash
# If a console script “nancy” exists:
poetry run nancy

# Otherwise:
poetry run python -m nancyai.bot
```

## Quick start (Docker) 🐳
Build:
```bash
docker build -t nancyai:latest .
```

Run:
```bash
docker run --rm -p 8000:8000 \
  -e BOT_TOKEN=YOUR_BOT_TOKEN \
  -e OMDB_API_KEY=YOUR_OMDB_KEY \
  -e GROQ_API_KEY=YOUR_GROQ_KEY \
  -e LOG_CHANNEL_ID=-1001234567890 \
  -e WEBHOOK_HOST=https://your-public-host.tld \
  -e BOT_LOG_FILE=/app/bot.log \
  nancyai:latest
```

Notes:
- The server listens on 0.0.0.0:8000
- Visit http://localhost:8000/ to view the live bot.log (no cache)

## Webhook setup 🌍
- Set WEBHOOK_HOST to your public HTTPS URL (ngrok, cloud, etc.)
- The bot registers the webhook on startup at: {WEBHOOK_HOST}/webhook
- Example (ngrok):
  - ngrok http 8000
  - Use the HTTPS URL from ngrok as WEBHOOK_HOST

## Commands 📜
- /start — greeting and basic usage
- /help — help
- /status — health/status
- /clear — clear pending state
- /log — link or file for the current log

## Troubleshooting 🛠️
- Root path shows “Error loading log.”:
  - Ensure BOT_LOG_FILE is writable and exists; the bot handles creation/rotation
- No Telegram updates:
  - Verify WEBHOOK_HOST is correct and publicly reachable over HTTPS
- OMDb metadata missing:
  - Check OMDB_API_KEY validity and rate limits
- Log channel copy not delivered:
  - Ensure the bot is in the channel (admin/member)
  - Use a numeric channel ID (-100…) or @channel username

## Easy deploy 📨
[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?name=nancyai-unified&type=git&repository=JeevabharathiRK%2FNancyAI-unified&branch=main&builder=dockerfile&instance_type=free&regions=was&instances_min=0&autoscaling_sleep_idle_delay=3600&env%5BBOT_LOG_FILE%5D=%7B%7B+secret.BOT_LOG_FILE+%7D%7D&env%5BBOT_TOKEN%5D=%7B%7B+secret.BOT_TOKEN+%7D%7D&env%5BGROQ_API_KEY%5D=%7B%7B+secret.GROQ_API_KEY+%7D%7D&env%5BLOG_CHANNEL_ID%5D=-1001153843878&env%5BOMDB_API_KEY%5D=%7B%7B+secret.OMDB_API_KEY+%7D%7D&env%5BWEBHOOK_HOST%5D=%7B%7B+KOYEB_PUBLIC_DOMAIN+%7D%7D)

## Contributing 🤝
Issues and PRs are welcome. Feel free to collaborate, improve features, and suggest ideas!

Made with ❤️ by [JeevabharathiRK](https://github.com/JeevabharathiRK)

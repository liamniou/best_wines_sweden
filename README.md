This Telegram bot checks Vivino toplists defined in `TOPLIST_URLS` variable and tries to find the wines in stock of Swedish alcohol retailer Systembolaget.

## Prerequisites
- create bot user via [BotFather and get API token](https://core.telegram.org/bots#3-how-do-i-create-a-bot);
- install Python3 and pip for it:
> apt update && apt install python3 && apt install -y python3-pip
- install Python Modules:
> python3 -m pip install -r app/requirements.txt
- install Chromium dependency libraries that are required for Pyppeteer:
> apt install -y gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils wget

## Usage
> TELEGRAM_BOT_TOKEN=PUT_TOKEN_HERE TELEGRAM_CHAT_ID=PUT_CHAT_ID_HERE CHROME_TIMEOUT=10000 python3 app/best_wines_sweden.py

This Telegram bot checks Vivino toplists defined in `TOPLIST_URLS` variable and tries to find the wines in stock of Swedish alcohol retailer Systembolaget.

## Prerequisites
- create bot user via [BotFather and get API token](https://core.telegram.org/bots#3-how-do-i-create-a-bot);
- create Telegraph account (you can use function `create_account` from `app/telegraph_functions.py`);
- install Docker.

## Usage
# Build Docker image
![build_and_publish_docker_image](https://github.com/liamniou/best_wines_sweden/actions/workflows/docker-publish.yml/badge.svg)
> docker build -f Dockerfile.arm -t best_wines_sweden .
# Start Docker container
> docker run -dit \
  --name=best_wines \
  --env=TELEGRAM_BOT_TOKEN=PUT_BOT_USER_TOKEN_HERE \
  --env=TELEGRAM_CHAT_ID=PUT_TELEGRAM_CHAT_ID_HERE \
  --env=TELEGRAPH_TOKEN=PUT_TELEGRAPH_TOKEN_HERE \
  best_wines_sweden

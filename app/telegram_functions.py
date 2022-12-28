import httpx
import os
from telegraph import Telegraph


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))


def create_account(short_name):
    telegraph = Telegraph(access_token=os.getenv("TELEGRAPH_TOKEN"))
    r = telegraph.create_account(short_name=short_name)
    return r


def upload_image_to_telegraph(image_url):
    image_file_name = image_url.split("/")[-1]
    local_file_path = f"/tmp/{image_file_name}"
    extension = local_file_path.split(",")[-1]
    with open(local_file_path, "wb") as f:
        with httpx.stream("GET", image_url) as r:
            for chunk in r.iter_bytes():
                f.write(chunk)
    with open(local_file_path, "rb") as f:
        r = httpx.post(
            "https://telegra.ph/upload",
            files={"file": ("file", f, f"image/{extension}")},
        )
        return r.json()[0]["src"]


def create_telegraph_page(title, html_content):
    telegraph = Telegraph(access_token=os.getenv("TELEGRAPH_TOKEN"))
    r = telegraph.create_page(title, html_content=html_content)
    return r


def normalize_string(string):
    return (
        str(string)
        .replace(".", "\\.")
        .replace("-", "\\-")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def send_telegram_message(message_text):
    with httpx.Client() as client:
        data_dict = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": normalize_string(message_text),
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": False,
        }
        r = client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data=data_dict,
        )
        return r.text

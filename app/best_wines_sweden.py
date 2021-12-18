import httpx
import logging as log
import os
import urllib.parse
from asyncio_systembolaget_search import get_systembolaget_info_about_drink
from bs4 import BeautifulSoup
from difflib import SequenceMatcher


TOPLIST_URLS = [
    "https://www.vivino.com/toplists/best-wines-under-100-kr-right-now-sweden",
    "https://www.vivino.com/toplists/best-wines-between-100-kr-and-200-kr-right-now-sweden",
]
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

log.basicConfig(level=log.INFO, format="%(asctime)s %(name)s %(levelname)s:%(message)s")


def how_similar(string_a, string_b):
    return SequenceMatcher(None, string_a, string_b).ratio()


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
            "text": message_text,
            "parse_mode": "MarkdownV2",
            "disable_web_page_preview": True,
        }
        r = client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data=data_dict,
        )
        return r.text


def parse_vivino_toplist(toplist_url):
    resulting_dict = {}

    with httpx.Client() as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"
        }
        r = client.get(toplist_url, headers=headers)

        soup = BeautifulSoup(r.text, "html.parser")
        all_results = soup.find_all(class_="card card-lg")

        for res in all_results:
            rating = res.select(".average__number")[0].text.strip()
            name = res.select(".bold")[1].text.strip()
            resulting_dict[name] = {
                "rating": rating,
            }
    return resulting_dict


def transform_wine_style_to_emoji(wine_style):
    if wine_style == "Rött":
        return "🍷"
    elif wine_style == "Vitt":
        return "🥂"
    elif wine_style == "Mousserande":
        return "🍾"
    else:
        return wine_style


def get_systembolaget_wine_data(name):
    log.info(f"Checking {name}")
    resulting_message = None
    systembolaget_info = get_systembolaget_info_about_drink(urllib.parse.quote(name))
    if systembolaget_info:
        log.info(systembolaget_info)
        for sb_name, value in systembolaget_info.items():
            match_rating = round(how_similar(name, sb_name) * 100, 1)
            if match_rating > 70:
                wine_style = transform_wine_style_to_emoji(
                    systembolaget_info[sb_name]["drink_tags"][1]
                )
                grape_variety = systembolaget_info[sb_name]["drink_taste"][0]
                bottle_price = systembolaget_info[sb_name]["bottle_price"][0].replace(
                    ":-", "kr"
                )
                bottle_volume = (
                    int(
                        systembolaget_info[sb_name]["bottle_metadata"][1].replace(
                            " ml", ""
                        )
                    )
                    / 1000
                )
                sb_link = systembolaget_info[sb_name]["systembolaget_link"]
                resulting_message = [
                    wine_style,
                    grape_variety,
                    sb_name,
                    sb_link,
                    bottle_volume,
                    bottle_price,
                ]
            else:
                log.info(
                    f"Name match rating is too low between {name} and {sb_name}: {match_rating}%"
                )
    log.info(resulting_message)
    return resulting_message


def create_tg_messages_per_grape_style_from_toplist(toplist_url):
    messages_to_send = {}

    wine_names_from_the_list = parse_vivino_toplist(toplist_url)

    for wine_name, wine_rating in wine_names_from_the_list.items():
        wine = get_systembolaget_wine_data(wine_name)
        if wine:
            wine = [normalize_string(item) for item in wine]
            formatted_wine_entry = normalize_string(
                f"\n*{wine_rating['rating']} ⭐ {wine_name}*"
            )
            formatted_wine_entry += (
                f" {wine[0]} {wine[1]}\n[{wine[2]}]({wine[3]}) {wine[4]}L {wine[5]}\n"
            )
            if wine[0] in messages_to_send:
                messages_to_send[wine[0]] += formatted_wine_entry
            else:
                toplist_title = (
                    toplist_url.split("/")[-1]
                    .replace("sweden", "🇸🇪")
                    .replace("-", " ")
                    .replace(" right now", "")
                    .replace("best", f"🔝 {wine[0]}")
                )
                messages_to_send[wine[0]] = f"\n{toplist_title}\n{formatted_wine_entry}"

    return messages_to_send


if __name__ == "__main__":
    for toplist_url in TOPLIST_URLS:
        log.warning(f"Processing {toplist_url}")
        messages = create_tg_messages_per_grape_style_from_toplist(toplist_url)
        for grape_style, message in messages.items():
            log.warning(message)
            log.warning(send_telegram_message(message))

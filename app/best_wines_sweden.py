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
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

log.basicConfig(level=log.INFO, format='%(asctime)s %(name)s %(levelname)s:%(message)s')


def how_similar(string_a, string_b):
    return SequenceMatcher(None, string_a, string_b).ratio()


def send_telegram_message(message):
    with httpx.Client() as client:
        data_dict = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
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


def create_message_to_send_for_wine_from_list(name):
    log.info(f"Checking {name}")
    resulting_messages = None
    systembolaget_info = get_systembolaget_info_about_drink(urllib.parse.quote(name))
    if systembolaget_info:
        log.info(systembolaget_info)
        resulting_messages = {}
        for key, value in systembolaget_info.items():
            match_rating = round(how_similar(name, key) * 100, 1)
            if match_rating > 70:
                wine_style = transform_wine_style_to_emoji(
                    systembolaget_info[key]["drink_tags"][1]
                )
                grape_variety = systembolaget_info[key]["drink_taste"][0]
                bottle_price = systembolaget_info[key]["bottle_price"][0].replace(
                    ":-", "SEK"
                )
                bottle_volume = (
                    int(
                        systembolaget_info[key]["bottle_metadata"][1].replace(" ml", "")
                    )
                    / 1000
                )
                sb_link = systembolaget_info[key]["systembolaget_link"]
                if wine_style in resulting_messages:
                    resulting_messages[wine_style] += f" {wine_style} {grape_variety}\n[{key}]({sb_link}) {bottle_volume}L {bottle_price}\n"
                else:
                    resulting_messages[wine_style] = f" {wine_style} {grape_variety}\n[{key}]({sb_link}) {bottle_volume}L {bottle_price}\n"
            else:
                log.warning(
                    f"Name match rating is too low between {name} and {key}: {match_rating}%"
                )
    log.info(resulting_messages)
    return resulting_messages


def create_tg_messages_from_vivino_sweden_toplist(toplist_url):
    list_of_messages_to_send = []
    toplist_title = (
        toplist_url.split("/")[-1]
        .replace("sweden", "🇸🇪")
        .replace("-", " ")
        .replace("best", "🔝")
    )
    message_to_send = f"\n{toplist_title.capitalize()}\n"

    wine_names_from_the_list = parse_vivino_toplist(toplist_url)[:5]

    for wine_name, wine_rating in wine_names_from_the_list.items():
        found_wine_message = create_message_to_send_for_wine_from_list(wine_name)
        if found_wine_message:
            message_to_send += f"\n*{wine_rating['rating']} ⭐ {wine_name}*"
            message_to_send += found_wine_message
    list_of_messages_to_send.append(message_to_send)
    return list_of_messages_to_send


if __name__ == "__main__":
    for toplist in TOPLIST_URLS:
        messages = create_tg_messages_from_vivino_sweden_toplist(toplist)
        for message in messages:
            log.info(message)
            send_telegram_message(message.replace(".", "\\.").replace("-", "\\-"))

import httpx
import logging as log
import os
import urllib.parse
from bs4 import BeautifulSoup
from dataclasses import dataclass
from difflib import SequenceMatcher
from telegraph_functions import create_telegraph_page, upload_image_to_telegraph
from with_browser import find_in_systembolaget


TOPLIST_URLS = [
    "https://www.vivino.com/toplists/best-wines-under-100-kr-right-now-sweden",
    "https://www.vivino.com/toplists/best-wines-between-100-kr-and-200-kr-right-now-sweden",
]
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))

log.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO").upper(), format="%(asctime)s %(name)s %(levelname)s:%(message)s"
)


def how_similar(string_a, string_b):
    return SequenceMatcher(None, string_a, string_b).ratio()


def normalize_string(string):
    return str(string).replace(".", "\\.").replace("-", "\\-").replace("(", "\\(").replace(")", "\\)")


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


def parse_vivino_toplist(toplist_url):
    resulting_dict = {}

    with httpx.Client() as client:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"}
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


def wine_style_to_emoji(wine_style):
    if wine_style == "Rött":
        return "🍷"
    elif wine_style == "Vitt":
        return "🥂"
    elif wine_style == "Mousserande":
        return "🍾"
    else:
        return wine_style


def get_systembolaget_wine_data(name):
    @dataclass
    class WineData:
        sb_name: str
        sb_link: str
        style: str
        grapes: str
        volume: int
        price: int
        image: str

    log.info(f"Checking {name}")
    result = None
    sb_info = find_in_systembolaget(urllib.parse.quote(name))
    if sb_info:
        log.info(sb_info)
        for sb_name, value in sb_info.items():
            match_rating = round(
                how_similar("".join(e for e in name if e.isalpha()), "".join(e for e in sb_name if e.isalpha())) * 100,
                1,
            )
            if match_rating > 70:
                result = WineData(
                    sb_name,
                    sb_info[sb_name]["systembolaget_link"],
                    wine_style_to_emoji(sb_info[sb_name]["drink_metadata"]["product"]["categoryLevel2"]),
                    sb_info[sb_name]["drink_metadata"]["product"]["grapes"],
                    sb_info[sb_name]["drink_metadata"]["product"]["volume"],
                    sb_info[sb_name]["drink_metadata"]["product"]["priceInclVat"],
                    sb_info[sb_name]["drink_metadata"]["product"]["images"][0]["imageUrl"] + "_100.png",
                )
            else:
                log.info(f"Name match rating is too low between {name} and {sb_name}: {match_rating}%")
    log.info(f"Matched results: {result}")
    return result


def create_pages_per_grape_style_from_toplist(toplist_url):
    pages = {}

    wine_names_from_the_list = parse_vivino_toplist(toplist_url)

    for wine_name, wine_rating in wine_names_from_the_list.items():
        wine = get_systembolaget_wine_data(wine_name)
        if wine:
            wine_html_content = f"<h4>{wine_rating['rating']} ⭐ {wine_name}</h4>"
            wine_html_content += f"<img src='{upload_image_to_telegraph(wine.image)}'><br>"
            wine_html_content += (
                f"<p><a href='{wine.sb_link}'>{wine.sb_name}</a> ({wine.grapes}) "
                f"<i><b>{wine.volume / 1000} L {wine.price} SEK</b></i></p>"
            )
            if wine.style in pages:
                pages[wine.style]["html"] += wine_html_content
            else:
                toplist_title = (
                    toplist_url.split("/")[-1]
                    .replace("sweden", "🇸🇪")
                    .replace("-", " ")
                    .replace(" right now", "")
                    .replace("best", f"🔝 {wine.style}")
                )
                pages[wine.style] = {"title": toplist_title, "html": wine_html_content}

    return pages


if __name__ == "__main__":
    for toplist_url in TOPLIST_URLS:
        log.warning(f"Processing {toplist_url}")
        pages = create_pages_per_grape_style_from_toplist(toplist_url)
        for grape_style, page in pages.items():
            log.warning(page)
            telegraph_page = create_telegraph_page(page["title"], page["html"])
            log.warning(telegraph_page)
            log.warning(send_telegram_message(telegraph_page["url"]))

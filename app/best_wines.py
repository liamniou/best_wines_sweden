import httpx
import re
from selectolax.parser import HTMLParser
from dataclasses import dataclass
from difflib import SequenceMatcher
from playwright.sync_api import sync_playwright
from retrying import retry
from telegram_functions import create_telegraph_page, send_telegram_message


TOPLIST_URLS = [
    "https://www.vivino.com/toplists/best-wines-under-100-kr-right-now-sweden",
    "https://www.vivino.com/toplists/best-wines-between-100-kr-and-200-kr-right-now-sweden",
    "https://www.vivino.com/toplists/top-25-australian-shiraz-wines-sweden-right-now-sweden",
    "https://www.vivino.com/toplists/top-25-south-african-syrah-wines-sweden-right-now-sweden",
]


@dataclass
class VivinoItem:
    name: str
    rating: int


@dataclass
class SbSearchResult:
    name: str
    href: str
    price: str
    rating: str
    style: str


def parse_vivino_toplist(toplist_url):
    vivino_items = []

    with httpx.Client() as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"
        }
        r = client.get(toplist_url, headers=headers)
        html = HTMLParser(r.text)
        for item in html.css("div.card.card-lg"):
            vivion_item = VivinoItem(
                name=item.css_first("span.bold").text().strip(),
                rating=item.css_first("div.text-inline-block.light.average__number")
                .text()
                .strip(),
            )
            vivino_items.append(vivion_item)
    return vivino_items


def retry_if_result_none(result):
    """Return True if we should retry (in this case when result is None), False otherwise"""
    return result is None


def wine_style_to_emoji(wine_style):
    if "Rött" in wine_style:
        return "🍷"
    if "Vitt" in wine_style:
        return "🥂"
    if "Mousserande" in wine_style:
        return "🍾"
    return wine_style


@retry(
    retry_on_result=retry_if_result_none, wait_fixed=10000, stop_max_attempt_number=5
)
def iteratively_search_sb(vivino_wine):
    try:
        search_results = []
        with sync_playwright() as p:
            # Launch browser
            browser = p.firefox.launch(headless=True, slow_mo=1000)
            page = browser.new_page()
            page.goto("https://www.systembolaget.se")
            # Accept age restriction
            over_20_link = page.get_by_role("link", name="Jag har fyllt 20 år")
            over_20_link.click()
            # Accept cookies
            accept_cookies = page.get_by_role(
                "button", name="Slå på och acceptera alla kakor"
            )
            accept_cookies.click()

            # Split search_sting by space and iteratively remove last piece from the string
            search_string = vivino_wine.name
            split_name = search_string.split(" ")
            while len(split_name) > 0:
                joined_name = " ".join(split_name)

                print(f"Looking for {joined_name}")
                page.goto(
                    f"https://www.systembolaget.se/sortiment/?textQuery={joined_name}"
                    "&categoryLevel1=Vin&assortmentText=Fast%20sortiment&volumeFrom=750&packaging=Flaska"
                )
                page.is_visible("div.css-1ad0061.e17wolzc0")
                html = page.inner_html("div.css-1ad0061.e17wolzc0")
                parsed_html = HTMLParser(html)

                piles_with_items = parsed_html.css("a.css-1lc3wed.enuzix00")
                print(f"Found {len(piles_with_items)} piles")
                for item in piles_with_items:
                    wine_name = item.css_first("p.css-54mqg2.e3wog7r0").text().strip()
                    try:
                        wine_additional_name = (
                            item.css_first("p.css-18wuxp4.e3wog7r0").text().strip()
                        )
                    except:
                        wine_additional_name = ""
                    wine_final_name = f"{wine_name} {wine_additional_name}".strip()
                    if calculate_match_rating(search_string, wine_final_name) > 70:
                        wine_href = item.css_first("a.css-1lc3wed.enuzix00").attributes[
                            "href"
                        ]
                        wine_price = (
                            item.css_first("p.css-tny168.enp2lf70").text().strip()
                        )
                        wine_style = (
                            item.css_first("p.css-utx0um.enp2lf70").text().strip()
                        )
                        search_results.append(
                            SbSearchResult(
                                name=wine_final_name,
                                href=wine_href,
                                price=wine_price,
                                style=wine_style_to_emoji(wine_style),
                                rating=vivino_wine.rating,
                            )
                        )
                        print(f"search_results: {search_results}")
                    else:
                        print(f"Match rating for {wine_final_name} was too low")
                if search_results:
                    return search_results
                else:
                    split_name.pop()
        return search_results
    except Exception as e:
        print(f"Something happened...\n{e}")
        return None


def how_similar(string_a, string_b):
    return SequenceMatcher(None, string_a, string_b).ratio()


def calculate_match_rating(string_a, string_b):
    expr = re.compile(
        "20\d{2}"
    )  # Remove years from titles during the comparision. Match 20**
    match_rating = round(
        how_similar(
            re.sub(expr, "", string_a),
            re.sub(expr, "", string_b),
        )
        * 100,
        1,
    )
    return match_rating


def generate_html_for_list(list_url, sb_search_results):
    html = []
    title = (
        list_url.split("/")[-1]
        .replace("sweden", "🇸🇪")
        .replace("-", " ")
        .replace(" right now", "")
    )
    for item in sb_search_results:
        html.append(
            f"<p>{item.rating} ⭐ {item.style} <a href='http://systembolaget.se{item.href}'>{item.name}</a> {item.price}</p>"
        )
    return title, "".join(html)


def main():
    all_sb_search_results = []
    for list_url in TOPLIST_URLS:
        sb_search_results = []
        vivino_wines = parse_vivino_toplist(list_url)
        for vivino_wine in vivino_wines:
            print(f"{vivino_wine}")
            result = iteratively_search_sb(vivino_wine)
            if result:
                sb_search_results.extend(result)
            else:
                print(f"Nothing found for {vivino_wine}")
        print(sb_search_results)
        all_sb_search_results.extend(sb_search_results)
        print(sb_search_results)
        title, html = generate_html_for_list(list_url, sb_search_results)
        print(f"{title}: {html}")
        telegraph_page = create_telegraph_page(title, html)
        print(telegraph_page)
        send_telegram_message(telegraph_page["url"])
    print(all_sb_search_results)


if __name__ == "__main__":
    main()

# telegraph_page = create_telegraph_page("best wines between 100 kr and 200 kr 🇸🇪", "<p>4,2 ⭐ 🍷 <a href='http://systembolaget.se/produkt/vin/zenato-1238501/'>Zenato Valpolicella Classico Superiore, 2019</a> 139:-</p><p>4,1 ⭐ 🍷 <a href='http://systembolaget.se/produkt/vin/doppio-passo-320408/'>Doppio Passo Primitivo, 2021</a> 269:-</p><p>4,1 ⭐ 🍷 <a href='http://systembolaget.se/produkt/vin/doppio-passo-320401/'>Doppio Passo Organic Primitivo, 2020</a> 99:-</p><p>4,0 ⭐ 🍷 <a href='http://systembolaget.se/produkt/vin/breadbutter-7667101/'>Bread&Butter Pinot Noir, 2020</a> 169:-</p><p>4,0 ⭐ 🍷 <a href='http://systembolaget.se/produkt/vin/garzn-321001/'>Garzón Reserva Tannat, 2020</a> 149:-</p><p>4,0 ⭐ 🍷 <a href='http://systembolaget.se/produkt/vin/catena-7243901/'>Catena Cabernet Sauvignon, 2019</a> 139:-</p>")
# print(telegraph_page)
# send_telegram_message(telegraph_page["url"])

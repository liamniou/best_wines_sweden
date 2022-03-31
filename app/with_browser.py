import json
import logging as log
import os
import httpx
from bs4 import BeautifulSoup
from retrying import retry
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from time import sleep


chrome_options = Options()
chrome_options.add_argument("--disable-extensions")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")  # linux only
chrome_options.add_argument("--headless")
ACTION_PAUSE = int(os.getenv("ACTION_PAUSE", 3))


def retry_if_result_none(result):
    """Return True if we should retry (in this case when result is None), False otherwise"""
    return result is None


def start_browser_accept_cookies():
    browser = webdriver.Chrome(options=chrome_options)
    browser.get("https://www.systembolaget.se")

    sleep(ACTION_PAUSE)

    over_20_button_selector = (
        "body > div:nth-child(5) > div > div > div > div > section > div > div >" " div.css-17qgtxi > button"
    )
    over_20_button = browser.find_element_by_css_selector(over_20_button_selector)
    over_20_button.click()

    cookies_button_selector = (
        "body > div:nth-child(5) > div > div > div > div > div > div.css-1fvhj4g >"
        " div.css-i0tesz > button.css-1sa6t7h.epc1dj70"
    )
    cookies_button = browser.find_element_by_css_selector(cookies_button_selector)
    cookies_button.click()

    return browser


def open_page_find_element(browser, url, css_selector):
    browser.get(url)
    sleep(ACTION_PAUSE)
    element = browser.find_element_by_css_selector(css_selector)
    return element


def perform_ladder_search(browser, query_text):
    """
    If search with textQuery="19%20Crimes%20Red%20Blend" returns nothing (open_page_wait_selector() reaches timeout),
    Repeat search with textQuery="19%20Crimes%20Red".
    If results is still the same, repeat with textQuery="19%20Crimes" and etc. unless there is only one word left.
    """
    try:
        resulting_dict = {"results": None, "new_search_query": None}
        log.info(f"Looking for {query_text}")
        url = (
            f"https://www.systembolaget.se/sok/?textQuery={query_text}"
            f"&categoryLevel1=Vin&assortmentText=Fast%20sortiment&volumeFrom=750&packaging=Flaska"
        )
        results = open_page_find_element(browser, url, ".css-fmawtr") # .css-fmawtr - class of <a> tag in search results
        log.info(f"Something found for {query_text}: {results}")
        resulting_dict["results"] = url
        return resulting_dict
    except:
        log.info(f"Failed to find anything for {query_text}")
        split_query_text = query_text.split("%20")
        if len(split_query_text) > 1:
            sliced_query_text = split_query_text[:-1]
            new_query_text = "%20".join(sliced_query_text)
            log.info(f"Try again with {new_query_text}")
            resulting_dict["new_search_query"] = new_query_text
        return resulting_dict


@retry(retry_on_result=retry_if_result_none, wait_fixed=10000, stop_max_attempt_number=5)
def find_in_systembolaget(search_text):
    try:
        search_item_with_metadata = {}
        browser = start_browser_accept_cookies()

        search_page_url_with_results = None
        while search_text is not None:
            ladder_search_result = perform_ladder_search(browser, search_text)
            search_page_url_with_results = ladder_search_result["results"]
            search_text = ladder_search_result["new_search_query"]

        if search_page_url_with_results:
            print(search_page_url_with_results)
            browser.get(search_page_url_with_results)
            href_items = browser.find_elements_by_css_selector(".css-fmawtr") # Class of <a> element
            for item in href_items:
                href = item.get_attribute("href")
                with httpx.Client() as client:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:66.0) Gecko/20100101 Firefox/66.0"
                    }
                    r = client.get(href, headers=headers)
                    soup = BeautifulSoup(r.text, "html.parser")
                    drink_metadata = json.loads(
                        soup.find(attrs={"data-react-component": "ProductDetailPageContainer"})["data-props"]
                    )

                    drink_name = drink_metadata["product"]["productNameBold"]
                    drink_sub_name = drink_metadata["product"]["productNameThin"]

                    search_item_with_metadata[f"{drink_name} {drink_sub_name or ''}"] = {
                        "systembolaget_link": href,
                        "drink_metadata": drink_metadata,
                    }
        return search_item_with_metadata
    except:
        return None
    finally:
        browser.quit()

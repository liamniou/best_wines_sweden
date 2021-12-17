import asyncio
import os
import logging as log

from pyppeteer import launch


TIMEOUT = int(os.getenv("CHROME_TIMEOUT", 3000))


async def start_browser_accept_cookies():
    browser = await launch(
        headless=True,
        args=["--no-sandbox",
          "--single-process",
          "--disable-dev-shm-usage",
          "--disable-gpu",
          "--no-zygote"
        ]
    )

    starting_page = await browser.newPage()
    await starting_page.goto("https://www.systembolaget.se", timeout=TIMEOUT)

    over_20_button = (
        "body > div:nth-child(5) > div > div > div > div > section > div > div >"
        " div.css-17qgtxi > button"
    )
    await starting_page.click(over_20_button)

    accept_cookies_button = (
        "body > div:nth-child(5) > div > div > div > div > div > div.css-1fvhj4g >"
        " div.css-i0tesz > button.css-1sa6t7h.epc1dj70"
    )
    await starting_page.waitForSelector(accept_cookies_button)
    await starting_page.click(accept_cookies_button)

    return browser


async def open_page_wait_selector(browser, page_url, selector_query):
    page = await browser.newPage()
    await page.goto(page_url, timeout=TIMEOUT)
    await page.waitForSelector(selector_query, {"timeout": TIMEOUT})
    return page


async def get_list_of_parsed_values_with_evaluate(
    page_object, selector_query, evaluate_function
):
    resulting_list = []
    queried_elements = await page_object.querySelectorAll(selector_query)
    for element in queried_elements:
        parsed_item = await page_object.evaluate(evaluate_function, element)
        resulting_list.append(parsed_item)
    return resulting_list


async def perform_ladder_search(browser, query_text):
    """
    If search with textQuery="19%20Crimes%20Red%20Blend" returns nothing (open_page_wait_selector timeouts),
    Repeat search with textQuery="19%20Crimes%20Red".
    If results is still the same, repeat with textQuery="19%20Crimes" and etc. unless there is only one word left.
    """
    try:
        resulting_dict = {"search_page_with_results": None, "new_search_query": None}
        log.info(f"Looking for {query_text}")
        url = (
            f"https://www.systembolaget.se/sok/?textQuery={query_text}"
            f"&categoryLevel1=Vin&assortmentText=Fast%20sortiment&volumeFrom=750&packaging=Flaska"
        )
        search_page_with_results = await open_page_wait_selector(
            browser, url, ".css-1n00zeq"
        )
        log.info(f"Something found for {query_text}: {search_page_with_results}")
        resulting_dict["search_page_with_results"] = search_page_with_results
        return resulting_dict
    except:
        log.warning(f"Failed to find anything for {query_text}")
        split_query_text = query_text.split("%20")
        if len(split_query_text) > 1:
            sliced_query_text = split_query_text[:-1]
            new_query_text = "%20".join(sliced_query_text)
            log.warning(f"Try again with {new_query_text}")
            resulting_dict["new_search_query"] = new_query_text
        return resulting_dict


async def find_in_systembolaget(search_text):
    search_item_with_metadata = {}
    browser = await start_browser_accept_cookies()

    search_page_with_results = None
    while search_text is not None:
        ladder_search_result = await perform_ladder_search(browser, search_text)
        search_page_with_results = ladder_search_result["search_page_with_results"]
        search_text = ladder_search_result["new_search_query"]

    if search_page_with_results:
        hrefs_of_drinks_from_search = await get_list_of_parsed_values_with_evaluate(
            search_page_with_results, ".css-1n00zeq", "(element) => element.href"
        )
        for href in hrefs_of_drinks_from_search:
            drink_page = await open_page_wait_selector(browser, href, ".e1kth9io0")
            drink_name = await get_list_of_parsed_values_with_evaluate(
                drink_page, ".css-udxfpu", "(element) => element.textContent"
            )
            drink_sub_name = await get_list_of_parsed_values_with_evaluate(
                drink_page, ".css-1rwk7h2", "(element) => element.textContent"
            )
            drink_tags = await get_list_of_parsed_values_with_evaluate(
                drink_page, ".css-wb2cce", "(element) => element.textContent"
            )
            bottle_metadata = await get_list_of_parsed_values_with_evaluate(
                drink_page, ".e1kth9io0", "(element) => element.textContent"
            )
            bottle_price = await get_list_of_parsed_values_with_evaluate(
                drink_page, ".css-owbemz", "(element) => element.textContent"
            )
            drink_taste = await get_list_of_parsed_values_with_evaluate(
                drink_page, ".css-azme4a", "(element) => element.textContent"
            )
            search_item_with_metadata[" ".join(drink_name + drink_sub_name)] = {
                "systembolaget_link": href,
                "drink_tags": drink_tags,
                "bottle_metadata": bottle_metadata,
                "bottle_price": bottle_price,
                "drink_taste": drink_taste,
            }
    await browser.close()
    return search_item_with_metadata


def get_systembolaget_info_about_drink(url_encoded_string):
    return asyncio.get_event_loop().run_until_complete(
        asyncio.wait_for(find_in_systembolaget(url_encoded_string), 600)
    )

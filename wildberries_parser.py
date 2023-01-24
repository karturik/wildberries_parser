from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

import csv
import os
import re
import concurrent.futures

from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selectolax.parser import HTMLParser

useragent = UserAgent()

# CREATE TXT FILE IF NOT EXISTS
with open(f'product_data/finished_category_pages.txt', 'a', encoding='utf-8') as ff:
    ff.close()


# SAVE HTML CONTENT TO FILE
def html_write(soup: BeautifulSoup, file_name: str) -> None:
    with open(f'category_pages/{file_name}.txt', 'w', encoding='utf-8') as file:
        links = soup.find_all('a', class_='product-card__main j-card-link')
        for product in links:
            file.write(product.get('href') + '\n')
            print('Get product link: ', product.get('href'))
        file.close()
    print(f'category_pages/{file_name}.txt finished')


# GET REQUIRED CATEGORIES LINKS
def category_links_get() -> list[str]:
    with open('category_pages.txt', 'r', encoding='utf-8') as file:
        category_urls = file.read().strip().split('\n')
        return category_urls


# COLLECTING HTML PAGES
def start(category_page: str, tries: int) -> bool:
    options = Options()
    options.add_argument(f"user-agent={useragent.random}")
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1024,720")
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument('--blink-settings=imagesEnabled=false')
    driver = webdriver.Chrome(chrome_options=options)

    file_name = category_page
    if 'promotions' in category_page:
        file_name = category_page.split('promotions/')[1]
    if 'catalog' in category_page:
        file_name = category_page.split('catalog/')[1]
    if 'brands' in category_page:
        file_name = category_page.split('brands/')[1]
    file_name = file_name.replace('/', '+').replace('?', '+').replace('.', '+')
    try:
        driver.get(category_page)
        check_element = None
        try:
            check_element = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "product-card__main.j-card-link")))
            html = driver.page_source
            soup = BeautifulSoup(html, features='html.parser')
            html_write(soup, file_name)
            print("Get HTML")
            driver.close()
        except Exception as e:
            html = driver.page_source
            if 'class="empty-seller"' in str(html):
                raise NameError('Finish page')
            else:
                print('No product cards founded')
                print(e)
                print('No check element, try again')
                tries += 1
                print('Try: ', tries, '/5')
                if tries <= 5:
                    start(category_page, tries)
                else:
                    success = True
                    return success
        if 'ERR_PROXY_CONNECTION_FAILED' in html:
            raise NameError('ERR_PROXY_CONNECTION_FAILED')
    except OSError as e:
        if 'ProxyError' or 'ConnectTimeout' or 'ERR_PROXY_CONNECTION_FAILED' in str(e):
            raise NameError('ERR_PROXY_CONNECTION_FAILED')
        if 'NameError' in str(type(e)):
            driver.close()
            raise NameError
        else:
            print(type(e).__name__, e.args)
            driver.close()
            raise NameError('ProxyError')


# GET PRODUCT LINKS
def product_parser(urls: list):
    for url in urls:
        with open(f'product_data/finished_product_urls.csv', 'r', encoding='utf-8') as ff:
            finished_pages = ff.read()
            ff.close()
        tries = 1
        if not url in finished_pages:
            success = 'No'
            while success != 'Yes':
                success = 'No'
                print('Try link: ', url)
                try:
                    get_data(url)
                    with open(f'product_data/finished_product_urls.csv', 'a', encoding='utf-8') as ff:
                        ff.write(url + '\n')
                        ff.close()
                    success = 'Yes'
                except Exception as e:
                    print('Error: ', e)
                    if tries < 5:
                        print('Try: ', tries, '/5')
                        tries += 1
                    else:
                        print('Cant get: ', url)
                        success = 'Yes'
        else:
            print('This product already finished: ', url)


# GET PRODUCT DATA FROM PRODUCT PAGES
def get_data(link: str) -> None:
    options = Options()
    options.add_argument(f"user-agent={useragent.random}")
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("disable-infobars")
    options.add_argument("--window-size=1024,720")
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    # options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument('--blink-settings=imagesEnabled=false')
    driver = webdriver.Chrome(chrome_options=options)

    file_name = link.replace('https://www.wildberries.ru/', '').replace('/', '+').replace('?', '+').replace('.', '+')
    driver.get(link)
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "product-page__details-section.details-section")))
    tree = HTMLParser(driver.page_source)
    sku = tree.css_first('#productNmId').text()
    title = tree.css_first('.product-page__header').css_first('h1').text()
    print(title)
    brand = tree.css_first('.product-page__header').text().strip().split("  ")[0]
    category = tree.css('.breadcrumbs__item')[1:-1]
    category_tags = ""
    for i in category:
        category_tags += i.text().strip() + "/"
    category = category_tags
    if len(category) < 5:
        category = 'Зоо (гигиена, груминг, косметика)'
    # print(category)
    with open(f'product_data/{file_name}.csv', 'w', encoding='utf-8', newline='') as file:
        data = {'sku':sku,'name': 'Имя товара', 'value': title}
        csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        data = {'sku':sku,'name': 'Товарная группа', 'value': category}
        csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        data = {'sku':sku,'name': 'Бренд', 'value': brand}
        csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        data = {'sku':sku,'name': 'SKU(ID)', 'value': sku}
        csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        params_table = tree.css('.details__content.collapsable')[-1]
        params = params_table.css('tr')
        for row in params:
            name = row.css_first('th').text().strip()
            value = row.css_first('td').text().strip()
            data = {'sku':sku,'name': name, 'value': value}
            print(data)
            csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        bonus_data = tree.css_first('.details-section__inner-wrap')
        info_tabs = bonus_data.css('.details-section__details.details')
        for tab in info_tabs:
            name = tab.css_first('h3').text().strip()
            value = tab.css_first('.details__content.collapsable').text().replace('Развернуть описание', '').replace('\n', '').strip()
            data = {'sku':sku,'name': name, 'value': value}
            print(data)
            csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        file.close()
    driver.close()


# MANAGE GET PRODUCT LINKS FUNCTION
def product_data_parser() -> None:
    with open(f'product_data/finished_product_urls.csv', 'r', encoding='utf-8') as ff:
        finished_pages = ff.read().strip().split('\n')
        ff.close()
    files = os.listdir('category_pages')
    open('category_pages/all_products_urls.csv', 'w').close()
    for file in files:
        if not 'finished' in file and not 'all_products' in file:
            open('category_pages/all_products_urls.csv', 'a', encoding='utf-8').write('\n' + open(f'category_pages/{file}', 'r').read().strip())
    all_all_urls = open('category_pages/all_products_urls.csv', 'r', encoding='utf-8').read().split('\n')

    all_urls = list(set(all_all_urls) - set(finished_pages))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(product_parser, all_urls)


def main(category_pages: list) -> None:
    for category_page in category_pages:
        proxy_tries = 0
        i = 2
        finish_page = False
        file_name = category_page
        while i <= 100 and finish_page == False:
            finish_page = False
            success = 'No'
            while success != 'Yes':
                success = 'No'
                with open('category_pages/finished_pages.csv', 'r', encoding='utf-8') as finish_file:
                    finished_urls = finish_file.read()
                    finish_file.close()
                if not category_page in finished_urls:
                    print('Try page ', category_page)
                    tries = 0
                    try:
                        start(category_page, tries)
                        with open('category_pages/finished_pages.csv', 'a', encoding='utf-8') as finish_file:
                            finish_file.write(category_page + '\n')
                            finish_file.close()
                        category_page = re.sub(r'page=(\d+)', f'page={i}', category_page)
                        file_name = category_page
                        i+=1
                        proxy_tries = 0
                        success = 'Yes'
                    except Exception as e:
                        print('Error', e)
                        if not 'Finish page' in str(e):
                            proxy_tries += 1
                            print('Try', proxy_tries, "/5")
                            if proxy_tries == 5:
                                proxy_tries = 0
                        else:
                            print('Get last page!')
                            finish_page = True
                            success = 'Yes'
                else:
                    print('Finished: ', category_page)
                    finish_page = True
                    success = 'Yes'


if __name__ == '__main__':

    category_urls = category_links_get()
    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(main, category_urls)

    product_data_parser()
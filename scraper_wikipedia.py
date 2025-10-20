from playwright.sync_api import sync_playwright
import pandas as pd
import re

URL = "https://www.zara.com/ca/fr/homme-tout-l7465.html?v1=2443335"

def scrape_zara_products(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='fr-CA'
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(4000)

        try:
            cookie_btn = page.query_selector("button#onetrust-accept-btn-handler")
            if cookie_btn:
                cookie_btn.click()
                page.wait_for_timeout(2000)
        except:
            pass

        for i in range(4):
            page.evaluate(f"window.scrollTo(0, {(i+1) * 1000})")
            page.wait_for_timeout(1000)

        products = []
        product_items = page.query_selector_all("li.product-grid-product")

        if product_items:
            for idx, item in enumerate(product_items[:50]):
                try:
                    product = {}
                    links = item.query_selector_all("a")
                    main_link = None
                    for link in links:
                        href = link.get_attribute("href")
                        if href and ('/p' in href or 'product' in href.lower()):
                            main_link = link
                            break
                    if not main_link and links:
                        main_link = links[0]
                    if main_link:
                        href = main_link.get_attribute("href")
                        product["lien"] = f"https://www.zara.com{href}" if href and href.startswith('/') else href
                    else:
                        product["lien"] = ""

                    titre = ""
                    text_elements = item.query_selector_all("h2, h3, h4, p, span, div")
                    for elem in text_elements:
                        text = elem.inner_text().strip()
                        if text and 5 < len(text) < 150 and not text.replace(' ', '').isdigit():
                            if not re.match(r'^[\d\s,.$CAD]+$', text):
                                if not titre or len(text) > len(titre):
                                    titre = text
                    product["titre"] = titre

                    prix = ""
                    price_elements = item.query_selector_all("[class*='price'], [class*='money'], .price-current, span, p")
                    for elem in price_elements:
                        text = elem.inner_text().strip()
                        if re.search(r'\d+[,.]?\d*\s*\$|CAD\s*\d+|\$\s*\d+', text):
                            prix = text
                            break
                    product["prix"] = prix

                    img = item.query_selector("img")
                    if img:
                        img_src = img.get_attribute("src") or img.get_attribute("data-src") or img.get_attribute("data-lazy-src") or ""
                        product["image"] = img_src
                    else:
                        product["image"] = ""

                    product_id = item.get_attribute("data-productid") or item.get_attribute("id") or ""
                    product["id"] = product_id

                    if product["titre"] or product["lien"]:
                        products.append(product)
                except:
                    continue

        if not products:
            html_content = page.content()
            with open("zara_full_debug.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            all_links = page.query_selector_all("a[href*='/p']")
            seen = set()
            for link in all_links[:30]:
                href = link.get_attribute("href")
                if href and href not in seen:
                    seen.add(href)
                    text = link.inner_text().strip()
                    if text and len(text) > 3:
                        products.append({
                            "titre": text,
                            "lien": f"https://www.zara.com{href}" if href.startswith('/') else href,
                            "prix": "",
                            "image": "",
                            "id": ""
                        })

        page.screenshot(path="zara_final.png", full_page=True)
        page.wait_for_timeout(1000)
        browser.close()
        return products

def main():
    try:
        products = scrape_zara_products(URL)
        if not products:
            return
        df = pd.DataFrame(products)
        df = df[df['titre'].str.len() > 3].drop_duplicates(subset=['titre'], keep='first')
        if df.empty:
            return
        filename = "zara_homme.csv"
        df.to_csv(filename, index=False, encoding="utf-8")
        for idx, row in df.head(10).iterrows():
            print(f"{idx+1}. {row['titre']}")
            if row.get('prix'):
                print(f"   {row['prix']}")
            if row.get('lien'):
                print(f"   {row['lien'][:65]}...")
        print(f"Total products: {len(df)}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
#
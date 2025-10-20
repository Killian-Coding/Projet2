from playwright.sync_api import sync_playwright
import pandas as pd
import re

URL = "https://www.zara.com/ca/fr/homme-tout-l7465.html"

def extraire_prix_numerique(prix_text):
    if not prix_text:
        return None
    match = re.search(r'(\d+)[,.](\d{2})', prix_text)
    if match:
        return float(f"{match.group(1)}.{match.group(2)}")
    match = re.search(r'\d+', prix_text)
    if match:
        return float(match.group())
    return None

def categoriser_produit(titre):
    titre_lower = titre.lower()
    if any(word in titre_lower for word in ['chaussure', 'basket', 'bottine', 'botte', 'mocassin', 'sandale', 'espadrille']):
        return 'Chaussures'
    if any(word in titre_lower for word in ['ceinture', 'sac', 'portefeuille', 'chapeau', 'casquette', 'écharpe', 'gant']):
        return 'Accessoires'
    if any(word in titre_lower for word in ['parfum', 'edt', 'edp', 'eau de toilette', 'eau de parfum', 'cologne']):
        return 'Parfums'
    return 'Vêtements'

def sous_categoriser_produit(titre, categorie):
    titre_lower = titre.lower()
    if categorie == 'Chaussures':
        if 'basket' in titre_lower or 'sneaker' in titre_lower:
            return 'Baskets'
        elif 'bottine' in titre_lower or 'chelsea' in titre_lower:
            return 'Bottines'
        elif 'botte' in titre_lower:
            return 'Bottes'
        elif 'mocassin' in titre_lower:
            return 'Mocassins'
        elif 'sandale' in titre_lower:
            return 'Sandales'
        else:
            return 'Chaussures habillées'
    elif categorie == 'Vêtements':
        if any(word in titre_lower for word in ['veste', 'manteau', 'blouson', 'doudoune', 'parka', 'trench', 'blazer']):
            return 'Vestes et Manteaux'
        elif any(word in titre_lower for word in ['pantalon', 'jean', 'chino', 'jogging', 'cargo']):
            return 'Pantalons'
        elif any(word in titre_lower for word in ['pull', 'sweat', 'polo', 'cardigan', 'gilet']):
            return 'Hauts'
        elif 'chemise' in titre_lower or 'surchemise' in titre_lower:
            return 'Chemises'
        elif 't-shirt' in titre_lower or 'tee-shirt' in titre_lower:
            return 'T-shirts'
        else:
            return 'Autre'
    elif categorie == 'Accessoires':
        if 'ceinture' in titre_lower:
            return 'Ceintures'
        elif any(word in titre_lower for word in ['sac', 'sacoche', 'portefeuille']):
            return 'Maroquinerie'
        elif any(word in titre_lower for word in ['chapeau', 'casquette', 'bonnet']):
            return 'Couvre-chefs'
        else:
            return 'Autre'
    elif categorie == 'Parfums':
        if 'edt' in titre_lower or 'eau de toilette' in titre_lower:
            return 'Eau de toilette'
        elif 'edp' in titre_lower or 'eau de parfum' in titre_lower:
            return 'Eau de parfum'
        else:
            return 'Coffrets'
    return 'Non classé'

def determiner_type_produit(titre):
    titre_propre = re.sub(r'\+\d+', '', titre)
    titre_propre = re.sub(r'\$.*', '', titre_propre)
    titre_propre = titre_propre.strip()
    if '\n' in titre_propre:
        titre_propre = titre_propre.split('\n')[0]
    return titre_propre

def scrape_zara_products(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=['--disable-blink-features=AutomationControlled'])
        context = browser.new_context(viewport={'width': 1920, 'height': 1080}, user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', locale='fr-CA')
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        try:
            cookie_btn = page.query_selector("button#onetrust-accept-btn-handler")
            if cookie_btn:
                cookie_btn.click()
                page.wait_for_timeout(2000)
        except:
            pass
        previous_height = 0
        same_count = 0
        max_same = 6
        max_scrolls = 150
        for i in range(max_scrolls):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2500)
            current_height = page.evaluate("document.body.scrollHeight")
            current_count = len(page.query_selector_all("li.product-grid-product"))
            if current_height == previous_height:
                same_count += 1
                if same_count >= max_same:
                    break
            else:
                same_count = 0
            previous_height = current_height
        page.wait_for_timeout(3000)
        products = []
        product_items = page.query_selector_all("li.product-grid-product")
        for idx, item in enumerate(product_items):
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
                        if not re.match(r'^[\d\s,.$CAD€]+$', text):
                            if not titre or len(text) > len(titre):
                                titre = text
                product["titre_complet"] = titre
                product["titre"] = determiner_type_produit(titre)
                prix_text = ""
                price_elements = item.query_selector_all("[class*='price'], [class*='money'], .price-current, span, p")
                for elem in price_elements:
                    text = elem.inner_text().strip()
                    if re.search(r'(\$|CAD|€)\s*\d+', text):
                        prix_text = text
                        break
                product["prix_texte"] = prix_text
                product["prix"] = extraire_prix_numerique(prix_text)
                product["devise"] = "CAD"
                img = item.query_selector("img")
                if img:
                    img_src = img.get_attribute("src") or img.get_attribute("data-src") or img.get_attribute("data-lazy-src") or ""
                    product["image_url"] = img_src
                else:
                    product["image_url"] = ""
                product["id_produit"] = item.get_attribute("data-productid") or item.get_attribute("id") or ""
                product["categorie"] = categoriser_produit(titre)
                product["sous_categorie"] = sous_categoriser_produit(titre, product["categorie"])
                product["disponible"] = True
                if product["titre"] or product["lien"]:
                    products.append(product)
            except Exception as e:
                continue
        try:
            page.screenshot(path="zara_final.png", full_page=False)
        except:
            pass
        browser.close()
        return products

def main():
    products = scrape_zara_products(URL)
    if not products:
        return
    df = pd.DataFrame(products)
    df = df[df['titre'].str.len() > 3]
    df = df.drop_duplicates(subset=['titre'], keep='first')
    colonnes_ordre = ['id_produit','titre','titre_complet','categorie','sous_categorie','prix','devise','prix_texte','lien','image_url','disponible']
    colonnes_existantes = [col for col in colonnes_ordre if col in df.columns]
    df = df[colonnes_existantes]
    filename = "zara_homme_structure.csv"
    df.to_csv(filename, index=False, encoding="utf-8")
    print(f"{len(df)} produits exportés: {filename}")

if __name__ == "__main__":
    main()

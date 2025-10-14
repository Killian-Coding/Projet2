from playwright.sync_api import sync_playwright
import pandas as pd
import re

URL = "https://www.zara.com/ca/fr/homme-tout-l7465.html?v1=2443335"

def scrape_zara_products(url):
    with sync_playwright() as p:
        print("🚀 Lancement du navigateur...")
        
        browser = p.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            locale='fr-CA'
        )
        
        page = context.new_page()
        
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        
        print("📄 Chargement de la page...")
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        print("   ✓ Page chargée")
        
        page.wait_for_timeout(4000)
        
        # Accepter cookies
        try:
            cookie_btn = page.query_selector("button#onetrust-accept-btn-handler")
            if cookie_btn:
                cookie_btn.click()
                print("   ✓ Cookies acceptés")
                page.wait_for_timeout(2000)
        except:
            pass
        
        # Scroller
        print("📜 Scroll...")
        for i in range(4):
            page.evaluate(f"window.scrollTo(0, {(i+1) * 1000})")
            page.wait_for_timeout(1000)
        
        print("🔍 Analyse de la structure...")
        
        # Méthode 1: Extraire via les éléments de grille de produits
        products = []
        
        product_items = page.query_selector_all("li.product-grid-product")
        print(f"   Trouvé {len(product_items)} éléments li.product-grid-product")
        
        if len(product_items) > 0:
            for idx, item in enumerate(product_items[:50]):
                try:
                    product = {}
                    
                    # Extraire toutes les infos possibles
                    # 1. Chercher le lien principal
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
                    
                    # 2. Titre - essayer plusieurs endroits
                    titre = ""
                    
                    # Essai dans les éléments texte
                    text_elements = item.query_selector_all("h2, h3, h4, p, span, div")
                    for elem in text_elements:
                        text = elem.inner_text().strip()
                        # Filtrer: doit contenir des lettres, pas trop court, pas trop long
                        if text and 5 < len(text) < 150 and not text.replace(' ', '').isdigit():
                            # Ignorer si c'est juste un prix
                            if not re.match(r'^[\d\s,.$CAD]+$', text):
                                if not titre or len(text) > len(titre):
                                    titre = text
                    
                    product["titre"] = titre
                    
                    # 3. Prix
                    prix = ""
                    price_elements = item.query_selector_all("[class*='price'], [class*='money'], .price-current, span, p")
                    for elem in price_elements:
                        text = elem.inner_text().strip()
                        # Chercher des patterns de prix
                        if re.search(r'\d+[,.]?\d*\s*\$|CAD\s*\d+|\$\s*\d+', text):
                            prix = text
                            break
                    
                    product["prix"] = prix
                    
                    # 4. Image
                    img = item.query_selector("img")
                    if img:
                        img_src = img.get_attribute("src") or img.get_attribute("data-src") or img.get_attribute("data-lazy-src") or ""
                        product["image"] = img_src
                    else:
                        product["image"] = ""
                    
                    # 5. ID produit (si disponible dans les attributs)
                    product_id = item.get_attribute("data-productid") or item.get_attribute("id") or ""
                    product["id"] = product_id
                    
                    # Ajouter si on a au moins un titre ou un lien
                    if product["titre"] or product["lien"]:
                        products.append(product)
                        if idx < 3:  # Debug: afficher les 3 premiers
                            print(f"\n   Produit {idx+1}:")
                            print(f"      Titre: {product['titre'][:50]}...")
                            print(f"      Prix: {product['prix']}")
                            print(f"      Lien: {product['lien'][:60]}...")
                
                except Exception as e:
                    print(f"   ⚠️ Erreur produit {idx}: {e}")
                    continue
        
        print(f"\n   ✓ {len(products)} produits extraits")
        
        # Si toujours rien, dump du HTML pour analyse manuelle
        if len(products) == 0:
            print("\n⚠️ Extraction alternative - Analyse du HTML brut...")
            
            # Sauvegarder le HTML complet
            html_content = page.content()
            with open("zara_full_debug.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Chercher tous les liens qui ressemblent à des produits
            all_links = page.query_selector_all("a[href*='/p']")
            print(f"   Trouvé {len(all_links)} liens avec '/p' dans l'URL")
            
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
            
            print(f"   ✓ {len(products)} liens de produits trouvés")
        
        # Screenshot
        page.screenshot(path="zara_final.png", full_page=True)
        print("   📸 Screenshot: zara_final.png")
        
        page.wait_for_timeout(1000)
        browser.close()
        
        return products

def main():
    print("=" * 70)
    print("🛍️  SCRAPER ZARA - ANALYSE APPROFONDIE")
    print("=" * 70)
    print()
    
    try:
        products = scrape_zara_products(URL)
        
        if not products:
            print("\n❌ Aucun produit trouvé")
            print("\n📋 Actions suggérées:")
            print("   1. Ouvrir zara_full_debug.html dans un navigateur")
            print("   2. Faire Ctrl+F et chercher 'product-grid-product'")
            print("   3. Regarder la structure HTML d'un produit")
            print("   4. Me donner un exemple de la structure HTML")
            return
        
        # Créer DataFrame
        df = pd.DataFrame(products)
        
        # Nettoyer
        df = df[df['titre'].str.len() > 3]
        df = df.drop_duplicates(subset=['titre'], keep='first')
        
        if len(df) == 0:
            print("\n❌ Tous les produits filtrés")
            return
        
        # Sauvegarder
        filename = "zara_homme.csv"
        df.to_csv(filename, index=False, encoding="utf-8")
        
        print(f"\n✅ {len(df)} produits exportés: {filename}")
        
        # Aperçu
        print("\n📋 APERÇU DES PRODUITS:")
        print("=" * 70)
        for idx, row in df.head(10).iterrows():
            print(f"\n{idx+1}. {row['titre']}")
            if row.get('prix'):
                print(f"   💰 {row['prix']}")
            if row.get('lien'):
                print(f"   🔗 {row['lien'][:65]}...")
        
        # Stats
        print("\n" + "=" * 70)
        print("📊 STATISTIQUES:")
        print(f"   Total: {len(df)} produits")
        print(f"   Avec prix: {df['prix'].astype(bool).sum()}")
        print(f"   Avec image: {df['image'].astype(bool).sum()}")
        print(f"   Avec lien: {df['lien'].astype(bool).sum()}")
            
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
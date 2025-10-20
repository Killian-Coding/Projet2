from playwright.sync_api import sync_playwright
import pandas as pd
import re

URL = "https://www.zara.com/ca/fr/homme-tout-l7465.html"

def extraire_prix_numerique(prix_text):
    """Extrait le prix numérique d'une chaîne de texte"""
    if not prix_text:
        return None
    
    # Chercher un pattern comme "$ 219,00" ou "219.00"
    match = re.search(r'(\d+)[,.](\d{2})', prix_text)
    if match:
        return float(f"{match.group(1)}.{match.group(2)}")
    
    # Si seulement un nombre entier
    match = re.search(r'\d+', prix_text)
    if match:
        return float(match.group())
    
    return None

def categoriser_produit(titre):
    """Détermine la catégorie en fonction du titre"""
    titre_lower = titre.lower()
    
    # Chaussures
    if any(word in titre_lower for word in ['chaussure', 'basket', 'bottine', 'botte', 'mocassin', 'sandale', 'espadrille']):
        return 'Chaussures'
    
    # Accessoires
    if any(word in titre_lower for word in ['ceinture', 'sac', 'portefeuille', 'chapeau', 'casquette', 'écharpe', 'gant']):
        return 'Accessoires'
    
    # Parfums
    if any(word in titre_lower for word in ['parfum', 'edt', 'edp', 'eau de toilette', 'eau de parfum', 'cologne']):
        return 'Parfums'
    
    # Vêtements (par défaut)
    return 'Vêtements'

def sous_categoriser_produit(titre, categorie):
    """Détermine la sous-catégorie en fonction du titre et de la catégorie"""
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
        # Vestes et Manteaux
        if any(word in titre_lower for word in ['veste', 'manteau', 'blouson', 'doudoune', 'parka', 'trench', 'blazer']):
            return 'Vestes et Manteaux'
        
        # Pantalons
        elif any(word in titre_lower for word in ['pantalon', 'jean', 'chino', 'jogging', 'cargo']):
            return 'Pantalons'
        
        # Hauts
        elif any(word in titre_lower for word in ['pull', 'sweat', 'polo', 'cardigan', 'gilet']):
            return 'Hauts'
        
        # Chemises
        elif 'chemise' in titre_lower or 'surchemise' in titre_lower:
            return 'Chemises'
        
        # T-shirts
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
    """Extrait le type spécifique du produit"""
    # Nettoyer le titre des prix et variantes
    titre_propre = re.sub(r'\+\d+', '', titre)
    titre_propre = re.sub(r'\$.*', '', titre_propre)
    titre_propre = titre_propre.strip()
    
    # Prendre la première ligne si multi-lignes
    if '\n' in titre_propre:
        titre_propre = titre_propre.split('\n')[0]
    
    return titre_propre

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
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")

        print("📄 Chargement de la page...")
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
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

        # --- Infinite Scroll ---
        print("📜 Début du scroll infini...")

        previous_height = 0
        same_count = 0
        max_same = 6
        max_scrolls = 150

        for i in range(max_scrolls):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2500)

            current_height = page.evaluate("document.body.scrollHeight")
            current_count = len(page.query_selector_all("li.product-grid-product"))
            print(f"   Scroll {i+1}: {current_count} produits détectés...")

            if current_height == previous_height:
                same_count += 1
                if same_count >= max_same:
                    print("📍 Aucun nouveau contenu détecté après plusieurs tentatives — arrêt du scroll.")
                    break
            else:
                same_count = 0

            previous_height = current_height

        print("✅ Scroll infini terminé — tous les produits devraient être chargés.")
        page.wait_for_timeout(3000)

        # --- Extraction des produits ---
        products = []
        product_items = page.query_selector_all("li.product-grid-product")
        print(f"   Trouvé {len(product_items)} produits dans la grille.")

        for idx, item in enumerate(product_items):
            try:
                product = {}

                # Lien principal
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

                # Titre
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

                # Prix
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

                # Image (URL uniquement)
                img = item.query_selector("img")
                if img:
                    img_src = (
                        img.get_attribute("src")
                        or img.get_attribute("data-src")
                        or img.get_attribute("data-lazy-src")
                        or ""
                    )
                    product["image_url"] = img_src
                else:
                    product["image_url"] = ""

                # ID produit
                product["id_produit"] = item.get_attribute("data-productid") or item.get_attribute("id") or ""

                # Catégorisation
                product["categorie"] = categoriser_produit(titre)
                product["sous_categorie"] = sous_categoriser_produit(titre, product["categorie"])
                
                # Disponibilité
                product["disponible"] = True

                if product["titre"] or product["lien"]:
                    products.append(product)
                    if idx < 3:
                        print(f"\n   Produit {idx+1}:")
                        print(f"      Titre: {product['titre'][:50]}...")
                        print(f"      Catégorie: {product['categorie']} > {product['sous_categorie']}")
                        print(f"      Prix: {product['prix']} {product['devise']}")

            except Exception as e:
                print(f"⚠️ Erreur sur le produit {idx}: {e}")
                continue

        print(f"\n   ✓ {len(products)} produits extraits avant nettoyage")

        # Screenshot de sécurité
        try:
            page.screenshot(path="zara_final.png", full_page=False)
            print("   📸 Screenshot capturé")
        except Exception as e:
            print(f"⚠️ Screenshot non capturé : {e}")

        browser.close()
        return products


def main():
    print("=" * 70)
    print("🛍️  SCRAPER ZARA - VERSION STRUCTURÉE AVEC CATÉGORIES")
    print("=" * 70)

    try:
        products = scrape_zara_products(URL)

        if not products:
            print("\n❌ Aucun produit trouvé")
            return

        df = pd.DataFrame(products)
        
        # Nettoyage
        df = df[df['titre'].str.len() > 3]
        df = df.drop_duplicates(subset=['titre'], keep='first')
        
        # Réorganiser les colonnes dans l'ordre logique
        colonnes_ordre = [
            'id_produit',
            'titre',
            'titre_complet',
            'categorie',
            'sous_categorie',
            'prix',
            'devise',
            'prix_texte',
            'lien',
            'image_url',
            'disponible'
        ]
        
        # Garder seulement les colonnes qui existent
        colonnes_existantes = [col for col in colonnes_ordre if col in df.columns]
        df = df[colonnes_existantes]

        # Export CSV
        filename = "zara_homme_structure.csv"
        df.to_csv(filename, index=False, encoding="utf-8")

        print(f"\n✅ {len(df)} produits exportés: {filename}")
        
        # Statistiques par catégorie
        print("\n📊 STATISTIQUES PAR CATÉGORIE:")
        print("=" * 70)
        stats_cat = df.groupby('categorie').agg({
            'id_produit': 'count',
            'prix': ['mean', 'min', 'max']
        }).round(2)
        print(stats_cat)
        
        print("\n📊 STATISTIQUES PAR SOUS-CATÉGORIE:")
        print("=" * 70)
        stats_sous_cat = df.groupby(['categorie', 'sous_categorie']).size().reset_index(name='count')
        stats_sous_cat = stats_sous_cat.sort_values(['categorie', 'count'], ascending=[True, False])
        print(stats_sous_cat.to_string(index=False))
        
        print("\n📋 APERÇU DES 10 PREMIERS PRODUITS:")
        print("=" * 70)
        for idx, row in df.head(10).iterrows():
            print(f"\n{idx+1}. {row['titre']}")
            print(f"   📁 {row['categorie']} > {row['sous_categorie']}")
            if pd.notna(row['prix']):
                print(f"   💰 {row['prix']:.2f} {row['devise']}")
            if row.get('lien'):
                print(f"   🔗 {row['lien'][:60]}...")

        print("\n" + "=" * 70)
        print("📊 RÉSUMÉ GÉNÉRAL:")
        print(f"   Total produits: {len(df)}")
        print(f"   Catégories: {df['categorie'].nunique()}")
        print(f"   Sous-catégories: {df['sous_categorie'].nunique()}")
        print(f"   Avec prix: {df['prix'].notna().sum()}")
        print(f"   Prix moyen: {df['prix'].mean():.2f} CAD")
        print(f"   Prix min: {df['prix'].min():.2f} CAD")
        print(f"   Prix max: {df['prix'].max():.2f} CAD")
        print(f"   Avec image: {df['image_url'].astype(bool).sum()}")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
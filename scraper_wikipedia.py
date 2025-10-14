import requests
from bs4 import BeautifulSoup

url = "https://fr.wikipedia.org/wiki/Liste_des_pays_par_population"

# Ajouter un header pour simuler un vrai navigateur
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    soup = BeautifulSoup(response.text, "html.parser")

    table = soup.find("table", {"class": "wikitable"})
    rows = table.find_all("tr")[1:]

    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 4:
            pays = cols[1].get_text(strip=True)
            population = cols[2].get_text(strip=True)
            date = cols[3].get_text(strip=True)

            print(f"Pays : {pays}")
            print(f"Population : {population}")
            print(f"Date : {date}")
            print("-" * 40)
else:
    print("Erreur de chargement :", response.status_code)

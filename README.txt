Krypto Dashboard – Mit Flask und Live-Daten

Ein interaktives, modernes Krypto-Dashboard auf Basis von **Flask**, das in Echtzeit Informationen über Kryptowährungen anzeigt. Es kombiniert Finanzdaten, Nachrichten, Karten und Nutzerfunktionen in einer eleganten Benutzeroberfläche mit Dark-Theme und Goldakzenten.

Funktionen

-Anzeige der Top 50 Kryptowährungen (Preis in EUR & USD)
-Dynamisches Bitcoin-Preisdiagramm (7 Tage)
-Aktuelle Krypto-Nachrichten von CryptoCompare und CoinDesk
-Market Sentiment: Fear & Greed Index von Alternative.me
-Weltkarte mit Handelsvolumen & Börsen (Leaflet + CoinGecko + OpenCage)
-Favoriten-System mit Benutzer-Login
-Persönliche Wallet zum Verwalten gekaufter Coins
-Zufälliger „Crypto-Joke“ des Tages
-Registrierungs- und Login-System mit SQLite

---

##Verwendete APIs

| API-Anbieter        | Beschreibung                                                                                   |
|---------------------|-----------------------------------------------------------------------------------------------|
| **[CoinGecko](https://www.coingecko.com/de/api)**        | Hauptquelle für Preise, Charts, Marktkapitalisierung, Börsendaten               |
| **[CryptoCompare](https://min-api.cryptocompare.com/)**  | Krypto-News (Titel, Quelle, Vorschaubild)                                       |
| **[CoinDesk (RSS über rss2json)](https://www.coindesk.com/arc/outboundfeeds/rss/)** | Weitere Nachrichten-Quelle                                                       |
| **[Alternative.me FNG](https://alternative.me/crypto/fear-and-greed-index/)** | Fear & Greed Index (Stimmungsbarometer des Markts)                              |
| **[exchangerate.host](https://exchangerate.host/)**       | Umrechnung USD ↔ EUR                                                              |
| **[Leaflet.js](https://leafletjs.com/)**                  | Interaktive Weltkarte zur Darstellung der Börsen                                 |
| **[OpenCage Geocoder](https://opencagedata.com/)**        | Umwandlung von Länder-/Städtenamen in Geo-Koordinaten                            |
| **[Official Joke API](https://official-joke-api.appspot.com/)** | Für zufällige Programmierer-Witze                                                |

---

Setup & Ausführung

### Voraussetzungen:
- Python 3.x
- Flask
- Internetverbindung (für API-Zugriffe)

### Installation (lokal):
```bash
# Projekt klonen
git clone https://github.com/DEIN_USERNAME/krypto-dashboard.git
cd krypto-dashboard

# Virtuelle Umgebung (empfohlen)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# Datenbank initialisieren & Server starten
python app.py

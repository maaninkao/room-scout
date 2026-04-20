# Room Scout

Notification service that monitors Joivy coliving listings (Trento) and
sends phone push via ntfy.sh when new rooms match user-defined filters.
No auto-messaging, no login, no transactions — pure observer + notifier.

## Tekninen stack

- Python 3.11+
- httpx (fetch), selectolax (parse), pydantic v2 (models), click (CLI)
- SQLite (dedup URL-slugilla)
- ntfy.sh (puhelin-push)

## Kehityssäännöt

1. Ei live-verkkokutsuja testeissä — scraper käyttää tests/fixtures/trento_sample.html.
2. httpx mockataan notifier-testeissä — ei oikeita ntfy-kutsuja.
3. Jokainen moduuli saa pytest-testit, acceptance = pytest vihreä.
4. UTF-8 ilman BOM:ia kaikissa tekstitiedostoissa.
5. Graceful degradation: yksittäisen kortin parse-virhe ei kaada ajoa — logita warning ja jatka.

## SEURAAVA TEHTÄVÄ

Rakenna MVP käsin ajettavaksi `room-scout run-once` -komennoksi. Scraper käyttää fixturea, notifier mockataan testeissä. Live-validointi aamulla tehtävien valmistumisen jälkeen.

- [ ] Pystytä Python-projektipohja: luo virtuaaliympäristö `python -m venv .venv`, kirjoita pyproject.toml (hatchling backend, Python >=3.11, runtime httpx>=0.27 selectolax>=0.3.21 pydantic>=2.6 pyyaml>=6.0 python-dotenv>=1.0 click>=8.1, dev-extras pytest>=8.0 pytest-asyncio>=0.23, console script `room-scout = room_scout.cli:main`), luo src/room_scout/-pakkaushakemisto tyhjillä stub-moduuleilla (__init__, __main__, cli, scraper, storage, filters, notifier, config, models), kirjoita .env.example `NTFY_TOPIC=CHANGE_ME_TO_LONG_RANDOM_STRING` ja config.example.yaml jossa kaupunki trento ja filtterit stubina. Hyväksyntä: `pip install -e ".[dev]"` onnistuu ja `room-scout --help` näyttää subkomennot.

- [ ] Määrittele Pydantic-datamallit ja filtterilogiikka: luo src/room_scout/models.py (Listing, FilterConfig, AppConfig v2-mallit kenttineen slug/url/title/address/size_sqm/flatmates/price_eur/available_from/recently_booked/image_url sekä kaikki filtterikentät max/min-price, min/max-sqm, earliest/latest_available, address_must_contain listat, include_recently_booked), luo src/room_scout/filters.py jossa `matches(listing, f)` palauttaa tuple[bool, str], AND-logiikka kaikille kentille, address_must_contain passaa jos ANY substring case-insensitive löytyy, address_must_not_contain hylkää jos ANY match, None-kentät skipataan. Kirjoita tests/test_filters.py vähintään 3 testillä: pass, reject-by-price, reject-by-recently-booked. Hyväksyntä: pytest vihreä.

- [ ] Toteuta SQLite-tallennuskerros kohteille: luo src/room_scout/storage.py sqlite3 stdlib -kirjastolla, parent dir luodaan automaattisesti db_pathille, taulu seen_listings jossa slug TEXT PRIMARY KEY, first_seen_at TEXT, last_seen_at TEXT, notified_at TEXT nullable, payload_json TEXT. API: mark_seen(listing) palauttaa True uudelle + upsertaa first/last_seen_at, mark_notified(slug) asettaa notified_at, was_notified(slug) palauttaa bool. Kirjoita tests/test_storage.py tmp_pathilla tai :memory: -kantalla, 3 testiä: insert-new-returns-true, insert-same-returns-false, mark-notified-persists. Hyväksyntä: pytest vihreä.

- [ ] Parsi Joivy-HTML fixturesta Listing-olioiksi: luo src/room_scout/scraper.py joka lukee tests/fixtures/trento_sample.html (ÄLÄ hae live-URLia). Strategia A preferoitu: etsi <script id="__NEXT_DATA__" type="application/json">, parsi JSON ja mappaa kentät Listing-malliin. Strategia B fallback: selectolax HTML-parse, href-pattern `/en/rent-single-room-trento-*/tn-\d{4}-\d{2}-[a-z]/`, poimi slug urlin viimeisestä segmentistä, title h2:sta, size_sqm regexillä `(\d+(?:\.\d+)?)\s*m²`, price_eur regexillä `€\s*(\d+)`, available_from "From DD Mon YYYY" -muodosta TAI recently_booked=True jos teksti "Recently Booked", image_url ensimmäisestä img-tagista. Yksittäisen kortin virhe logitetaan warningiksi eikä kaada ajoa. Kirjoita tests/test_scraper.py jossa fixturesta tulee vähintään 5 Listingiä kaikilla slug-muotoa tn-\d{4}-\d{2}-[a-z] ja vähintään yksi recently_booked=True. Ehdoton kielto: ei httpx.get Joivy-URLiin. Hyväksyntä: pytest vihreä.

- [ ] Rakenna ntfy-push-lähettäjä ja click-CLI: luo src/room_scout/notifier.py jossa send_notification(config, listing) POSTaa ntfy-serverille headerein Title, Click (listing.url), Priority=high, Tags=house, Attach jos image_url, body muodossa "€{price}/mo · {size} m² · from {available_from}" (tai "booked") + osoite jos saatavilla, httpx-timeout 10s, raise non-2xx. Luo src/room_scout/config.py joka lataa config.yaml (oletus ./config.yaml, override ROOM_SCOUT_CONFIG env) ja mergeaa .env:stä NTFY_TOPIC (REQUIRED). Luo src/room_scout/cli.py click-komennoilla run-once (fetch → mark_seen → jos uusi JA matches niin send_notification + mark_notified, tulosta "Found N, M new, K matched, K notified") ja test-notify (lähettää kovakoodatun testi-ilmoituksen). Kirjoita tests/test_notifier.py joka mockaa httpx.post ja tarkastaa headerit + body-sisällön. Testit eivät saa tehdä oikeita verkkokutsuja. Hyväksyntä: pytest vihreä.

- [ ] Dokumentoi README ja viimeistele koodi: kirjoita README.md joka sisältää lyhyen kuvauksen (2 lausetta), quick start -ohjeen (venv, install, ntfy-appi, config.yaml, .env, test-notify, run-once), filtterit lyhyesti, data-polut (SQLite poistettavissa resetointia varten), known limitations (parse best-effort, ei ajastusta). Lisää yksirivinen docstring jokaisen src/room_scout/-moduulin alkuun. Hyväksyntä: pytest vihreä ja `python -m py_compile src/room_scout/*.py` ilman virheitä.

## IHMISELLE

Live-validointi aamulla kun koodi on kasassa:

- [ ] Rekisteröi ntfy-topic ja aktivoi push-ilmoitukset puhelimella: asenna ntfy-appi, valitse pitkä satunnainen topic, tilaa appissa, aseta NTFY_TOPIC .env:iin, kopioi config.example.yaml config.yamliksi ja säädä filtterit, aja `room-scout test-notify` ja varmista push tulee alle 5 s, aja `room-scout run-once` live-datalla ja tarkasta >=5 listingiä + matchit pushataan, aja run-once toistamiseen ja varmista 0 pushia (dedup), inspektoi scraper.py:n docstringistä kumpi parse-strategia voitti ja säädä tarvittaessa.

## Raporttipohja

TEHTY:
TULOS:
ONGELMAT:
MUUTETUT TIEDOSTOT:
SEURAAVA ASKEL: luo src/room_scout/scraper.py joka lukee tests/fixtures/trento_sample.html (ÄLÄ hae live-URLia). Strategia A preferoitu: etsi <script id="__NEXT_DATA__" type="application/json">, parsi JSON ja mappaa kentät Listing-malliin. Strategia B fallback: selectolax HTML-parse, href-pattern `/en/rent-single-room-trento-*/tn-\d{4}-\d{2}-[a-z]/`, poimi slug urlin viimeisestä segmentistä, title h2:sta, size_sqm regexillä `(\d+(?:\.\d+)?)\s*m²`, price_eur regexillä `€\s*(\d+)`, available_from "From DD Mon YYYY" -muodosta TAI recently_booked=True jos teksti "Recently Booked", image_url ensimmäisestä img-tagista. Yksittäisen kortin virhe logitetaan warningiksi eikä kaada ajoa. Kirjoita tests/test_scraper.py jossa fixturesta tulee vähintään 5 Listingiä kaikilla slug-muotoa tn-\d{4}-\d{2}-[a-z] ja vähintään yksi recently_booked=True. Ehdoton kielto: ei httpx.get Joivy-URLiin. Hyväksyntä: pytest vihreä.

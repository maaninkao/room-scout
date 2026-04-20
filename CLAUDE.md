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

1. Ei live-verkkokutsuja testeissä eikä validoinnissa — scraper käyttää tiedostoa `tests/fixtures/trento_sample.html`.
2. httpx mockataan kaikissa notifier-testeissä — ei oikeita ntfy-kutsuja.
3. Jokainen moduuli saa pytest-testit, acceptance = pytest vihreä.
4. UTF-8 ilman BOM:ia kaikissa tekstitiedostoissa.
5. Graceful degradation: yksittäisen kortin parse-virhe ei saa kaataa koko ajoa — logita warning ja jatka.

## SEURAAVA TEHTÄVÄ

MVP rakennetaan käsin ajettavaksi komennoksi `room-scout run-once`. Scraper käyttää fixture-tiedostoa, notifier mockattuna testeissä. Live-validointi tehdään ihmisen käsin tehtävien 1–6 valmistumisen jälkeen.

- [ ] 1. Skaffaa projekti: luo virtuaaliympäristö komennolla `python -m venv .venv` ja aktivoi se, kirjoita pyproject.toml (hatchling build backend, Python >=3.11, runtime-deps httpx>=0.27 selectolax>=0.3.21 pydantic>=2.6 pyyaml>=6.0 python-dotenv>=1.0 click>=8.1, dev-extras pytest>=8.0 pytest-asyncio>=0.23, console script `room-scout = room_scout.cli:main`), luo src/room_scout/-kansiorakenne (__init__.py, __main__.py, cli.py, scraper.py, storage.py, filters.py, notifier.py, config.py, models.py tyhjinä stubeina), luo .env.example sisällöllä `NTFY_TOPIC=CHANGE_ME_TO_LONG_RANDOM_STRING`, luo config.example.yaml (kaupunki trento ja filtterit stubina). Acceptance: `pip install -e .[dev]` onnistuu ja `room-scout --help` näyttää molemmat subkomennot run-once ja test-notify.

- [ ] 2. Luo models.py ja filters.py: Pydantic v2 -mallit Listing (slug, url, title, address, size_sqm, flatmates, price_eur, available_from, recently_booked, image_url), FilterConfig (max_price_eur, min_price_eur, min_sqm, max_sqm, earliest_available_from, latest_available_from, address_must_contain list, address_must_not_contain list, include_recently_booked) ja AppConfig (city, filters, ntfy_topic, ntfy_server, db_path, user_agent, request_timeout_seconds). filters.matches(listing, f) palauttaa tuple[bool, str] — kaikki ehdot AND, address_must_contain passaa jos ANY substring case-insensitive löytyy titlesta, address_must_not_contain hylkää jos ANY match, skipataan None-kentät. Kirjoita tests/test_filters.py vähintään 3 testillä (pass, reject-by-price, reject-by-recently-booked). Acceptance: pytest vihreä.

- [ ] 3. Luo storage.py: sqlite3 stdlibillä, luo parent dir db_pathille automaattisesti, taulu seen_listings (slug TEXT PRIMARY KEY, first_seen_at TEXT, last_seen_at TEXT, notified_at TEXT nullable, payload_json TEXT). API: mark_seen(listing) palauttaa True jos uusi + upsert first/last_seen_at, mark_notified(slug) asettaa notified_at, was_notified(slug) palauttaa bool. Kirjoita tests/test_storage.py käyttäen tmp_pathia tai :memory: -kantaa, 3 testiä: insert-new-returns-true, insert-same-returns-false, mark-notified-persists. Acceptance: pytest vihreä.

- [ ] 4. Luo scraper.py fixture-pohjaisesti: input tests/fixtures/trento_sample.html (jo olemassa, ÄLÄ hae uudelleen). Strategia 1 preferoitu: etsi `<script id=__NEXT_DATA__ type=application/json>`, parsi JSON, inspektoi rakenne ja mappaa listingit Listing-malliin. Strategia 2 fallback: selectolax HTML-parse, hrefit muotoa `/en/rent-single-room-trento-*/tn-\d{4}-\d{2}-[a-z]/`, poimi per kortti slug (urlin viimeinen segmentti), url, title (h2), size_sqm (regex `(\d+(?:\.\d+)?)\s*m²`), price_eur (regex `€\s*(\d+)`), available_from (From DD Mon YYYY -> date) TAI recently_booked=True jos teksti Recently Booked, image_url (1. img src). Yksittäisen kortin parse-virhe EI saa kaataa ajoa — logita warning ja palauta Listing nullikentillä. Kirjoita tests/test_scraper.py jossa fixturesta pitää tulla vähintään 5 Listingiä, kaikilla slug-muotoa `tn-\d{4}-\d{2}-[a-z]`, vähintään yksi recently_booked=True. Ehdoton kielto: älä tee httpx.get-kutsua Joivyn live-URLiin scraperin testeissä tai validoinnissa. Acceptance: pytest vihreä.

- [ ] 5. Luo notifier.py ja cli.py: notifier.send_notification(config, listing) POSTaa ntfy-serverille headerein Title=listing.title, Click=listing.url, Priority=high, Tags=house, Attach=image_url jos olemassa. Body: €{price}/mo · {size} m² · from {available_from} (tai booked jos recently_booked) + osoite jos saatavilla. httpx-timeout 10s, raise non-2xx. config.py lataa config.yaml (oletus ./config.yaml, override env-muuttujalla ROOM_SCOUT_CONFIG) ja mergeaa .env:stä NTFY_TOPIC joka on REQUIRED. cli.py click-komennoilla run-once ja test-notify: run-once hakee listingit, jokaiselle mark_seen, jos uusi JA matches() niin send_notification + mark_notified, tulostaa yhteenvedon Found N, M new, K matched, K notified; test-notify lähettää yhden kovakoodatun testi-ilmoituksen varmistukseksi. Kirjoita tests/test_notifier.py joka mockaa httpx.post ja assertoi oikeat headerit ja body-sisällön. Kielto: testit eivät saa tehdä oikeita verkkokutsuja. Acceptance: pytest vihreä.

- [ ] 6. Luo README.md ja siivous: README sisältää mitä tekee (2 lausetta), quick start (venv, install, ntfy-app, config.yaml, .env, test-notify, run-once), filtterit lyhyesti, data-polut (SQLite poistettavissa reset-varten), known limitations (parse best-effort, ei vielä ajastusta). Lisää yksirivinen docstring jokaisen src/room_scout/-moduulin alkuun. Acceptance: pytest vihreä ja `python -m py_compile src/room_scout/*.py` ilman virheitä.

## IHMISELLE (AutoRun ohittaa)

Live-validointi aamulla kun tehtävät 1–6 ovat valmiit:

- [ ] 7. Rekisteröi ntfy-topic: asenna ntfy-appi puhelimeen, valitse pitkä satunnainen topic-nimi (esim. `scout-x9k2m4n8p-trento`), tilaa topic appissa, aseta sama topic .env-tiedostoon NTFY_TOPIC-avaimelle, kopioi config.example.yaml config.yamliksi ja säädä filtterit, aja `room-scout test-notify` ja varmista push tulee alle 5 sekunnissa, aja `room-scout run-once` ja varmista että live-data tulee parsittua oikein (>=5 listingiä) ja matchit pushataan, aja run-once uudestaan ja varmista 0 pushia dedup-varmistuksena, inspektoi scraper.py:n docstringistä kumpi strategia voitti ja säädä parseria jos live-datassa eroja fixtureen nähden.

## Raporttipohja

Jokaisen tehtävän jälkeen Claude Code tulostaa raportin tarkalleen tässä muodossa:

TEHTY:
TULOS:
ONGELMAT:
MUUTETUT TIEDOSTOT:
SEURAAVA ASKEL:
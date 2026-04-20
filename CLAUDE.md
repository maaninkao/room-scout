# Room Scout

Notification service that monitors Joivy coliving listings (Trento) and
sends phone push via ntfy.sh when new rooms match user-defined filters.
No auto-messaging, no login, no transactions — pure observer + notifier.

## SEURAAVA TEHTÄVÄ

### [AUTORUN] 1. Skaffaa projekti
- Luo venv: `python -m venv .venv` ja aktivoi
- pyproject.toml: hatchling build backend, Python >=3.11
  - Runtime: httpx>=0.27, selectolax>=0.3.21, pydantic>=2.6,
    pyyaml>=6.0, python-dotenv>=1.0, click>=8.1
  - Dev extras: pytest>=8.0, pytest-asyncio>=0.23
  - Console script: `room-scout = room_scout.cli:main`
- src/room_scout/{__init__,__main__,cli,scraper,storage,filters,
  notifier,config,models}.py tyhjinä stubeina
- .env.example (vain `NTFY_TOPIC=CHANGE_ME_TO_LONG_RANDOM_STRING`)
- config.example.yaml (kaupunki trento, filtterit stubina)
- Acceptance: `pip install -e ".[dev]"` menee läpi venv:ssä,
  `room-scout --help` näyttää molemmat subkomennot (run-once, test-notify)

### [AUTORUN] 2. models.py + filters.py + testit
- Pydantic v2 mallit: Listing, FilterConfig, AppConfig
- filters.matches(listing, f) -> tuple[bool, str] (pass, reason_if_rejected)
- Kaikki ehdot AND. address_must_contain = ANY substring (case-insensitive)
  listing.title/addressissa passaa. address_must_not_contain = ANY match
  hylkää. Skip None-kentät.
- tests/test_filters.py: vähintään 3 testiä (pass, reject-by-price,
  reject-by-recently-booked)
- Acceptance: pytest vihreä

### [AUTORUN] 3. storage.py + testit
- sqlite3 stdlib, auto-create parent dir db_pathille
- Taulu seen_listings (slug PK, first_seen_at, last_seen_at,
  notified_at, payload_json)
- API: mark_seen(listing) -> bool (True jos uusi), mark_notified(slug),
  was_notified(slug) -> bool
- tests/test_storage.py: käytä :memory: tai tmp_path; testit:
  insert-new-returns-true, insert-same-returns-false, mark-notified-persists
- Acceptance: pytest vihreä

### [AUTORUN] 4. scraper.py fixture-pohjaisesti
- INPUT: tests/fixtures/trento_sample.html (jo olemassa, ÄLÄ HAE UUDELLEEN)
- Strategia 1 (preferred): etsi <script id="__NEXT_DATA__"
  type="application/json">, parsi JSON, inspektoi rakenne, mappaa
  listingit Listing-malliin. Jos JSON-struktuuria on vaikea lukea
  varmasti, dokumentoi mitä löydyt scraper.py:n docstringiin ja
  siirry strategiaan 2.
- Strategia 2 (fallback): selectolax HTML-parse. Hrefit muotoa
  /en/rent-single-room-trento-*/tn-\d{4}-\d{2}-[a-z]/. Poimi per kortti:
  slug (url-polun viimeinen segmentti), url, title (h2), size_sqm
  (regex `(\d+(?:\.\d+)?)\s*m²`), price_eur (regex `€\s*(\d+)`),
  available_from ("From DD Mon YYYY" -> date) TAI recently_booked=True
  jos teksti "Recently Booked", image_url (1. img src).
- Yksittäisen kortin parsimisvirhe EI saa kaataa koko ajoa: logita
  warning ja palauta Listing nullikentillä.
- tests/test_scraper.py: fixturesta pitää tulla >=5 Listingiä,
  kaikilla slug-formaatti `tn-\d{4}-\d{2}-[a-z]`, vähintään yksi
  recently_booked=True.
- Acceptance: pytest vihreä.
- KIELTO: ÄLÄ tee httpx.get -kutsua Joivyn live-URLiin missään
  scraperin testissä tai validoinnissa. Käytä aina fixturea.

### [AUTORUN] 5. notifier.py + cli.py mockilla
- notifier.send_notification(config, listing): POST ntfy-serverille
  headerit: Title, Click (listing.url), Priority=high, Tags=house,
  Attach (jos image_url). Body: "€{price}/mo · {size} m² · from
  {available_from}" + osoite jos saatavilla. httpx timeout 10s.
  Raise non-2xx.
- cli.py: click-komennot run-once ja test-notify. run-once =
  fetch_listings -> for each: mark_seen, jos uusi JA matches() ->
  send_notification + mark_notified. Tulosta: "Found N, M new,
  K matched, K notified".
- config.py: lataa config.yaml (default ./config.yaml,
  override ROOM_SCOUT_CONFIG env), merge .env:stä NTFY_TOPIC
  (REQUIRED).
- tests/test_notifier.py: mockaa httpx.post, assertoi oikeat
  headerit ja body. EI oikeita verkkokutsuja.
- Acceptance: pytest vihreä, grep -r "httpx.post" tests/ näyttää
  vain mock-käyttöä.

### [AUTORUN] 6. README + final polish
- README.md: mitä tekee (2 lausetta), quick start (venv, install,
  ntfy-appi, config, test-notify, run-once), filterit lyhyesti,
  data-polut, known limitations (parse best-effort, ei vielä
  ajastusta).
- Kaikki moduulit: yksirivinen docstring ylälaitaan.
- Acceptance: pytest vihreä, `python -m py_compile src/room_scout/*.py`
  ei virheitä.

### [HUMAN] 7. Live-validointi (aamulla)
- Asenna ntfy-appi puhelimeen, tilaa topic
- Täytä .env oikealla topicilla, kopioi config.example.yaml
  config.yamliksi, säädä filtterit
- `room-scout test-notify` -> push <5s
- `room-scout run-once` -> löytää live-listat, pushaa matchit
- `room-scout run-once` uudestaan -> 0 pushia (dedup)
- Inspektoi __NEXT_DATA__ -parserin toimivuus live-datalla, säädä
  tarvittaessa

## RAPORTTIPOHJA

### TEHTY
- ...

### TULOS
- ...

### ONGELMAT
- ...

### MUUTETUT TIEDOSTOT
- ...

### SEURAAVA ASKEL
- ...

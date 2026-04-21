# PROJECT_LOG.md — Room Scout

> Itsenäinen projektitiiviste. Päivitetty 2026-04-21.

---

## 1. TL;DR — yhden minuutin yhteenveto

Room Scout on Python-botti joka skannaa Joivy-coliving-sivuston Trenton
huonelistaukset joka 10. minuutti ja lähettää push-ilmoituksen puhelimeen
kun uusi kohde täsmää filttereihin. Botti pyörii GitHub Actionsin ilmaisella
cron-ajastuksella — ei palvelimia, ei kuukausimaksuja.

Projekti rakennettiin yhden yön aikana AutoRun Commander -työkalun avulla.
Ylläpitotyötä vaatii noin 30 sekuntia kuukaudessa (tarkista Actions-loki).
Jos Joivyn HTML muuttuu, scraper saattaa hajota — tarkistusohje luvussa 9.

---

## 2. Ongelma jota ratkaistaan

Ossin kaveri etsii vuokra-asuntoa Trentosta Joivyn coliving-sivustolta.
Uusia kohteita ilmestyy harvakseltaan ja ne menevät nopeasti. Joivyn oma
"House alert" -sähköposti-ilmoitus ei toiminut käytännössä: neljä sopivaa
kohdetta meni ohi ilman yhtään ilmoitusta.

Tarvittiin oma ratkaisu joka ilmoittaa alle 10 minuutissa ja suoraan
puhelimeen. Automaattista varausta ei haluttu — Joivy on booking-pohjainen
eikä tiedustelupohjainen, joten automaatti sitoutuisi taloudellisesti
käyttäjän puolesta ilman hyväksyntää.

---

## 3. Arkkitehtuuri lyhyesti

| Komponentti | Toteutus |
|-------------|----------|
| Kieli | Python 3.11+ |
| Fetch | httpx 0.27+ |
| HTML-parse | selectolax 0.3.21+ |
| Datamallit | Pydantic v2 |
| CLI | click 8.1+ |
| Dedup-tallennus | SQLite3 (stdlib) |
| Push-kanava | ntfy.sh (ilmainen) |
| Hosting | GitHub Actions, public repo |
| Ajastus | cron `*/10 * * * *` |
| Persistenssi | `data/seen.db` Actions-cachessa |

**Toimintaperiaate:** Jokainen Actions-ajo on tilaton (kertakäyttöinen Ubuntu-VM).
`data/seen.db` ladataan Actions-cachesta ajon alussa ja tallennetaan cacheen
lopussa — näin dedup toimii ajojen välillä ilman pysyvää palvelinta.

**Ei auto-booking-toimintoa.** Botti havaitsee ja notifioi. Push-ilmoituksesta
klikkaus vie Joivyn sivulle, jossa ihminen tekee päätöksen itse.

---

## 4. Päätökset ja miksi niin

- **GitHub Actions vs VPS** → 0 € kustannus, 10 min reagointiaika riittää
  tähän käyttöön. Nopeampaan reagointiin (< 60 s) tarvittaisiin VPS (ks. luku 12).

- **Julkinen repo** → GitHub antaa Actions-minuutit rajattomasti julkisille
  repoeille. Salaisuudet (NTFY_TOPIC, CONFIG_YAML) tallennetaan Secretseihin,
  ei koodiin.

- **Vain selectolax HTML-parse (Strategy B)** → Suunnitelmassa oli
  __NEXT_DATA__ JSON -strategia ensin, mutta scraper.py toteutettiin
  selectolax-pohjaisesti. DOM-parseri on haavoittuvampi HTML-muutoksille,
  mutta toimii nykyisellä Joivy-sivurakenteella hyvin.

- **Dedup SQLite + Actions cache** → Yksinkertaisin tapa saavuttaa
  muisti ajojen välillä ilman ulkoista palvelua. Cache voi joskus kadota
  (ks. luku 9) mutta seuraus on vain kaksoispush, ei datahäviö.

- **RFC 2047 Base64 -enkoodaus HTTP-headereille** → Joivyn kohde-otsikoissa
  on em-dash (`—`) ja muita ei-ASCII-merkkejä. httpx lähettää headerit
  ASCII:na, joten enkoodaus on pakollinen. Toteutettu `notifier.py`:n
  `_encode_header()`-funktiossa.

- **CONFIG_YAML-secret base64-enkoodattuna** → config.yaml sisältää
  filtterit jotka ovat paikallinen salaisuus, ei versioitavaa koodia.
  Base64-enkoodaus mahdollistaa monirivaisen YAML:n tallentamisen
  GitHub Secretsiin yhtenä merkkijonona.

---

## 5. Kansiorakenne ja tiedostojen rooli

```
room-scout/
├── .github/workflows/scout.yml    — GitHub Actions cron 10 min välein
├── .gitignore                     — estää .env, config.yaml, data/, reports.db
├── .env.example                   — NTFY_TOPIC=CHANGE_ME template
├── config.example.yaml            — filtterit ja ntfy-asetukset template
├── pyproject.toml                 — riippuvuudet + console script room-scout
├── README.md                      — quick start + deploy-ohje
├── PROJECT_LOG.md                 — tämä tiedosto
├── CLAUDE.md                      — AutoRun Commander -tehtäväkuvaukset
├── src/room_scout/
│   ├── models.py                  — Pydantic v2: Listing, FilterConfig, AppConfig
│   ├── config.py                  — lataa config.yaml + .env NTFY_TOPIC
│   ├── scraper.py                 — selectolax HTML-parse, palauttaa list[Listing]
│   ├── filters.py                 — matches(listing, f) -> (bool, reason)
│   ├── storage.py                 — SQLite: mark_seen, mark_notified, was_notified
│   ├── notifier.py                — httpx POST ntfy:lle RFC 2047 -enkoodauksella
│   └── cli.py                     — click: run-once, test-notify
└── tests/
    ├── fixtures/trento_sample.html — staattinen HTML-snapshot testejä varten
    ├── test_cli.py                 — 3 testiä (run-once retry-semantiikka)
    ├── test_filters.py             — 8 yksikkötestiä
    ├── test_notifier.py            — 4 testiä (httpx mock)
    ├── test_scraper.py             — 5 testiä (fixture-pohjaisia)
    ├── test_scraper_live.py        — 1 testi (fetch_live URL + UA mock)
    └── test_storage.py             — 3 testiä (tmp_path SQLite)
```

---

## 6. Tuotantotila — secrets ja konfig

Kaksi GitHub Secretia täytyy olla asetettuna (repo → Settings → Secrets and
variables → Actions):

**NTFY_TOPIC** — ntfy-topic-nimi (pitkä satunnainen merkkijono). Tallennettu
myös paikallisesti `.env`-tiedostoon. Sama topic tilataan ntfy-appista
puhelimelle (sekä Ossilla että kaverilla tarvittaessa).

**CONFIG_YAML** — base64-enkoodattu kopio paikallisesta `config.yaml`:sta.
Päivitetään aina kun filttereitä muutetaan:

```powershell
# Päivitä CONFIG_YAML-secret filtterien muokkaamisen jälkeen:
$b64 = [Convert]::ToBase64String(
    [System.IO.File]::ReadAllBytes((Join-Path $PWD "config.yaml")))
$b64 | gh secret set CONFIG_YAML
```

Muutokset astuvat voimaan seuraavan cron-ajon yhteydessä (max 10 min).

**Paikallinen config.yaml rakenne** (ks. `config.example.yaml`):

```yaml
city: trento

ntfy:
  server: https://ntfy.sh
  priority: high

filters:
  max_price_eur: null        # esim. 650
  min_price_eur: null
  min_size_sqm: null
  max_size_sqm: null
  earliest_available: null   # esim. "2025-06-01"
  latest_available: null
  address_must_contain: []   # esim. ["centro", "povo"]
  address_must_not_contain: []
  include_recently_booked: false

storage:
  db_path: data/seen.db
```

---

## 7. Kehityshistoria tiivistettynä

Rakennettu yhdessä yössä AutoRun Commander -työkalun avulla:

1. **Prep (käsin):** repo-alustus, `.gitignore`, fetch Joivy-HTML
   `tests/fixtures/trento_sample.html`-fixtureksi.

2. **AutoRun 6 tehtävää:**
   scaffold → models + filters → storage → scraper (selectolax) →
   notifier + cli → README. Commit `68d7c0d` — 20/20 testiä vihreänä.

3. **Unicode-bugi live-testissä:** `notifier.py`:n httpx kaatui
   em-dashiin (`—`) Joivyn otsikossa — ASCII-codec error. Korjattu
   RFC 2047 Base64 -enkoodauksella. Commit `2afca2b`.

4. **GitHub Actions -deploy:** `scout.yml`-workflow, secretit,
   seen.db-cache. Commit `0f15fcd`.

5. **Kaksi kolia deployssa:**
   - CONFIG_YAML meni ensin tyhjänä koska `$PWD` oli eri .NET-kontekstissa;
     korjattu `Join-Path $PWD "config.yaml"` -muodolla.
   - GitHub ei indeksoinut workflow'ta heti; kierto: tyhjä muutos
     `scout.yml`:ään pakotti re-indeksoinnin.

8. **Kriittinen bugi havaittu PROJECT_LOG-kirjoituksen yhteydessä**:
   cli.py:run-once kutsui scrape_fixture():a eikä live-fetchia.
   Tuotantobotti näki aina vain eilisen HTML-snapshotin. Korjattu
   lisäämällä scraper.fetch_live() joka httpx-GET:taa Joivyn live-
   URL:n oikealla User-Agentilla, ja vaihtamalla cli.py osoittamaan
   siihen. Mocked-testi tests/test_scraper_live.py varmistaa että
   oikea URL ja User-Agent lähtevät ilman että testi käy oikeasti
   verkossa.

9. **Audit paljasti HIGH-tason bugin "notification loss"** (2026-04-21):
   cli.py:run-once merkitsi kohteen `seen`-tilaan ennen push-yritystä.
   Jos ntfy-kutsu epäonnistui (verkkovirhe, palvelin alhaalla), kohde
   jäi "seen mutta ei notified" -tilaan. Seuraavalla ajolla `mark_seen`
   palautti False → `is_new=False` → ilmoitusta ei yritetty uudelleen.
   Ilmoitus menetettiin pysyvästi ja hiljaisesti.
   Lisäksi yksittäinen poikkeus kaatoi koko for-loopin, joten loopun
   jäljellä olevat kohteet jäivät kokonaan käsittelemättä.
   Korjattu commit `c1edce2`:
   - `mark_seen` + `mark_notified` kutsutaan vain onnistuneen pushin jälkeen
   - per-kohde `try/except` kirjoittaa ERROR-tason lokin ja jatkaa seuraavaan
   - virheet lokitetaan stack tracella (`exc_info=True`)
   - `run-once` tulostaa nyt `errors`-sarakkeen yhteenvedossa
   - 3 uutta testiä `tests/test_cli.py` varmistavat retry-semantiikan

---

## 8. Miten se toimii normaalissa käytössä

**Yhden GitHub Actions -ajon elinkaari:**

```
1. cron laukeaa */10 * * * *
2. Ubuntu-VM spinnaa, Python 3.11 asennetaan
3. config.yaml dekoodataan: echo "$CONFIG_YAML_B64" | base64 -d > config.yaml
4. data/seen.db palautetaan Actions-cachesta (tyhjä jos ensimmäinen ajo)
5. room-scout run-once:
   a. fetch_live(config) httpx-GET:taa Joivyn live-sivun oikealla User-Agentilla
   b. parse_html(resp.text) → list[Listing]
   c. mark_seen(listing) → True jos uusi slug
   d. jos uusi JA matches() → send_notification() + mark_notified()
   e. tulosta "Found N, M new, K matched, K notified"
6. seen.db tallennetaan cacheen seuraavaa ajoa varten
```

**Paikallinen testisykli:**

```powershell
cd C:\Projects\room-scout
.venv\Scripts\activate
room-scout test-notify        # varmistaa ntfy-yhteyden
room-scout run-once           # ajaa kerran, tulostaa Found/new/matched/notified
```

---

## 9. Vianetsintä — mitä tarkistaa kun jotain on rikki

### `errors > 0` ajon yhteenvedossa

Yksi tai useampi push kaatui (ntfy alhaalla, verkkovirhe, HTTP 4xx/5xx).
Kohteet pysyvät tilassa "seen mutta ei notified" — ne yritetään uudelleen
seuraavalla ajolla, koska `mark_seen` ja `mark_notified` kutsutaan vain
onnistuneen pushin jälkeen.

Tarkista mikä kohde ja virhe:

```powershell
gh run view <run-id> --log | Select-String -Pattern "ERROR|failed"
```

Jos ntfy on jatkuvasti alhaalla, harkitse `test-notify`-komennon ajamista
paikallisesti ennen seuraavaa tuotantoajoa.

### Puhelimeen ei tule mitään

Tarkista ensin Actions-loki:

```powershell
gh run list --workflow=scout.yml --limit 10
gh run view <run-id> --log
```

Yleisin syy nykyisellä arkkitehtuurilla: scraper lukee aina samaa
`trento_sample.html`-fixturea — kaikki slugit on jo nähty, `0 new`.
Toimiakseen oikeasti live-datalla botti tarvitsee live-fetchin (ks. yllä).

### Puhelimeen tulee liikaa pusheja (sama kohde useasti)

Actions-cache ei persistoi kunnolla. Tarkista `gh run view <id> --log`
ja etsi `Restore seen.db cache` -vaihe. Jos lukee "Cache not found",
cache-avain on vaihtunut. Tarkista `scout.yml`:n `key:` ja `restore-keys:`.

### GitHub Actions -ajo punaisena

```powershell
gh run list --limit 10
gh run view <run-id> --log
```

Yleisin syy: Joivy 403 tai HTML-muutos scraperissa (jos live-fetch lisätty).

### Ntfy-push ei tule vaikka botti raportoi notifoineensa

- Varmista että topic-nimi on täsmälleen sama `.env`:ssä ja ntfy-appissa
- Android: poista appi akun säästötilasta (Asetukset → Akku → Ei optimoitu)
- Tarkista ilmoitusoikeudet puhelimesta

### Unicode-crash `'ascii' codec can't encode`

RFC 2047 -enkoodaus `notifier.py`:ssä on rikki. Testi
`test_send_notification_headers_and_body` pitäisi havaita tämä.

```powershell
pytest tests/test_notifier.py -v
```

### Fixture-päivitys (Joivyn HTML muuttui)

```powershell
cd C:\Projects\room-scout
curl.exe -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36" `
  "https://coliving.joivy.com/en/rent-room-trento/" `
  -o tests\fixtures\trento_sample.html
.venv\Scripts\activate
pytest tests/test_scraper.py -v
```

Jos testit feilaavat, päivitä `scraper.py`:n regex-kaavat vastaamaan
uutta HTML-rakennetta.

### Fiksaamisen perusrutiini

```powershell
# 1. Korjaa koodi
# 2. Aja testit
pytest -v
# 3. Committaa
git commit -am "fix: kuvaava viesti"
git push
# → GitHub ottaa muutoksen käyttöön seuraavalla cron-ajolla
```

---

## 10. Kuukausittainen tarkistusrutiini (30 s)

```powershell
cd C:\Projects\room-scout
gh run list --workflow=scout.yml --limit 10
```

Jos kaikissa ✓ (success) → kaikki kunnossa. GitHub lähettää
sähköpostia automaattisesti jos workflow feilaantuu (oletusasetus).

---

## 11. Jos projekti halutaan siirtää kaverille

**Kevyt siirto (nykytila):** kaveri tilaa saman ntfy-topicin omaan
puhelimeensa. Ossi säilyy ylläpitäjänä. Ei koodimuutoksia.

**Täysi siirto:** kaveri forkkaa repon omalle GitHub-tililleen, asettaa
omat `NTFY_TOPIC`- ja `CONFIG_YAML`-secretit repo-asetuksiin, ja workflow
ajaa hänen tilillään. Ossi voi sulkea oman repon tai jättää sen pystyyn.

```
Kaverille annettavat ohjeet täyteen siirtoon:
1. Fork https://github.com/maaninkao/room-scout
2. Settings → Secrets → NTFY_TOPIC = oma topic
3. Luo config.yaml, enkoodaa: base64, aseta CONFIG_YAML-secret
4. Actions-välilehti → Enable workflows
5. Aja workflow_dispatch käsin → tarkista loki
```

---

## 12. Mahdollisia parannuksia (ei pakollisia)

- **Health-check-push** — jos scraper löytää 0 kohdetta tai yli 30,
  lähetä erillinen hälytys. Kertoisi automaattisesti parse-viasta.

- **Nopeampi reagointi (< 60 s)** — siirto Hetzner-VPS:lle (3 €/kk) tai
  Oraclen ilmais-VPS:lle. GitHub-cronin jitter on 1–10 min.

- **Useampi kaupunki** — muuta `config.yaml`:n `city` listaksi, scraper
  fetchaisi useammasta URL:sta, filtterit per kaupunki.

- **Filtteri-tuning UI** — pieni web-form joka muokkaa `config.yaml`:ia ja
  committaa sen automaattisesti GitHubiin. Helpottaisi kaverin itsenäistä
  käyttöä ilman komentoriviä.

---

## 13. Oleelliset linkit

- Repo: https://github.com/maaninkao/room-scout
- Joivy-sivu: https://coliving.joivy.com/en/rent-room-trento/
- ntfy-dokumentaatio: https://docs.ntfy.sh/
- ntfy mobile-appit: https://ntfy.sh/docs/subscribe/phone/
- GitHub Actions ajolistaus: Actions-välilehti repossa

---

## 14. Testit ja hyväksyntäkriteerit

Kaikki 24 yksikkötestiä kulkevat ilman live-verkkokutsuja:

```powershell
cd C:\Projects\room-scout
.venv\Scripts\activate
pytest -v
```

Odotettu tulos:

```
tests/test_cli.py           3 passed
tests/test_filters.py       8 passed
tests/test_notifier.py      4 passed
tests/test_scraper.py       5 passed
tests/test_scraper_live.py  1 passed
tests/test_storage.py       3 passed
==================== 24 passed ====================
```

**Testisäännöt (CLAUDE.md:stä):**
- Scraper käyttää `tests/fixtures/trento_sample.html` — ei live-URLia
- httpx mockataan notifier-testeissä — ei oikeita ntfy-kutsuja
- Jokainen moduuli saa pytest-testit
- UTF-8 ilman BOM:ia kaikissa tekstitiedostoissa
- Yksittäisen kortin parse-virhe ei kaada ajoa — logita warning ja jatka

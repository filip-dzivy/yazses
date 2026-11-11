# DevOps v projekte YazSes

| Údaj | Hodnota |
|---|---|
| Projekt | YazSes, offline hlasové diktovanie (Linux, macOS, Windows), Python 3.11+ |
| Pôvodný repozitár | `github.com/MSKazemi/yazses` |
| Môj fork | `github.com/filip-dzivy/yazses` |
| Skúmaná verzia | 2.43.2 (commit `9afb8aa9`) |

## 1. Kde sú DevOps nastavenia uložené

Takmer všetko súvisiace s DevOps je v priečinku `.github/`. Zvyšok tvoria konfigurácie
balíčkov v koreni repozitára a v `packaging/`.

**Priečinok `.github/`**

- `workflows/`: 33 YAML súborov pre **GitHub Actions**. Toto je jadro celej CI/CD.
- `dependabot.yml`: nastavenie **Dependabota** (automatické aktualizácie knižníc).
- `codeql/codeql-config.yml`: konfigurácia **CodeQL** (hľadanie bezpečnostných chýb v kóde).
- `labeler.yml`: pravidlá, podľa ktorých dostane pull request štítky.
- `release.yml`: ako sa majú triediť automaticky generované poznámky k vydaniu (**GitHub Releases**).
- `ISSUE_TEMPLATE/`, `DISCUSSION_TEMPLATE/`, `PULL_REQUEST_TEMPLATE.md`: formuláre pre hlásenia, diskusie a PR.
- `CODEOWNERS`: kto musí schváliť zmeny v ktorej časti kódu.
- `CI_POLICY.md`: písané pravidlá, ako sa má CI/CD správať.

**Koreň repozitára a ďalšie priečinky**

- `.devcontainer/`: definícia vývojového kontajnera (**GitHub Codespaces / VS Code Dev Containers**).
- `pyproject.toml` + `uv.lock`: závislosti so zamknutými verziami (**uv**), nastavenia ruff, mypy a pytest.
- `mkdocs.yml`: dokumentačný web (**MkDocs Material**, nasadzovaný na **GitHub Pages**).
- `sbom.cdx.json`: súpis všetkých závislostí vo formáte **CycloneDX** (SBOM).
- `flake.nix` / `flake.lock`: reprodukovateľný build cez **Nix**.
- `snap/snapcraft.yaml`, `debian/`, `packaging/…` (docker, winget, chocolatey, scoop, homebrew,
  arch, flatpak, fedora, store…): recepty pre jednotlivé distribučné kanály.
- `.all-contributorsrc`: zoznam prispievateľov, ktorý nástroj **all-contributors** vypisuje do README.
- `fuzz/`, `android/`: fuzzing harness (**Atheris**) a Android aplikácia (**Gradle**). Obe spúšťa CI.
- `.editorconfig`, `.gitattributes`, `Makefile`: jednotný štýl a lokálne príkazy, nie samostatné služby.

V repozitári nie je konfigurácia žiadnej inej CI platformy (Travis, CircleCI, Jenkins,
GitLab CI, Azure Pipelines). Chýbajú aj služby na meranie pokrytia testami (Codecov,
Coveralls) a na zber chýb z produkcie (napr. Sentry).

## 2. Priebežná integrácia (build a test)

### Hlavný pipeline: `test.yml`

Spúšťa sa automaticky pri každom pushi na vetvu `main` a pri každom pull requeste do nej.
Postupne prebehne:

1. **Hygiena repozitára:** zastaví sa, ak niekto pridal príliš veľký súbor alebo ak
   preložené README nezodpovedajú anglickému originálu.
2. **Lint a závislosti:** `ruff check` a kontrola, či sa neprekročil „rozpočet“ veľkosti závislostí.
3. **Testy (pytest) v matici:** Ubuntu, macOS aj Windows s Pythonom 3.11 a 3.12. Na Ubuntu
   navyše 3.13 a 3.14 a jeden beh na ARM stroji (`ubuntu-24.04-arm`).
4. **GUI testy:** Qt časti (overlay, ikona v lište, okno nastavení) na Ubuntu a Windows.
5. **Doplnkové joby:** testy s voliteľnými knižnicami (`extras`), beh bez rozpoznávača reči,
   ktorý napodobňuje prostredie FreeBSD (`freebsd`), a kontrola benchmark skriptov
   (`benchmark-harness`).

### Platformové buildy pri pull requestoch

| Workflow | Čo overuje |
|---|---|
| `build-windows.yml` | zostaví inštalátor `.exe` (PyInstaller + Inno Setup) |
| `build-macos.yml`, `macos-smoke.yml` | zostaví `.app` / `.dmg` a vyskúša, že aplikácia naštartuje a vypíše verziu |
| `msix-validate.yml` | zabalí balík pre Microsoft Store. Zámerne zlyhá, ak v manifeste zostal zástupný text. |
| `flatpak.yml` | pregeneruje Python závislosti pre Flatpak, skontroluje, či sú commitnuté, a balík zostaví |
| `android-test.yml` | Gradle build Android aplikácie: architektonické pravidlá, kontroly súkromia, unit testy a lint |
| `gradle-wrapper.yml` | overí pravosť súboru `gradle-wrapper.jar` |
| `eye-eval-ci.yml` | vyhodnotí ovládanie očami bez hardvéru na viacerých OS. Prejde, iba ak má platný výsledok každý OS. |
| `docs.yml` | zostaví dokumentáciu v prísnom režime (`--strict`), takže pokazený odkaz zastaví build |

Vďaka tomu sa chyba v balení pre konkrétnu platformu ukáže už v pull requeste, a nie až pri
vydaní.

### Pravidlá pre samotné CI

Súbor `.github/CI_POLICY.md` delí workflowy do piatich skupín: rýchla kontrola PR, plná
validácia, platformové buildy, plánované kontroly a vydávanie. Každý workflow spúšťaný z PR
musí mať nastavenú `concurrency`, aby nový push do toho istého PR zrušil starý, už zbytočný
beh. Že to platí pre všetky workflowy, stráži test `tests/test_workflow_concurrency.py`.

Vývojár spúšťa tie isté kontroly aj lokálne: `uv run python -m pytest tests/`,
`uv run ruff check …`, `uv run mypy src`, prípadne všetko naraz cez `make check`.

## 3. Bezpečnosť a závislosti

- **CodeQL** (`codeql.yml`) analyzuje kód pri pushi a PR do `main` a navyše raz týždenne.
- **Dependency Review** (`dependency-review.yml`) v PR zastaví pridanie knižnice so známou zraniteľnosťou.
- **Dependabot** raz mesačne pripraví zoskupené PR s novými verziami pre tri oblasti: Python
  balíčky (uv), GitHub Actions a Docker. Naraz otvorí najviac 5 PR, všetky s prefixom `chore(deps)`.
- **Obnova SBOM** (`dependabot-sbom.yml`): keď Dependabot zmení `uv.lock`, workflow znovu
  vygeneruje `sbom.cdx.json` a pridá ho do toho istého PR.
- **OpenSSF Scorecard** (`scorecard.yml`) týždenne hodnotí bezpečnostné návyky repozitára
  a výsledky posiela do GitHub Code Scanning.
- **Fuzzing cez Atheris** (`fuzz.yml`) raz týždenne skúša náhodné vstupy na ceste od
  rozpoznávača reči po klávesnicu a v načítaní konfigurácie. Vstup, ktorý spôsobil pád,
  uloží ako artefakt.
- **Pripnuté akcie:** každá použitá GitHub akcia je zadaná cez SHA commitu, nie cez tag,
  ktorý sa dá prepísať. Dodržiavanie kontroluje skript `scripts/check-action-pins.py`.
- **Zákaz sieťovej komunikácie:** test `tests/test_egress_inventory.py` zastaví build, ak
  sa v kóde objaví sieťové volanie, ktoré nie je schválené v ADR-019.

## 4. Vydávanie verzií a nasadenie (release + CD)

YazSes je desktopová aplikácia, takže „nasadenie“ neznamená nahratie na server, ale
zverejnenie v obchodoch a repozitároch balíčkov, z ktorých si ho ľudia inštalujú. Celý
proces štartuje jediný krok: správca pushne tag v tvare `v*`, napríklad `v2.43.2`.

**Čo nasleduje po pushi tagu:**

1. `release.yml` znovu spustí testy. Potom zostaví wheel a sdist a nahrá ich na **PyPI**
   cez *trusted publishing* (prihlásenie cez OIDC, bez uloženého hesla) spolu
   s attestáciami podľa PEP 740.
2. Ten istý workflow zostaví balíky `.deb` pre viac architektúr, ku každému vydá potvrdenie
   pôvodu (build provenance) a vytvorí **GitHub Release** s prílohami.
3. Po úspešnom Release sa spustí `apt-repo.yml` (cez `workflow_run`). Stiahne `.deb`,
   podpíše **APT repozitár** kľúčom GPG a zverejní ho na **GitHub Pages**.
4. Paralelne bežia:
    - `build-windows.yml`: inštalátor `.exe`, podpísaný službou **SignPath**,
    - `build-macos.yml`: `.dmg`, podpísaný certifikátom Developer ID a **notarizovaný u Apple**,
    - `snap.yml`: balík do **Snap Store**,
    - `ppa.yml`: zdrojový balík do **Launchpad PPA** pre Ubuntu,
    - `docker.yml`: obraz pre amd64 a arm64 do **GitHub Container Registry**. Počká, kým
      je nová verzia dostupná na PyPI.
5. `publish-channels.yml` počká na hotové inštalátory a odošle nové verzie do **winget**
   (PR do `microsoft/winget-pkgs`), **Chocolatey**, **Homebrew** (cask v tape) a **AUR**.
6. `checksums.yml` pripojí k vydaniu `SHA256SUMS.txt` a overí, že kontrolné súčty sedia
   s prílohami.
7. `release-complete.yml` na záver skontroluje, či je verzia naozaj v každom kanáli
   a každý artefakt má attestáciu. Ak niečo chýba, vydanie stratí označenie „Latest“.

Poznámky k vydaniu vytvára GitHub automaticky zo zlúčených PR. Podľa `.github/release.yml`
ich roztriedi podľa štítkov (Features, Fixes, Android, Packaging…) a PR od Dependabota
vynechá.

Popri vydaniach sa aj pri každom pushi na `main` automaticky nasadzuje dokumentačný web
(`docs.yml`, **GitHub Pages**). Pred nasadením sa skontroluje, že do webu neunikol žiadny
súkromný súbor.

## 5. Monitoring

Klasický monitoring bežiacej aplikácie tu chýba úmyselne. Prvé pravidlo projektu znie
„nič neopustí počítač používateľa“, takže aplikácia nemá telemetriu, analytiku ani
automatické hlásenie pádov. Projekt namiesto toho sleduje stav distribúcie, závislostí
a dokumentácie cez naplánované behy GitHub Actions:

| Kedy | Workflow | Na čo dáva pozor |
|---|---|---|
| denne | `channel-drift.yml` | či je posledné vydanie dostupné všade (PyPI, Snap, winget…) |
| denne | `traceability.yml` | či issues a míľniky na GitHube zodpovedajú plánu v `design/traceability.yml` |
| týždenne | `link-check.yml` | odkazy v dokumentácii, ktoré už nefungujú |
| týždenne | `heavy-extras.yml` | či sa dajú stále nainštalovať veľké voliteľné knižnice (pyannote, resemblyzer) |
| týždenne | `scorecard.yml`, `codeql.yml`, `fuzz.yml` | bezpečnostné skóre, nové nálezy v kóde, nové pády |
| týždenne | `attribution.yml` | či je každý autor zlúčeného PR uvedený medzi prispievateľmi |
| pri vydaní | `release-complete.yml` | úplnosť vydania naprieč kanálmi |
| na požiadanie | `benchmark.yml` | presnosť rozpoznávania a latencia, výsledky ukladá do `paper/results/` |

Informácie o problémoch u používateľov prichádzajú cez **GitHub Issues**. Na to slúžia
špeciálne formuláre, napr. pre hlásenie Android zariadenia alebo zariadenia na sledovanie
očí, a výstup príkazu `yazses doctor`, ktorý si používateľ spustí sám.

## 6. Plánovanie a spolupráca

- **Formuláre pre issues:** deväť typov (chyba, nová funkcia, hlásenie zariadenia, úloha
  pre AI agenta…). Každý vyžaduje údaje potrebné na riešenie, napr. OS a verziu.
- **Automatické štítky** (`labeler.yml`) podľa zmenených ciest. Štítky potom určujú, kam
  zmena patrí v poznámkach k vydaniu.
- **Privítanie nováčikov** (`first-interaction.yml`) pri ich prvom issue alebo PR.
- **Kontroly pred začatím práce** (`campaign-preflight.yml`, `jules-issue-preflight.yml`):
  overia, či PR alebo zadanie pre AI agenta nezasahuje mimo povoleného rozsahu.
- **CODEOWNERS** automaticky priradí revízora podľa toho, ktoré súbory sa menia.
- **Codespaces / Dev Containers:** kontajner s Pythonom 3.12, `uv` a závislosťami.
  Testy aj dokumentácia v ňom fungujú hneď, bez lokálnej inštalácie.

## 7. Prehľad podľa fáz DevOps

| Fáza | Čo projekt používa |
|---|---|
| Plánovanie | GitHub Issues s formulármi, Discussions, traceability audit, automatické štítky |
| Vývoj | GitHub, šablóna PR, CODEOWNERS, Codespaces / Dev Containers |
| Build | GitHub Actions; uv, PyInstaller, Inno Setup, create-dmg, Snapcraft, Docker Buildx, Gradle, Flatpak |
| Test | pytest na 3 OS a viacerých verziách Pythonu, ruff, mypy, CodeQL, Dependency Review, fuzzing, smoke testy inštalátorov |
| Vydanie | tag `v*`, GitHub Releases, SignPath, notarizácia Apple, attestácie, SHA256SUMS |
| Nasadenie | PyPI, APT (GitHub Pages), Launchpad PPA, Snap Store, GHCR, winget, Chocolatey, Homebrew, AUR; web dokumentácie |
| Monitoring | plánované kontroly kanálov, odkazov, závislostí a bezpečnosti; bez telemetrie |
| Údržba | Dependabot, automatická obnova SBOM |

## 8. Môj fork

Workflowy sú obyčajné súbory v repozitári, takže ich fork `filip-dzivy/yazses` obsahuje
tiež. GitHub ich však vo forku sám od seba nespúšťa. Najprv treba zapnúť Actions
v nastaveniach forku (karta *Actions*). Potom budú testy, CodeQL a build dokumentácie bežať
pri pushi a PR do `main` aj vo forku. Workflowy na zverejňovanie (PyPI, Snap, winget,
podpisovanie) potrebujú tajné kľúče, ktoré má iba autor pôvodného projektu. Vo forku sa
preto preskočia alebo skončia chybou a nič nezverejnia.

## 9. Záver

YazSes používa DevOps vo veľkej miere, no stavia na jedinej platforme, **GitHub Actions**,
v ktorej má 33 workflowov. Tie pokrývajú celý cyklus: testovanie na troch operačných
systémoch, kontrolu bezpečnosti a závislostí, plne automatické vydanie do viac ako desiatich
distribučných kanálov po pushi jedného tagu a pravidelné kontroly, či je všetko zverejnené
správne. Pripájať ďalšiu CI službu nebolo potrebné.

# DevOps v projekte YazSes

Cvičenie: zistiť, či je projekt prepojený so službami a nástrojmi na priebežnú integráciu
(CI), správu vydávania verzií (release management), priebežné nasadzovanie (CD),
priebežný monitoring a podobne. Pre každú službu uvádzam **názov** a **ktorú fázu vývoja
podporuje a ako konkrétne v tomto projekte**.

- Projekt: YazSes, offline diktovanie hlasom pre Linux, macOS a Windows (Python 3.11+)
- Upstream: `github.com/MSKazemi/yazses`
- Môj fork: `github.com/filip-dzivy/yazses`
- Stav repozitára: verzia 2.43.2, commit `9afb8aa9`

## 1. Postup

1. Prešiel som súbory a priečinky v koreni projektu, hlavne skryté (začínajú bodkou)
   a súbory s koncovkou `.yml`, `.yaml` a `.json`.
2. Prečítal som všetky workflowy v `.github/workflows/` (33 súborov), z každého jeho
   spúšťač (`on:`) a hlavné kroky.
3. Prečítal som dokument `.github/CI_POLICY.md`, ktorý opisuje pravidlá CI/CD projektu,
   a `AGENTS.md` / `CONTRIBUTING.md`, ktoré opisujú brány kvality.

## 2. Nájdené „zaujímavé" súbory

| Súbor / priečinok | Čo to je | Služba / nástroj |
|---|---|---|
| `.github/workflows/*.yml` (33 súborov) | CI/CD pipeline | **GitHub Actions** |
| `.github/dependabot.yml` | automatické aktualizácie závislostí | **Dependabot** |
| `.github/codeql/codeql-config.yml` | statická bezpečnostná analýza | **GitHub CodeQL** |
| `.github/labeler.yml` | automatické štítky na PR podľa zmenených súborov | **actions/labeler** |
| `.github/release.yml` | kategórie automatických poznámok k vydaniu | **GitHub Releases** |
| `.github/ISSUE_TEMPLATE/*.yml`, `PULL_REQUEST_TEMPLATE.md`, `DISCUSSION_TEMPLATE/` | štruktúrované hlásenia a PR | **GitHub Issues / Discussions** |
| `.github/CODEOWNERS` | povinný revízor podľa cesty | **GitHub code review** |
| `.devcontainer/devcontainer.json` | hotové vývojové prostredie | **GitHub Codespaces / Dev Containers** |
| `.all-contributorsrc` | zoznam prispievateľov v README | **all-contributors** |
| `.editorconfig`, `.gitattributes`, `.gitignore` | jednotné formátovanie a konce riadkov | (konvencie, nie služba) |
| `pyproject.toml`, `uv.lock` | závislosti, zamknuté verzie, nastavenie ruff/mypy/pytest | **uv**, ruff, mypy, pytest |
| `Makefile` | lokálne skratky (`make check`, `make docs`, `make man`) | (lokálna automatizácia) |
| `mkdocs.yml` | dokumentačný web | **MkDocs Material + GitHub Pages** |
| `sbom.cdx.json` | zoznam všetkých závislostí (SBOM) | **CycloneDX** |
| `packaging/docker/Dockerfile` | kontajnerový obraz | **Docker / GHCR** |
| `snap/snapcraft.yaml` | balík pre Snap Store | **Snapcraft** |
| `debian/` | balík `.deb` | **APT repozitár, Launchpad PPA** |
| `packaging/{winget,chocolatey,scoop,homebrew,arch,flatpak,nix,fedora,windows,macos,store}` | manifesty pre správcov balíčkov | **winget, Chocolatey, Scoop, Homebrew, AUR, Flathub, Nix…** |
| `flake.nix`, `flake.lock` | reprodukovateľný build | **Nix** |
| `fuzz/` | fuzzing harness | **Atheris** (beží v GitHub Actions) |
| `android/` (Gradle) | Android aplikácia | **Gradle** (beží v GitHub Actions) |

Projekt **nepoužíva** externé CI služby ako Travis CI, CircleCI, Jenkins, GitLab CI
ani Azure Pipelines. Všetko beží na **GitHub Actions**. Nepoužíva ani služby na pokrytie
kódu (Codecov, Coveralls) ani runtime monitoring (Sentry a pod.), pozri časť 7.

## 3. Fáza PLAN / CODE: plánovanie a vývoj

| Služba | Ako ju projekt používa |
|---|---|
| **GitHub Issues + šablóny** (`.github/ISSUE_TEMPLATE/`) | 9 typov hlásení (bug, feature, report zariadenia, „agent task" atď.). Šablóny vynútia potrebné údaje, napr. OS a verziu. |
| **GitHub Discussions** (`DISCUSSION_TEMPLATE/`) | otázky a nápady mimo issue trackera |
| **Live traceability audit** (`traceability.yml`, denne cron `41 5 * * *`) | kontroluje, či issues a míľniky na GitHube zodpovedajú súboru `design/traceability.yml`, teda či plán a skutočný stav nie sú v rozpore |
| **actions/labeler** (`labeler.yml`) | každému PR automaticky pridá štítky podľa zmenených ciest (napr. `android`, `packaging`). Tie potom určujú kategóriu v poznámkach k vydaniu. |
| **first-interaction** (`first-interaction.yml`) | automaticky privíta nového prispievateľa pri jeho prvom issue alebo PR |
| **Campaign preflight** (`campaign-preflight.yml`), **Jules issue preflight** | kontrolujú, či PR alebo úloha pre AI agenta spĺňa pravidlá projektu (rozsah, zmenené cesty) |
| **GitHub Codespaces / Dev Containers** (`.devcontainer/`) | jedným klikom vytvorí kontajner s Pythonom 3.12, `uv` a nainštalovanými závislosťami. Testy, lint a docs v ňom fungujú bez lokálnej inštalácie. |
| **CODEOWNERS** | GitHub automaticky pridá správneho revízora podľa zmenených súborov |

## 4. Fáza BUILD + TEST: priebežná integrácia (CI)

Hlavný CI workflow je **`test.yml` (GitHub Actions)**, spúšťa sa pri každom `push` na
`main` a pri každom pull requeste do `main`. Má tieto joby:

| Job | Čo konkrétne robí |
|---|---|
| `repo-hygiene` | odmietne príliš veľké súbory a skontroluje, či sa preklady README nerozišli so zdrojom |
| `test` (matica) | **ruff** (lint), kontrola „rozpočtu" závislostí, potom **pytest** na **Ubuntu, macOS a Windows** × Python 3.11 a 3.12, navyše Python 3.13 a 3.14 na Ubuntu a ARM runner `ubuntu-24.04-arm` |
| `gui` | testy Qt rozhrania (overlay, tray, nastavenia) na Ubuntu a Windows |
| `extras` | testy s voliteľnými závislosťami |
| `freebsd` | sada bez dekodéra (simulovaná FreeBSD sada závislostí) |
| `benchmark-harness` | overí, že benchmark skripty v `paper/benchmark/` fungujú |

Ďalšie CI workflowy pre konkrétne platformy:

| Workflow | Fáza | Ako |
|---|---|---|
| `android-test.yml` | build + test | Gradle: architektonické pravidlá, „privacy gates", unit testy a lint Android aplikácie |
| `gradle-wrapper.yml` | build (bezpečnosť) | overí, že `gradle-wrapper.jar` nie je podvrhnutý |
| `macos-smoke.yml` | build + test | na PR zostaví `.app` a skontroluje, že sa spustí a vie vypísať svoju verziu |
| `build-macos.yml` / `build-windows.yml` | build | na PR zostaví inštalátory `.dmg` a `.exe`, takže chyba v balení sa ukáže už pred vydaním |
| `msix-validate.yml` | build | zabalí MSIX balík (Microsoft Store) s dočasnou identitou a overí, že zostavenie zlyhá, ak v manifeste ostal zástupný text |
| `flatpak.yml` | build | pregeneruje Python moduly pre Flatpak, overí, že sú commitnuté, a zostaví Flatpak |
| `eye-control-eval` (`eye-eval-ci.yml`) | test | vyhodnotenie ovládania očami (bez hardvéru) na viacerých OS a záverečný job, ktorý vyžaduje platný výsledok z každého OS |
| `docs.yml` | build + test | `mkdocs build --strict`, teda každý nefunkčný odkaz v dokumentácii zastaví build |

**Lokálne brány** (rovnaké ako v CI): `uv run python -m pytest tests/`, `uv run ruff check …`,
`uv run mypy src` a `make check`. Pravidlá sú opísané v `AGENTS.md`: ruff a pytest musia
byť zelené.

**Ako CI riadi spotrebu runnerov** (`CI_POLICY.md`): workflowy sú rozdelené do 5 „pruhov"
(rýchla PR brána, plná validácia, platformové, plánované, release). Každý workflow
spúšťaný pull requestom musí mať nastavené `concurrency`, aby novší commit v tom istom PR
zrušil starý beh. Toto pravidlo stráži test `tests/test_workflow_concurrency.py`.

## 5. Bezpečnosť v pipeline (DevSecOps)

| Služba | Fáza | Ako |
|---|---|---|
| **GitHub CodeQL** (`codeql.yml`) | test / security | statická analýza kódu na každý push a PR do `main` a navyše raz týždenne (cron) |
| **Dependency Review** (`dependency-review.yml`) | test / security | na PR zablokuje pridanie závislosti so známou zraniteľnosťou |
| **Dependabot** (`dependabot.yml`) | údržba | raz mesačne otvorí zoskupené PR s aktualizáciami pre tri ekosystémy: uv (Python), GitHub Actions a Docker, najviac 5 naraz, s prefixom `chore(deps)` |
| **Dependabot SBOM refresh** (`dependabot-sbom.yml`) | build | keď Dependabot zmení `uv.lock`, workflow pregeneruje `sbom.cdx.json` (CycloneDX) a commitne ho do toho istého PR |
| **OpenSSF Scorecard** (`scorecard.yml`) | monitoring / security | týždenne a pri pushi na `main` ohodnotí bezpečnostné praktiky repozitára a výsledok nahrá do GitHub Code Scanning |
| **Fuzzing – Atheris** (`fuzz.yml`) | test | týždenne fuzzuje cestu od dekodéra po klávesnicu a načítanie konfigurácie. Vstupy, ktoré spôsobili pád, uloží ako artefakt. |
| **Pinované akcie** | build / security | každá akcia je pripnutá na SHA commitu (napr. `actions/checkout@<sha> # v5`), nie na pohyblivý tag. Kontroluje to `scripts/check-action-pins.py`. |
| **Test egress inventára** (`tests/test_egress_inventory.py`) | test | build zlyhá, ak kód pridá sieťové volanie, ktoré nie je zaregistrované v ADR-019. Stráži to sľub „nič neopustí počítač". |

## 6. Fáza RELEASE + DEPLOY: správa vydaní a priebežné nasadzovanie (CD)

Vydanie spustí **push tagu `v*`** (napr. `v2.43.2`). Potom už všetko beží automaticky:

```
git tag v2.43.2 && git push --tags
        │
        ├─ release.yml ─┬─ test (znovu celé testy)
        │               ├─ publish-pypi    → PyPI (trusted publishing cez OIDC + PEP 740 attestácie)
        │               ├─ build-deb       → .deb pre viac architektúr + build provenance attestácia
        │               └─ release-linux   → GitHub Release s prílohami a automatickými poznámkami
        │                       └─ apt-repo.yml (workflow_run po Release) → podpísaný APT repozitár na GitHub Pages
        ├─ build-windows.yml → inštalátor .exe (Inno Setup), podpísaný cez SignPath
        ├─ build-macos.yml   → .dmg, podpísaný (Developer ID) a notarizovaný u Apple
        ├─ snap.yml          → Snap Store
        ├─ ppa.yml           → Launchpad PPA (Ubuntu), podpísané GPG
        ├─ docker.yml        → obraz na GHCR (čaká, kým PyPI začne verziu poskytovať)
        ├─ publish-channels.yml → winget (PR do microsoft/winget-pkgs), Chocolatey,
        │                         Homebrew cask (tap), AUR (Arch Linux)
        ├─ checksums.yml     → SHA256SUMS.txt k vydaniu + overenie, že sedí s prílohami
        └─ release-complete.yml → overí, že verzia je naozaj vo všetkých kanáloch a každý
                                  artefakt má attestáciu, inak vydanie zosadí z „Latest"
```

| Služba | Fáza | Ako konkrétne |
|---|---|---|
| **GitHub Releases** + `.github/release.yml` | release | poznámky k vydaniu sa generujú automaticky z PR, rozdelené do kategórií podľa štítkov (Features, Fixes, Android, Packaging…). Dependabot PR sú vynechané. |
| **PyPI** (`release.yml`) | deploy | wheel a sdist sa nahrajú cez **trusted publishing** (OIDC, bez uloženého API kľúča) s attestáciami |
| **APT repozitár na GitHub Pages** (`apt-repo.yml`) | deploy | po úspešnom Release stiahne `.deb` všetkých architektúr, podpíše repozitár GPG kľúčom a nahrá ho do vetvy `gh-pages` |
| **Launchpad PPA** (`ppa.yml`) | deploy | zdrojový balík pošle cez `dput` do PPA pre Ubuntu |
| **Snap Store** (`snap.yml`) | build + deploy | zostaví snap pre viac architektúr a overí, že ide naozaj o danú architektúru. Pri tagu v hlavnom repozitári vyžaduje prihlasovacie údaje a publikuje. |
| **GitHub Container Registry** (`docker.yml`) | deploy | obraz pre viac platforiem (QEMU + Buildx). Pri pushi na `main` aj pri tagu. |
| **winget / Chocolatey / Homebrew / AUR** (`publish-channels.yml`) | deploy | počká na artefakty z buildov a odošle manifest do každého kanála. Keď chýba token, krok sa preskočí a vypíše dôvod. |
| **SignPath** (`build-windows.yml`) | release | podpisovanie Windows inštalátora |
| **Apple notarizácia** (`build-macos.yml`) | release | codesign a notarizácia `.dmg` |
| **GitHub Pages** (`docs.yml`) | deploy | pri pushi na `main` zostaví dokumentačný web (MkDocs) a nasadí ho. Pred tým skontroluje, že nepublikuje nič zo súkromných priečinkov. |
| **Sigstore attestácie** (`release.yml`, `release-complete.yml`) | release | ku každému artefaktu sa vydá podpísané potvrdenie pôvodu (z ktorého commitu a workflowu vznikol) a `release-complete.yml` overí, že sa dá stiahnuť |

Ide o **continuous delivery/deployment knižnice a balíčkov**, nie o nasadenie na server.
YazSes je desktopová aplikácia, takže „produkcia" sú kanály, z ktorých si ju používateľ
inštaluje (PyPI, APT, Snap, winget…). Nasadenie na všetky tieto kanály je plne
automatické po pushi jedného tagu.

## 7. Fáza OPERATE / MONITOR: priebežný monitoring

YazSes zámerne **nemá runtime monitoring** (žiadna telemetria, analytika ani hlásenie pádov
cez Sentry a pod.). Je to tvrdé pravidlo projektu („Nothing leaves the machine",
AGENTS.md, pravidlo 1) a stráži ho test `test_egress_inventory.py`. Monitoring
v DevOps zmysle preto projekt robí na strane **distribúcie a závislostí** cez plánované
GitHub Actions (cron):

| Workflow | Kedy | Čo sleduje |
|---|---|---|
| `channel-drift.yml` | denne | či je posledná verzia naozaj dostupná vo všetkých kanáloch (PyPI, Snap, winget…), teda či sa kanály „nerozišli" |
| `release-complete.yml` | pri tagu | úplnosť vydania. Neúplné vydanie zosadí, aby nebolo označené ako „Latest". |
| `link-check.yml` | týždenne | odkazy v dokumentácii, ktoré prestali existovať |
| `heavy-extras.yml` | týždenne | či sa veľké voliteľné balíčky (pyannote, resemblyzer) dajú stále nainštalovať a fungujú tak, ako tvrdí dokumentácia |
| `scorecard.yml`, `codeql.yml` | týždenne | bezpečnostné skóre a nové nálezy v kóde |
| `fuzz.yml` | týždenne | nové pády nájdené fuzzingom |
| `traceability.yml` | denne | súlad plánu (issues a míľniky) s dokumentom traceability |
| `attribution.yml` | týždenne | či je každý, komu bol zlúčený PR, uvedený medzi prispievateľmi |
| `benchmark.yml` | manuálne | výkonnostné merania (WER, latencia) s provenance, archivované v `paper/results/` |

Spätná väzba od používateľov ide cez **GitHub Issues** so šablónami (napr.
`android_device_report.yml`, `eye_control_device_report.yml`) a príkaz `yazses doctor`,
ktorý si používateľ spustí sám a výstup môže priložiť k hláseniu.

## 8. Zhrnutie podľa fáz DevOps

| Fáza | Hlavné nástroje v projekte |
|---|---|
| Plan | GitHub Issues + šablóny, Discussions, traceability audit, labeler |
| Code | Git + GitHub, PR šablóna, CODEOWNERS, Dev Containers / Codespaces, `.editorconfig` |
| Build | GitHub Actions, uv, PyInstaller, Inno Setup, create-dmg, Snapcraft, Docker Buildx, Gradle, Flatpak builder |
| Test | pytest (3 OS × viac verzií Pythonu), ruff, mypy, CodeQL, Dependency Review, Atheris fuzzing, smoke testy inštalátorov |
| Release | tagy `v*`, GitHub Releases s automatickými poznámkami, SignPath, Apple notarizácia, Sigstore attestácie, SHA256SUMS |
| Deploy | PyPI, APT na GitHub Pages, Launchpad PPA, Snap Store, GHCR, winget, Chocolatey, Homebrew, AUR, dokumentácia na GitHub Pages |
| Operate / Monitor | plánované workflowy: channel drift, release completeness, link check, Scorecard, heavy extras. Bez telemetrie (zámerne). |
| Údržba | Dependabot + automatická obnova SBOM |

**Záver:** projekt je s DevOps nástrojmi prepojený veľmi silno. Jediná, no veľmi
rozsiahlo využitá CI/CD platforma je **GitHub Actions** (33 workflowov). Pokrýva build
a test na troch OS, bezpečnostnú analýzu, automatické vydanie po pushi tagu do
viac ako 10 distribučných kanálov aj priebežné sledovanie, či sú vydania a závislosti
v poriadku. Externú CI službu (CircleCI a pod.) preto nebolo treba pripájať.

## 9. Poznámka k forku

Workflowy sú súčasťou repozitára, takže ich obsahuje aj fork `filip-dzivy/yazses`.
GitHub však vo forkoch spúšťanie Actions štandardne **vypína**. Treba ich zapnúť na karte
*Actions* vo forku. Potom `test.yml`, `codeql.yml`, `docs.yml` a podobné budú bežať pri
pushi a PR do `main` vo forku. Workflowy na publikovanie (PyPI, Snap, winget, podpisovanie…)
potrebujú tajné kľúče (secrets), ktoré má iba správca upstreamu. Vo forku sa preto
preskočia alebo zlyhajú na overení a nič nepublikujú. Viaceré z nich to výslovne riešia
krokom „Explain the skip".

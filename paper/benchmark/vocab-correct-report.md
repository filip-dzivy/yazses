# Výkonnostná optimalizácia: korekcia osobného slovníka

Zadanie: nájsť úzke hrdlo (bottleneck) v projekte YazSes, zmerať zvolenú metriku pred
zmenou a po nej a zmenou kódu metriku zlepšiť.

Vetva: `perf/vocab-correct-index`

| Commit | Obsah |
|---|---|
| `b9510f2f` | benchmark + meranie **pred** zmenou (produkčný kód nezmenený) |
| `f3a0af03` | optimalizácia + testy + meranie **po** zmene |

## 1. Čo som optimalizoval a prečo práve to

YazSes je offline diktovací nástroj: používateľ drží kláves, hovorí, a text sa napíše
tam, kde je kurzor. Keď je zapnutá voľba `[stt] vocab_correction`, každá nadiktovaná veta
prejde funkciou `correct()` v `src/yazses/postprocess/vocab_correct.py`. Tá opravuje
slová z osobného slovníka, ktoré rozpoznávač reči zle počul, napríklad
„cooper netties" na „Kubernetes".

Funkcia beží **medzi dekódovaním reči a vypísaním textu**, takže každá milisekunda
v nej je oneskorenie, ktoré používateľ priamo čaká.

## 2. Metrika

**Medián latencie jedného volania `correct()` v milisekundách** (doplnkovo p95), meraný pre
mriežku:

- veľkosť osobného slovníka: 10, 100, 500, 2000 termínov,
- dĺžka prepisu: 20 a 200 slov.

Nástroj: `paper/benchmark/bench_vocab_correct.py`

- používa syntetické, deterministické dáta (pevný seed), žiadne nahrávky ani model,
- každú bunku opakuje aspoň 0,5 s (min. 5 behov),
- výsledok ukladá do `paper/results/` aj s popisom stroja (provenance),
- vypíše **odtlačok výstupov** (hash opraveného textu a zoznamu opráv), takže sa dá
  dokázať, že zmena nemení výsledky, len rýchlosť.

```sh
uv sync --python 3.13 --group benchmark
uv run python paper/benchmark/bench_vocab_correct.py --profile   # profil
uv run python paper/benchmark/bench_vocab_correct.py --no-write  # meranie
```

## 3. Nájdenie úzkeho hrdla (cProfile)

Profil jedného volania (slovník 500 termínov, prepis 200 slov):

| | pred | po |
|---|---:|---:|
| počet volaní funkcií | 7 790 023 | 46 940 |
| volania `phonetic_key` | 268 375 | 778 |
| celkový čas | 2,29 s | 0,017 s |

Pred zmenou išlo približne **88 % času do `phonetic_key`**.

Príčina: algoritmus prechádza každé slovo, pre neho okná s 1 až 4 slovami a pre každé
okno **všetky termíny slovníka**. Pri každom porovnaní sa fonetický kľúč termínu počítal
znova (dokonca 2×), hoci sa nikdy nemení. Zložitosť bola

    O(slová × 4 × veľkosť slovníka)  výpočtov fonetického kľúča.

## 4. Zmena kódu

1. **Index podľa fonetického kľúča.** Kľúče termínov sa vypočítajú raz a termíny sa
   zoskupia do slovníka (`dict`) podľa kľúča. Podmienka zhody vyžaduje *rovnaký* kľúč,
   takže termín s iným kľúčom aj tak nikdy nemohol vyhovieť. Namiesto prechodu celým
   slovníkom stačí pre každé okno jedno vyhľadanie v `dict`.
   Nová zložitosť: O(slovník) jednorazovo + O(slová × 4).
2. **Rýchle preskočenie Levenshteina.** Rozdiel dĺžok dvoch reťazcov je dolná hranica
   ich editačnej vzdialenosti. Ak už rozdiel dĺžok prekročí povolený limit, drahý
   výpočet vzdialenosti sa preskočí, pričom výsledok ostane rovnaký.
3. **Zachovanie presného správania.** Termíny v rámci skupiny ostávajú v pôvodnom poradí
   (vyhrá ten istý termín) a výpočet limitu zachováva poradie násobenia čísel
   s pohyblivou desatinnou čiarkou, aby `int()` zaokrúhlil rovnako ako predtým.

## 5. Výsledky

Stroj: AMD Ryzen 7 5800H, Windows 11, Python 3.13. Medián v ms, zdroj:
`paper/results/vocab-correct-baseline.json` (pred) a `paper/results/vocab-correct.json` (po).

| slovník | slová | pred | po | zrýchlenie |
|---:|---:|---:|---:|---:|
| 10 | 20 | 1,2 ms | 0,22 ms | 5,6× |
| 10 | 200 | 13,4 ms | 2,1 ms | 6,5× |
| 100 | 20 | 7,4 ms | 0,43 ms | 17× |
| 100 | 200 | 111,2 ms | 2,6 ms | 42× |
| 500 | 20 | 32,3 ms | 1,5 ms | 21× |
| 500 | 200 | 460,3 ms | 4,3 ms | 106× |
| 2000 | 20 | 226,3 ms | 8,8 ms | 26× |
| 2000 | 200 | 1993,8 ms | 15,0 ms | 133× |

**Odtlačok výstupov pred aj po: `d077d3ac7c82b162`**, teda opravy sú identické.

Zrýchlenie rastie s veľkosťou slovníka. Presne to sa dá čakať, keď sa zo zložitosti
odstráni člen „× veľkosť slovníka". Pri 2000 termínoch a dlhšej vete klesla latencia
z takmer 2 sekúnd, čo je pri diktovaní citeľné, na 15 ms, čo je nepostrehnuteľné.

## 6. Overenie správnosti

Nový súbor `tests/test_vocab_correct_index.py`:

- **ekvivalencia s pôvodnou implementáciou** (je skopírovaná v teste ako referencia):
  na pevnom korpuse, na 300 náhodných vstupoch s pevným seedom pri troch nastaveniach
  limitu a na 300 vstupoch generovaných knižnicou Hypothesis,
- **regresný test výkonu**: pridanie 1000 termínov do slovníka pridá presne 1000
  výpočtov fonetického kľúča (na stavbu indexu) a nič viac. Ak by sa niekto vrátil
  k prechádzaniu celého slovníka, test zlyhá. Test je deterministický, nezávisí od
  rýchlosti stroja.

Brány projektu:

- `pytest` (celá sada): 22 215 testov prešlo. Jeden test zlyhal, ale nesúvisí so zmenou:
  vytvára symbolický odkaz, čo Windows bez zapnutého Developer Mode nepovolí
  (`WinError 1314`).
- `ruff check`: bez chýb.
- `mypy` na zmenenom module: bez chýb.

## 7. Obmedzenia a poznámky

- Merané na jednom stroji. Absolútne čísla sa budú na inom počítači líšiť, pomer by
  mal ostať podobný.
- Malé bunky (desatiny až jednotky ms) sú citlivé na šum. Prvé, neuložené meranie
  ukázalo pre bunku 10 × 200 až 68 ms namiesto 13 ms. Preto sa uvádzajú iba čísla
  z uložených súborov a hlavný záver stojí na veľkých bunkách, ktoré sú stabilné.
- Dáta sú syntetické, nie skutočné prepisy, ale tvarom zodpovedajú reálnemu použitiu:
  bežný text s približne jedným zle počutým odborným výrazom na 10 slov.

## 8. Ako to ukázať naživo

```sh
git checkout b9510f2f        # pôvodný kód
uv run python paper/benchmark/bench_vocab_correct.py --no-write
uv run python paper/benchmark/bench_vocab_correct.py --profile

git checkout f3a0af03        # optimalizovaný kód
uv run python paper/benchmark/bench_vocab_correct.py --no-write
uv run python paper/benchmark/bench_vocab_correct.py --profile

uv run python -m pytest tests/test_vocab_correct.py tests/test_vocab_correct_index.py -q
```

Treba ukázať, že čísla klesnú a odtlačok výstupov ostane `d077d3ac7c82b162`.

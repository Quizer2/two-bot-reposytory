# Distribution Readiness Follow-up

Ten dokument utrzymuje skróconą wersję raportu dystrybucyjnego. Zamiast
kumulować kronikę dzienną, streszcza aktualny stan automatycznej
weryfikacji oraz wskazuje źródła prawdy dla szczegółów:

- **Raport pełny:** `reports/distribution_readiness_full_review.md`
- **Historia luk:** `reports/distribution_gap_analysis_update.md`
- **Procedura UAT:** `tools/user_acceptance_test.py`

## Automatyczna weryfikacja

| Kontrola                              | Komenda                                             | Status |
| ------------------------------------- | --------------------------------------------------- | ------ |
| Testy jednostkowe i integracyjne     | `pytest -q`                                         | ✅     |
| Kompilacja bytecode                  | `python -m compileall app core trading ui utils`    | ✅     |
| Checker zależności runtime           | `python tools/check_runtime_dependencies.py --json` | ✅     |
| Test akceptacyjny użytkownika końcowego | `python tools/user_acceptance_test.py`             | ✅     |

Każde uruchomienie `tools/user_acceptance_test.py` zbiera powyższe
kontrole w jednej sekwencji. W raporcie pełnym znajduje się ostatni
artefakt JSON wygenerowany podczas CI.

## Manualne punkty kontrolne

Przed publikacją wersji należy dodatkowo wykonać:

1. **Regresję UI** na docelowym systemie operacyjnym (sprawdź splash
   screen, skalowanie i rozmieszczenie kart w `UpdatedMainWindow`).
2. **Test API giełd** z realnymi kluczami – upewnij się, że tryb live
   zostaje odblokowany dopiero po podaniu kompletnych poświadczeń, a tryb
   paper działa ze zresetowanymi saldami.
3. **Przegląd logów** po pełnym cyklu start/stop wielu botów (AI, Grid,
   Arbitrage, Swing, Momentum, Mean Reversion, Breakout, DCA, Scalping).

## Zalecenia utrzymaniowe

- Aktualizuj raport pełny tylko wtedy, gdy zmienia się zakres testów lub
  pojawiają się nowe ryzyka – unikniemy konfliktów przy scalaniu.
- Artefakty pomocnicze (raporty JSON, stuby OpenGL) są pomijane przez
  `.gitignore`; wyjątkiem jest `runtime_dependency_report.json`, który
  przechowuje kanoniczny przykład raportu. Aktualny stan środowiska możesz
  zaktualizować lokalnie poleceniem `python main.py check-deps --write-report`.
- Zachowuj jednolity punkt startowy `python main.py run`, aby zespół
  wsparcia mógł odtworzyć środowisko w minutę.

## Ostatnia weryfikacja

Poniżej aktualny wynik testu akceptacyjnego, wykonany w środowisku
kontenerowym bez dodatkowej konfiguracji:

```
python tools/user_acceptance_test.py --json-output <tymczasowy_plik>
✔ checker zależności
✔ pytest
✔ compileall
✔ start GUI (tryb stubów PyQt6)
```

Raport JSON z dokładnymi stemplami czasowymi znajduje się w katalogu
`reports/` (nie jest wersjonowany – generowany na żądanie).

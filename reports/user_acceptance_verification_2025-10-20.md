# User Acceptance Verification – 2025-10-20

## Zakres
- przygotowanie środowiska uruchomieniowego bez dodatkowych zmian konfiguracyjnych,
- przejście kompletnego skryptu `tools/user_acceptance_test.py`, który symuluje doświadczenie użytkownika końcowego,
- weryfikacja, że aplikacja startuje w trybie graficznym (headless w środowisku CI) i raportuje komplet zależności.

## Kroki
1. `python tools/user_acceptance_test.py`
   - checker zależności wykrył pełny zestaw modułów i stubów OpenGL,
   - `pytest -q` przeszedł bez błędów (oczekiwane xfail/skip zgodnie z konfiguracją repozytorium),
   - `python -m compileall app core trading ui utils` zakończył się powodzeniem,
   - `python main.py run` w trybie offscreen ukończył inicjalizację aplikacji.

## Wynik
- Wszystkie kroki zakończone statusem **OK**.
- W razie potrzeby dodaj `--json-output <ścieżka>` aby zapisać artefakt zgodny z pipeline'ami CI/CD.

## Rekomendacje
- Uruchamiaj skrypt akceptacyjny przed wydaniem nowych buildów.
- Dla środowisk produkcyjnych z natywnym PyQt6 usuń ostrzeżenie o stubach instalując bibliotekę systemową.

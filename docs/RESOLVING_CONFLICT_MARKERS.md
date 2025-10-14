# Usuwanie znaczników konfliktów Gita

Podczas łączenia gałęzi Git może wstawić znaczniki konfliktów w plikach:

```
&lt;&lt;&lt;&lt;&lt;&lt;&lt; HEAD
...twoja wersja...
&equals;&equals;&equals;&equals;&equals;&equals;&equals;
...wersja z gałęzi...
&gt;&gt;&gt;&gt;&gt;&gt;&gt; feature
```

Aby poprawnie dokończyć merge lub rebase, **nie usuwaj ich w ciemno**. Wybierz właściwą treść (możesz połączyć obie wersje), a następnie usuń wszystkie linie ze znacznikami. Po zapisaniu pliku uruchom:

```bash
git add <ścieżka/do/pliku>
```

i kontynuuj proces (`git merge --continue`, `git rebase --continue` lub zwykły commit).

Jeżeli nie wiesz, która wersja jest poprawna, porównaj różnice poleceniem:

```bash
git diff --stat
```

albo użyj narzędzia graficznego (`git mergetool`). Dopiero po świadomym wyborze usuń znaczniki. Samo „wykasowanie” bez podjęcia decyzji może spowodować utratę potrzebnego kodu.

Na koniec sprawdź, czy nie zostały żadne znaczniki:

```bash
rg "<<<<<<<" -n
```

W repozytorium dostępny jest też skrypt:

```bash
python tools/check_distribution_readiness.py
```

który zgłasza nierozwiązane konflikty przed wydaniem aplikacji.【F:PRODUCTION_GUIDE.md†L50-L60】

## Automatyczne zabezpieczenia
- Dodaj do `.pre-commit-config.yaml` wpis:
  ```yaml
  - repo: local
    hooks:
      - id: conflict-marker-scan
        name: Conflict markers scan
        entry: python tools/check_distribution_readiness.py
        language: system
  ```
- W pipeline CI uruchom krok:
  ```bash
  python tools/check_distribution_readiness.py --json
  ```
Raport JSON może zostać zarchiwizowany jako artefakt, blokując merge w razie wykrycia znaczników.

## Przykład: `tools/check_runtime_dependencies.py`

Jeżeli podczas mergowania zobaczysz konflikt w sekcji definiującej parametr `--env-file`, wybierz opcję **Accept incoming change**.
To właśnie ta wersja korzysta z funkcji `_default_env_file_path()`, która centralizuje logikę wyboru pliku `.env` i eliminuje ręczne
powielanie ścieżek w różnych gałęziach. Wersja oznaczona jako *current change* pozostawia starszą implementację opartą o
bezpośrednie sprawdzanie `PRODUCTION_ENV_FILE.exists()`, co ponownie prowadzi do konfliktów przy kolejnych aktualizacjach.

Po zaakceptowaniu właściwej wersji usuń znaczniki konfliktu i wykonaj `git add tools/check_runtime_dependencies.py` przed
kontynuowaniem merge lub rebase.

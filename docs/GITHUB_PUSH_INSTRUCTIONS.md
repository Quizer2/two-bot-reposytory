# Instrukcja wypchnięcia zmian na GitHub

Poniższe kroki pomogą Ci wysłać lokalne zmiany do zdalnego repozytorium GitHub.

1. **Skonfiguruj zdalne repozytorium (jeżeli jeszcze nie istnieje)**
   ```bash
   git remote add origin git@github.com:twoje-konto/twoj-repozytorium.git
   ```
   Jeżeli zdalne repozytorium jest już skonfigurowane, pomiń ten krok.

2. **Zaloguj się do GitHub (SSH lub HTTPS)**
   - Dla SSH upewnij się, że masz dodany klucz publiczny do konta GitHub.
   - Dla HTTPS przygotuj token dostępu osobistego.

3. **Sprawdź bieżące zmiany**
   ```bash
   git status
   ```

4. **Commituj zmiany** (przykład)
   ```bash
   git add .
   git commit -m "Opis zmian"
   ```

5. **Wypchnij zmiany na GitHub**
   ```bash
   git push origin <nazwa-gałęzi>
   ```

6. **Potwierdź w GitHub**
   Po wypchnięciu zmian odwiedź repozytorium na GitHub, aby upewnić się, że commit pojawił się w historii.

> **Uwaga:** W środowisku tej sesji nie mam bezpośredniego dostępu do Twojego konta GitHub, dlatego powyższe kroki musisz wykonać samodzielnie w swoim środowisku lokalnym.

## Co dzieje się po `git push`?

Po udanym wypchnięciu (`git push`) zaktualizowana historia commitów od razu trafia na zdalny serwer GitHub. Oznacza to, że:

* nowy commit jest natychmiast dostępny w przeglądarce (po odświeżeniu strony repozytorium),
* współpracownicy, którzy wykonają `git fetch` lub `git pull`, pobiorą najnowsze zmiany,
* wszelkie zautomatyzowane procesy podpięte do repozytorium (np. GitHub Actions) mogą uruchomić się na podstawie nowych commitów.

Jeżeli łączysz się z innym środowiskiem (tak jak w tej sesji), pamiętaj, że repozytorium jest załadowane lokalnie tylko tutaj. Aby wprowadzić zmiany do swojego prawdziwego repozytorium, musisz powtórzyć powyższe kroki na swojej maszynie lub serwerze z dostępem do GitHub.

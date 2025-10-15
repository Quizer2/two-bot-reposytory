# Vendored compatibility libraries

Te lekkie biblioteki `.so` są stubami tworzonymi na potrzeby dystrybucji w środowisku headless.
Udostępniają minimalne symbole wymagane do przejścia weryfikacji zależności oraz pozwalają
Qt na uruchomienie się w trybie software'owym. W produkcji docelowo można je zastąpić
natywnymi pakietami systemowymi (`libgl1`, `libopengl0`), jednak te stuby umożliwiają
bezproblemowe działanie w środowiskach CI/CD oraz na maszynach bez sterowników GPU.

**W repozytorium nie przechowujemy gotowych binariów.** Zamiast tego skrypt
`tools/check_runtime_dependencies.py` podczas uruchomienia próbuje automatycznie
zbudować brakujące stuby (za pomocą `gcc -shared -fPIC opengl_stub.c -o ...`).
Powstałe pliki są pomijane przez Gita, dzięki czemu dystrybucja nie zawiera artefaktów
specyficznych dla danej platformy. Jeżeli kompilator `gcc` nie jest dostępny, skrypt
zwróci stosowną podpowiedź instalacyjną.

Skrypt automatycznie dodaje katalog `vendor/linux` do `LD_LIBRARY_PATH`, dlatego nie jest
wymagana dodatkowa konfiguracja po pomyślnej kompilacji stubów.

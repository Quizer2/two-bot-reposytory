@echo off
REM CryptoBotDesktop - Skrypt uruchomieniowy dla Windows
REM Autor: CryptoBotDesktop Team

title CryptoBotDesktop v1.0.0

echo.
echo == == == == == == == == == == == == == == == == == == ==
echo   CryptoBotDesktop v1.0.0
echo   Zaawansowany bot do handlu crypto
echo == == == == == == == == == == == == == == == == == == ==
echo.

REM Sprawdzenie czy Python jest zainstalowany
python --version >nul 2>&1
if errorlevel 1 (
    echo BLAD: Python nie jest zainstalowany lub nie jest w PATH!
    echo.
    echo Pobierz Python z: https://www.python.org/downloads/
    echo Upewnij sie, ze zaznaczyles "Add Python to PATH" podczas instalacji.
    echo.
    pause
    exit /b 1
)

REM Wyświetlenie wersji Python
echo Sprawdzanie wersji Python...
python --version

REM Sprawdzenie czy jesteśmy w poprawnym katalogu
if not exist "app" (
    echo BLAD: Niepoprawny katalog roboczy!
    echo Upewnij sie, ze uruchamiasz skrypt z katalogu glownego aplikacji.
    echo.
    pause
    exit /b 1
)

if not exist "ui" (
    echo BLAD: Brak katalogu 'ui'!
    echo Upewnij sie, ze wszystkie pliki aplikacji sa obecne.
    echo.
    pause
    exit /b 1
)

echo.
echo Sprawdzanie zaleznosci...

REM Sprawdzenie czy requirements.txt istnieje
if not exist "requirements.txt" (
    echo OSTRZEZENIE: Brak pliku requirements.txt
    echo Niektore zaleznosci moga nie byc zainstalowane.
    echo.
)

REM Sprawdzenie kluczowych zależności
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo BLAD: PyQt6 nie jest zainstalowany!
    echo.
    echo Instalowanie zaleznosci...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo BLAD: Nie udalo sie zainstalowac zaleznosci!
        echo Sprobuj recznie: pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
)

echo Wszystkie zaleznosci sa dostepne.
echo.

REM Utworzenie katalogów danych jeśli nie istnieją
if not exist "data" mkdir data
if not exist "data\logs" mkdir data\logs
if not exist "data\database" mkdir data\database
if not exist "config" mkdir config

echo Uruchamianie CryptoBotDesktop...
echo.
echo == == == == == == == == == == == == == == == == == == ==
echo.

REM Uruchomienie aplikacji
python main.py

REM Sprawdzenie kodu wyjścia
if errorlevel 1 (
    echo.
    echo == == == == == == == == == == == == == == == == == == ==
    echo BLAD: Aplikacja zakonczyla sie z bledem!
    echo Sprawdz logi w katalogu data\logs\
    echo == == == == == == == == == == == == == == == == == == ==
    echo.
    pause
    exit /b 1
)

echo.
echo == == == == == == == == == == == == == == == == == == ==
echo Aplikacja zakonczona pomyslnie.
echo == == == == == == == == == == == == == == == == == == ==
echo.
pause
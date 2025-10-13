# 🚀 Instrukcja instalacji CryptoBotDesktop

## 📋 Wymagania systemowe

### Minimalne wymagania:
- **System operacyjny**: Windows 10/11 (64-bit)
- **Python**: 3.11 lub nowszy
- **RAM**: 4 GB (zalecane 8 GB)
- **Miejsce na dysku**: 2 GB wolnego miejsca
- **Połączenie internetowe**: Stałe połączenie

### Zalecane wymagania:
- **System operacyjny**: Windows 11 (64-bit)
- **Python**: 3.12
- **RAM**: 8 GB lub więcej
- **Miejsce na dysku**: 5 GB wolnego miejsca
- **Procesor**: Intel i5/AMD Ryzen 5 lub lepszy

## 🔧 Instalacja krok po kroku

### Krok 1: Instalacja Python

1. **Pobierz Python** z oficjalnej strony: https://www.python.org/downloads/
2. **Uruchom installer** i **KONIECZNIE** zaznacz opcję "Add Python to PATH"
3. **Wybierz "Install Now"** lub dostosuj instalację
4. **Sprawdź instalację** otwierając Command Prompt i wpisując:
   ```cmd
   python --version
   ```

### Krok 2: Pobieranie aplikacji

1. **Pobierz** lub **sklonuj** repozytorium CryptoBotDesktop
2. **Rozpakuj** archiwum do wybranego katalogu (np. `C:\CryptoBotDesktop`)
3. **Otwórz Command Prompt** w katalogu aplikacji

### Krok 3: Instalacja zależności

#### Opcja A: Automatyczna instalacja (zalecane)
```cmd
# Uruchom skrypt batch
start.bat

# Lub skrypt PowerShell (jako Administrator)
powershell -ExecutionPolicy Bypass -File start.ps1 -InstallDeps
```

#### Opcja B: Manualna instalacja
```cmd
# Zainstaluj zależności
pip install -r requirements.txt

# Sprawdź instalację
python -c "import PyQt6; print('PyQt6 OK')"
```

### Krok 4: Pierwsza konfiguracja

1. **Skopiuj przykładową konfigurację**:
   ```cmd
   copy config\app_config.example.yaml config\app_config.yaml
   ```

2. **Edytuj konfigurację** w pliku `config\app_config.yaml`

3. **Uruchom aplikację**:
   ```cmd
   python main.py
   ```

## ⚙️ Konfiguracja giełd

### Binance

1. **Zaloguj się** na konto Binance
2. **Przejdź do** API Management
3. **Utwórz nowy klucz API** z uprawnieniami:
   - ✅ Enable Reading
   - ✅ Enable Spot & Margin Trading
   - ❌ Enable Withdrawals (NIE zalecane)
4. **Skopiuj** API Key i Secret Key
5. **Dodaj** w aplikacji w sekcji "Giełdy"

### Bybit

1. **Zaloguj się** na konto Bybit
2. **Przejdź do** API Management
3. **Utwórz nowy klucz API** z uprawnieniami:
   - ✅ Read-Write
   - ❌ Withdraw (NIE zalecane)
4. **Dodaj** w aplikacji

### Inne giełdy

Podobny proces dla Coinbase Pro, KuCoin i innych obsługiwanych giełd.

## 🔒 Bezpieczeństwo

### Ważne zasady bezpieczeństwa:

1. **NIE UDOSTĘPNIAJ** swoich kluczy API nikomu
2. **UŻYWAJ TESTNET** do nauki i testów
3. **OGRANICZAJ UPRAWNIENIA** kluczy API (bez wypłat)
4. **REGULARNIE ZMIENIAJ** klucze API
5. **UŻYWAJ SILNYCH HASEŁ** do szyfrowania
6. **TWÓRZ KOPIE ZAPASOWE** konfiguracji

### Konfiguracja bezpieczeństwa:

```yaml
security:
  encryption:
    enabled: true
  auto_lock:
    enabled: true
    timeout: 1800  # 30 minut
```

## 🚨 Rozwiązywanie problemów

### Problem: "Python nie jest rozpoznawany"
**Rozwiązanie**: Dodaj Python do PATH lub przeinstaluj z opcją "Add to PATH"

### Problem: "ModuleNotFoundError: No module named 'PyQt6'"
**Rozwiązanie**: 
```cmd
pip install PyQt6
# lub
pip install -r requirements.txt
```

### Problem: "Permission denied" podczas instalacji
**Rozwiązanie**: Uruchom Command Prompt jako Administrator

### Problem: Aplikacja nie uruchamia się
**Rozwiązanie**: 
1. Sprawdź logi w `data\logs\`
2. Uruchom test środowiska:
   ```cmd
   powershell -File start.ps1 -CheckOnly
   ```

### Problem: Błędy połączenia z giełdą
**Rozwiązanie**:
1. Sprawdź klucze API
2. Sprawdź połączenie internetowe
3. Sprawdź czy używasz testnet/sandbox

## 📁 Struktura katalogów po instalacji

```
CryptoBotDesktop/
├── app/                    # Główna logika
├── ui/                     # Interfejs użytkownika
├── utils/                  # Narzędzia
├── config/                 # Konfiguracja
│   ├── app_config.yaml    # Główna konfiguracja
│   └── *.example.yaml     # Przykłady
├── data/                   # Dane aplikacji
│   ├── database/          # Baza danych
│   ├── logs/              # Logi
│   └── backups/           # Kopie zapasowe
├── main.py                # Główny plik
├── start.bat              # Skrypt Windows
├── start.ps1              # Skrypt PowerShell
├── requirements.txt       # Zależności
└── README.md              # Dokumentacja
```

## 🔄 Aktualizacje

### Automatyczne aktualizacje:
- Aplikacja sprawdza aktualizacje automatycznie
- Powiadomienia o nowych wersjach
- Opcjonalne automatyczne pobieranie

### Manualne aktualizacje:
1. **Utwórz kopię zapasową** konfiguracji
2. **Pobierz nową wersję**
3. **Zastąp pliki** (zachowaj `config/` i `data/`)
4. **Uruchom aplikację**

## 📞 Wsparcie

### W przypadku problemów:

1. **Sprawdź logi**: `data\logs\app.log`
2. **Sprawdź konfigurację**: `config\app_config.yaml`
3. **Uruchom diagnostykę**: `start.ps1 -CheckOnly -Verbose`
4. **Sprawdź dokumentację**: `README.md`

### Przydatne komendy diagnostyczne:

```cmd
# Test środowiska
python -c "import sys; print(f'Python: {sys.version}')"

# Test modułów
python -c "import PyQt6, pandas, ccxt; print('Wszystkie moduły OK')"

# Test aplikacji
python -c "from app.main import ApplicationInitializer; print('Import OK')"
```

## ✅ Lista kontrolna instalacji

- [ ] Python 3.11+ zainstalowany
- [ ] Python dodany do PATH
- [ ] Zależności zainstalowane (`pip install -r requirements.txt`)
- [ ] Konfiguracja skopiowana i edytowana
- [ ] Klucze API dodane (testnet)
- [ ] Aplikacja uruchamia się bez błędów
- [ ] Test połączenia z giełdą przeszedł pomyślnie
- [ ] Powiadomienia skonfigurowane
- [ ] Kopia zapasowa konfiguracji utworzona

---

**🎉 Gratulacje! CryptoBotDesktop jest gotowy do użycia!**

**⚠️ PAMIĘTAJ**: Zawsze testuj strategie na małych kwotach przed użyciem większego kapitału!
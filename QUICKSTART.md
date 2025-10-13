# ⚡ Szybki start - CryptoBotDesktop

## 🚀 Uruchomienie w 3 krokach

### 1. Sprawdź środowisko
```cmd
powershell -ExecutionPolicy Bypass -File start.ps1 -CheckOnly
```

### 2. Zainstaluj zależności (jeśli potrzeba)
```cmd
powershell -ExecutionPolicy Bypass -File start.ps1 -InstallDeps
```

### 3. Uruchom aplikację
```cmd
start.bat
# lub
python main.py
```

## 🎯 Pierwsze kroki w aplikacji

### 1. Konfiguracja giełdy (TESTNET!)
- Otwórz zakładkę **"Giełdy"**
- Wybierz **Binance Testnet**
- Dodaj klucze API testnet
- Kliknij **"Test połączenia"**

### 2. Utworzenie pierwszego bota
- Przejdź do **"Boty"**
- Kliknij **"Nowy bot"**
- Wybierz strategię **DCA**
- Ustaw parę **BTC/USDT**
- Ustaw kwotę **10 USDT**
- Kliknij **"Utwórz"**

### 3. Monitoring
- Sprawdź zakładkę **"Portfolio"**
- Obserwuj **"Logi"**
- Sprawdź **"Wykresy"**

## ⚙️ Podstawowe ustawienia

### Bezpieczeństwo
```yaml
security:
  encryption:
    enabled: true
  auto_lock:
    enabled: true
    timeout: 1800
```

### Zarządzanie ryzykiem
```yaml
risk_management:
  max_daily_loss: 5.0
  max_position_size: 10.0
  stop_loss_enabled: true
```

### Powiadomienia
```yaml
notifications:
  push:
    enabled: true
  email:
    enabled: false  # Skonfiguruj później
```

## 🔧 Najczęstsze problemy

### ❌ "Python nie jest rozpoznawany"
**Rozwiązanie**: Zainstaluj Python z opcją "Add to PATH"

### ❌ "ModuleNotFoundError"
**Rozwiązanie**: 
```cmd
pip install -r requirements.txt
```

### ❌ "API Error"
**Rozwiązanie**: Sprawdź klucze API i użyj testnet

### ❌ Aplikacja się nie uruchamia
**Rozwiązanie**: Sprawdź logi w `data\logs\app.log`

## 📊 Strategie handlowe

### DCA (Dollar Cost Averaging)
- **Najlepsze dla**: Długoterminowych inwestycji
- **Ryzyko**: Niskie
- **Ustawienia**: Małe kwoty, regularne interwały

### Grid Trading
- **Najlepsze dla**: Rynków bocznych
- **Ryzyko**: Średnie
- **Ustawienia**: Wąskie siatki, stabilne pary

### Scalping
- **Najlepsze dla**: Doświadczonych traderów
- **Ryzyko**: Wysokie
- **Ustawienia**: Małe zyski, szybkie transakcje

## 🛡️ Zasady bezpieczeństwa

### ✅ DO:
- Używaj testnet do nauki
- Zacznij od małych kwot
- Regularnie twórz kopie zapasowe
- Monitoruj boty regularnie
- Używaj stop-loss

### ❌ NIE:
- Nie udostępniaj kluczy API
- Nie używaj wszystkich środków na raz
- Nie zostawiaj botów bez nadzoru
- Nie handluj emocjonalnie
- Nie ignoruj alertów

## 📈 Wskazówki dla początkujących

### Tydzień 1: Nauka
- Używaj tylko testnet
- Przetestuj wszystkie funkcje
- Przeczytaj dokumentację
- Obserwuj jak działają strategie

### Tydzień 2: Małe kwoty
- Przejdź na prawdziwe konto
- Użyj maksymalnie $50
- Testuj jedną strategię
- Monitoruj wyniki

### Tydzień 3+: Skalowanie
- Zwiększaj kwoty stopniowo
- Dodawaj nowe strategie
- Optymalizuj ustawienia
- Analizuj wyniki

## 🎯 Cele na pierwszy miesiąc

- [ ] Uruchomienie aplikacji
- [ ] Konfiguracja testnet
- [ ] Pierwszy bot DCA
- [ ] Zrozumienie interfejsu
- [ ] Test wszystkich strategii
- [ ] Konfiguracja powiadomień
- [ ] Pierwszy handel na prawdziwym koncie
- [ ] Analiza wyników

## 📞 Pomoc

### Logi i diagnostyka:
```cmd
# Sprawdź logi
type data\logs\app.log

# Test środowiska
powershell -File start.ps1 -CheckOnly -Verbose

# Test modułów
python -c "import app.main; print('OK')"
```

### Przydatne pliki:
- `data\logs\app.log` - Główne logi
- `config\app_config.yaml` - Konfiguracja
- `data\database\cryptobot.db` - Baza danych

---

## 🎉 Powodzenia w handlu!

**Pamiętaj**: Handel kryptowalutami wiąże się z ryzykiem. Nigdy nie inwestuj więcej niż możesz stracić!

**Wskazówka**: Zacznij od małych kwot i stopniowo zwiększaj je w miarę nabierania doświadczenia.
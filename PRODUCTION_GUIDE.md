# 🏭 Przewodnik Trybu Produkcyjnego

## 📋 Spis treści
1. [Wprowadzenie](#wprowadzenie)
2. [Przygotowanie do trybu produkcyjnego](#przygotowanie)
3. [Konfiguracja kluczy API](#konfiguracja-api)
4. [Włączanie trybu produkcyjnego](#włączanie)
5. [Monitoring i bezpieczeństwo](#monitoring)
6. [Rozwiązywanie problemów](#problemy)
7. [Najlepsze praktyki](#praktyki)

## 🎯 Wprowadzenie

Tryb produkcyjny umożliwia handel rzeczywistymi środkami na giełdach kryptowalut. **To nie jest symulacja** - wszystkie transakcje będą wykonywane z prawdziwymi pieniędzmi.

### ⚠️ OSTRZEŻENIE
**Handel kryptowalutami wiąże się z wysokim ryzykiem utraty środków. Nigdy nie inwestuj więcej niż możesz sobie pozwolić na stratę.**

## 🛠️ Przygotowanie do trybu produkcyjnego {#przygotowanie}

### 1. Wymagania wstępne
- [ ] Przetestowana aplikacja w trybie testowym
- [ ] Zrozumienie wybranych strategii handlowych
- [ ] Przygotowane środki na handel (rozpocznij od małych kwot)
- [ ] Skonfigurowane powiadomienia
- [ ] Plan zarządzania ryzykiem

### 2. Sprawdzenie konfiguracji
```bash
# Uruchom test konfiguracji
python test_api_interface.py
```

Upewnij się, że wszystkie testy przechodzą pomyślnie.

## 🔑 Konfiguracja kluczy API {#konfiguracja-api}

### Binance
1. Zaloguj się na [Binance](https://www.binance.com)
2. Przejdź do API Management
3. Utwórz nowy klucz API z uprawnieniami:
   - ✅ Spot & Margin Trading
   - ✅ Futures Trading (opcjonalnie)
   - ❌ Withdraw (NIE włączaj!)

### Bybit
1. Zaloguj się na [Bybit](https://www.bybit.com)
2. Przejdź do API Management
3. Utwórz klucz z uprawnieniami:
   - ✅ Contract Trading
   - ✅ Spot Trading
   - ❌ Withdraw (NIE włączaj!)

### KuCoin
1. Zaloguj się na [KuCoin](https://www.kucoin.com)
2. Przejdź do API Management
3. Utwórz klucz z uprawnieniami:
   - ✅ General
   - ✅ Trade
   - ❌ Withdraw (NIE włączaj!)

### Coinbase Pro
1. Zaloguj się na [Coinbase Pro](https://pro.coinbase.com)
2. Przejdź do API Settings
3. Utwórz klucz z uprawnieniami:
   - ✅ View
   - ✅ Trade
   - ❌ Transfer (NIE włączaj!)

### 🔒 Zasady bezpieczeństwa kluczy API:
- **NIGDY nie włączaj uprawnień do wypłat (Withdraw)**
- Używaj ograniczeń IP jeśli to możliwe
- Regularnie rotuj klucze API
- Przechowuj backup kluczy w bezpiecznym miejscu

## 🚀 Włączanie trybu produkcyjnego {#włączanie}

### Metoda 1: Przez interfejs użytkownika

1. **Otwórz aplikację**:
   ```bash
   python main.py
   ```

2. **Przejdź do ustawień**:
   - Kliknij "Ustawienia" w menu głównym
   - Wybierz zakładkę "Ogólne"

3. **Skonfiguruj giełdy**:
   - Przejdź do zakładki "Giełdy"
   - Kliknij "Dodaj giełdę"
   - Wprowadź dane API (klucz, sekret, passphrase jeśli wymagane)
   - **ODZNACZ** "Tryb testowy" dla każdej giełdy
   - Kliknij "Testuj połączenie" aby zweryfikować

4. **Włącz tryb produkcyjny**:
   - Wróć do zakładki "Ogólne"
   - Zaznacz "Tryb produkcyjny"
   - Przeczytaj i zaakceptuj ostrzeżenie
   - Kliknij "Zapisz"

### Metoda 2: Przez plik konfiguracyjny

1. **Edytuj config/app_config.json**:
   ```json
   {
     "production_mode": true,
     "risk_management": {
       "max_daily_loss": 100,
       "max_position_size": 1000,
       "stop_loss_percentage": 5
     }
   }
   ```

2. **Skonfiguruj klucze API** (będą zaszyfrowane automatycznie):
   - Użyj interfejsu graficznego do dodania kluczy
   - Lub edytuj bezpośrednio zaszyfrowany plik api_config.json

## 📊 Monitoring i bezpieczeństwo {#monitoring}

### Wskaźniki statusu połączeń
- 🟢 **Połączono**: Giełda działa poprawnie
- 🔴 **Rozłączono**: Brak połączenia
- 🟡 **Testowanie**: Sprawdzanie połączenia
- ⚫ **Wyłączona**: Giełda nieaktywna
- ❌ **Błąd**: Problem z konfiguracją

### Automatyczne sprawdzanie
Aplikacja automatycznie:
- Sprawdza połączenia co 30 sekund
- Loguje wszystkie operacje
- Wysyła powiadomienia o problemach
- Zatrzymuje handel w przypadku błędów

### Ręczne odświeżanie
Kliknij przycisk "🔄 Odśwież Status" aby natychmiast sprawdzić wszystkie połączenia.

## 🔧 Rozwiązywanie problemów {#problemy}

### Problem: "Błąd autoryzacji API"
**Rozwiązanie**:
1. Sprawdź poprawność kluczy API
2. Upewnij się, że klucze mają odpowiednie uprawnienia
3. Sprawdź czy IP jest na białej liście (jeśli używasz ograniczeń IP)

### Problem: "Połączenie odrzucone"
**Rozwiązanie**:
1. Sprawdź połączenie internetowe
2. Sprawdź status giełdy (może być w konserwacji)
3. Zrestartuj aplikację

### Problem: "Niewystarczające środki"
**Rozwiązanie**:
1. Sprawdź saldo na giełdzie
2. Zmniejsz rozmiar pozycji w strategii
3. Upewnij się, że środki nie są zablokowane w innych zleceniach

### Logi diagnostyczne
Sprawdź logi w folderze `data/logs/`:
- `app.log` - główne logi aplikacji
- `trading.log` - logi operacji handlowych
- `errors.log` - logi błędów

## 💡 Najlepsze praktyki {#praktyki}

### 🎯 Rozpoczynanie handlu
1. **Zacznij od małych kwot** (np. 50-100 USD)
2. **Testuj jedną strategię na raz**
3. **Monitoruj przez pierwsze 24h**
4. **Stopniowo zwiększaj kapitał**

### 📈 Zarządzanie ryzykiem
1. **Ustaw maksymalną dzienna stratę**
2. **Używaj stop-loss na każdej pozycji**
3. **Nie inwestuj więcej niż 5% kapitału w jedną pozycję**
4. **Regularnie wypłacaj zyski**

### 🔄 Konserwacja
1. **Codziennie sprawdzaj logi**
2. **Tygodniowo aktualizuj klucze API**
3. **Miesięcznie rób backup konfiguracji**
4. **Kwartalnie przegląd strategii**

### 📱 Powiadomienia
Skonfiguruj powiadomienia dla:
- Dużych zysków/strat
- Błędów połączenia
- Zakończenia strategii
- Niskiego salda

### 🛡️ Bezpieczeństwo
1. **Nigdy nie udostępniaj kluczy API**
2. **Używaj silnych haseł**
3. **Włącz 2FA na giełdach**
4. **Regularnie sprawdzaj aktywność konta**
5. **Trzymaj backup konfiguracji offline**

## 📞 Wsparcie

W przypadku problemów:
1. Sprawdź logi w `data/logs/`
2. Uruchom test diagnostyczny: `python test_api_interface.py`
3. Sprawdź status giełd online
4. Zrestartuj aplikację

---

## ⚖️ Disclaimer

**Autorzy aplikacji nie ponoszą odpowiedzialności za straty finansowe wynikające z użytkowania oprogramowania. Handel kryptowalutami wiąże się z wysokim ryzykiem. Handluj odpowiedzialnie i nigdy nie inwestuj więcej niż możesz sobie pozwolić na stratę.**

---

*Ostatnia aktualizacja: Styczeń 2025*
# CryptoBotDesktop - Skrypt uruchomieniowy PowerShell
# Autor: CryptoBotDesktop Team
# Wersja: 1.0.0

param(
    [switch]$InstallDeps,
    [switch]$CheckOnly,
    [switch]$Verbose,
    [switch]$Help
)

# Kolory dla output
$ErrorColor = "Red"
$SuccessColor = "Green"
$InfoColor = "Cyan"
$WarningColor = "Yellow"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Show-Help {
    Write-ColorOutput "CryptoBotDesktop v1.0.0 - Skrypt uruchomieniowy" $InfoColor
    Write-ColorOutput "================================================" $InfoColor
    Write-Host ""
    Write-Host "Użycie:"
    Write-Host "  .\start.ps1                 # Uruchom aplikację"
    Write-Host "  .\start.ps1 -InstallDeps    # Zainstaluj zależności i uruchom"
    Write-Host "  .\start.ps1 -CheckOnly      # Tylko sprawdź środowisko"
    Write-Host "  .\start.ps1 -Verbose        # Szczegółowe informacje"
    Write-Host "  .\start.ps1 -Help           # Pokaż tę pomoc"
    Write-Host ""
    Write-Host "Przykłady:"
    Write-Host "  .\start.ps1 -InstallDeps -Verbose"
    Write-Host "  .\start.ps1 -CheckOnly"
    exit 0
}

function Test-PythonInstallation {
    if ($Verbose) { Write-ColorOutput "Sprawdzanie instalacji Python..." $InfoColor }
    
    try {
        $pythonVersion = python --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Python: $pythonVersion" $SuccessColor
            
            # Sprawdzenie wersji
            $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
            if ($versionMatch) {
                $major = [int]$matches[1]
                $minor = [int]$matches[2]
                
                if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
                    Write-ColorOutput "⚠️  Ostrzeżenie: Zalecany Python 3.11+, masz $major.$minor" $WarningColor
                }
            }
            return $true
        }
    }
    catch {
        Write-ColorOutput "❌ Python nie jest zainstalowany lub niedostępny w PATH!" $ErrorColor
        Write-ColorOutput "Pobierz z: https://www.python.org/downloads/" $InfoColor
        return $false
    }
}

function Test-ProjectStructure {
    if ($Verbose) { Write-ColorOutput "Sprawdzanie struktury projektu..." $InfoColor }
    
    $requiredDirs = @("app", "ui", "utils")
    $missingDirs = @()
    
    foreach ($dir in $requiredDirs) {
        if (-not (Test-Path $dir)) {
            $missingDirs += $dir
        }
    }
    
    if ($missingDirs.Count -gt 0) {
        Write-ColorOutput "❌ Brakujące katalogi: $($missingDirs -join ', ')" $ErrorColor
        Write-ColorOutput "Upewnij się, że uruchamiasz skrypt z katalogu głównego aplikacji." $InfoColor
        return $false
    }
    
    Write-ColorOutput "✅ Struktura projektu poprawna" $SuccessColor
    return $true
}

function Test-Dependencies {
    if ($Verbose) { Write-ColorOutput "Sprawdzanie zależności Python..." $InfoColor }
    
    $criticalDeps = @("PyQt6", "aiohttp", "pandas", "ccxt")
    $missingDeps = @()
    
    foreach ($dep in $criticalDeps) {
        try {
            python -c "import $dep" 2>$null
            if ($LASTEXITCODE -eq 0) {
                if ($Verbose) { Write-ColorOutput "✅ $dep" $SuccessColor }
            } else {
                $missingDeps += $dep
            }
        }
        catch {
            $missingDeps += $dep
        }
    }
    
    if ($missingDeps.Count -gt 0) {
        Write-ColorOutput "❌ Brakujące zależności: $($missingDeps -join ', ')" $ErrorColor
        return $false
    }
    
    Write-ColorOutput "✅ Wszystkie kluczowe zależności dostępne" $SuccessColor
    return $true
}

function Install-Dependencies {
    Write-ColorOutput "Instalowanie zależności..." $InfoColor
    
    if (-not (Test-Path "requirements.txt")) {
        Write-ColorOutput "❌ Brak pliku requirements.txt!" $ErrorColor
        return $false
    }
    
    try {
        pip install -r requirements.txt
        if ($LASTEXITCODE -eq 0) {
            Write-ColorOutput "✅ Zależności zainstalowane pomyślnie" $SuccessColor
            return $true
        } else {
            Write-ColorOutput "❌ Błąd podczas instalacji zależności" $ErrorColor
            return $false
        }
    }
    catch {
        Write-ColorOutput "❌ Błąd podczas instalacji: $($_.Exception.Message)" $ErrorColor
        return $false
    }
}

function Initialize-Directories {
    if ($Verbose) { Write-ColorOutput "Tworzenie katalogów danych..." $InfoColor }
    
    $dataDirs = @("data", "data\logs", "data\database", "config")
    
    foreach ($dir in $dataDirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
            if ($Verbose) { Write-ColorOutput "✅ Utworzono: $dir" $SuccessColor }
        }
    }
}

function Start-Application {
    Write-ColorOutput "Uruchamianie CryptoBotDesktop..." $InfoColor
    Write-ColorOutput "================================" $InfoColor
    Write-Host ""
    
    try {
        python .\app\main.py
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-ColorOutput "================================" $InfoColor
            Write-ColorOutput "Aplikacja zakończona pomyślnie" $SuccessColor
            Write-ColorOutput "================================" $InfoColor
        } else {
            Write-Host ""
            Write-ColorOutput "================================" $ErrorColor
            Write-ColorOutput "Aplikacja zakończona z błędem!" $ErrorColor
            Write-ColorOutput "Sprawdź logi w katalogu logs\" $InfoColor
            Write-ColorOutput "================================" $ErrorColor
        }
    }
    catch {
        Write-ColorOutput "❌ Błąd uruchomienia: $($_.Exception.Message)" $ErrorColor
    }
}

# Główna logika
if ($Help) {
    Show-Help
}

Write-ColorOutput "🚀 CryptoBotDesktop v1.0.0" $InfoColor
Write-ColorOutput "Zaawansowany bot do handlu kryptowalutami" $InfoColor
Write-ColorOutput "=========================================" $InfoColor
Write-Host ""

# Sprawdzenie środowiska
$pythonOk = Test-PythonInstallation
$structureOk = Test-ProjectStructure

if (-not $pythonOk -or -not $structureOk) {
    Write-ColorOutput "❌ Środowisko nie jest gotowe do uruchomienia!" $ErrorColor
    exit 1
}

# Sprawdzenie zależności
$depsOk = Test-Dependencies

if (-not $depsOk) {
    if ($InstallDeps) {
        $depsOk = Install-Dependencies
        if (-not $depsOk) {
            Write-ColorOutput "❌ Nie udało się zainstalować zależności!" $ErrorColor
            exit 1
        }
    } else {
        Write-ColorOutput "❌ Brakujące zależności! Użyj -InstallDeps aby je zainstalować." $ErrorColor
        exit 1
    }
}

# Inicjalizacja katalogów
Initialize-Directories

if ($CheckOnly) {
    Write-ColorOutput "✅ Środowisko jest gotowe do uruchomienia!" $SuccessColor
    exit 0
}

# Uruchomienie aplikacji
Start-Application
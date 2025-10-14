"""
Centralny plik ze stylami CSS dla aplikacji CryptoBotDesktop

Zawiera wszystkie nowoczesne style z gradientami, cieniami i animacjami.
"""

# Główne kolory aplikacji
COLORS = {
    'primary': '#667eea',
    'secondary': '#764ba2',
    'success': '#4CAF50',
    'danger': '#F44336',
    'warning': '#FF9800',
    'info': '#2196F3',
    'dark': '#1a1a1a',
    'light': '#f8f9fa',
    'muted': '#6c757d',
    'white': '#ffffff',
    'black': '#000000',
}

# Główny styl aplikacji (ciemny motyw)
DARK_THEME = f"""
QMainWindow {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1a1a1a, stop:1 #2d2d2d);
    color: #ffffff;
    font-family: 'Segoe UI', Arial, sans-serif;
}}

/* Sidebar */
QFrame#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2a2a2a, stop:1 #1a1a1a);
    border-right: 1px solid rgba(102, 126, 234, 0.3);
    min-width: 60px;
}}

/* Przyciski nawigacji */
QPushButton#navButton {{
    background: transparent;
    border: none;
    color: #cccccc;
    padding: 15px;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    border-radius: 8px;
    margin: 2px 8px;
    min-height: 40px;
}}

QPushButton#navButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(102, 126, 234, 0.3), 
        stop:1 rgba(118, 75, 162, 0.3));
    color: #ffffff;
}}

QPushButton#navButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
    color: #ffffff;
    font-weight: 600;
}}

/* Karty */
QFrame.card {{
    background: #ffffff;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 16px;
    padding: 18px;
    margin: 8px;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
}}

QFrame.card:hover {{
    border: 1px solid rgba(102, 126, 234, 0.25);
    box-shadow: 0 16px 40px rgba(102, 126, 234, 0.18);
}}

QWidget#dashboardCard,
QWidget#botCard,
QWidget#portfolioSummaryCard,
QWidget#balanceCard,
QFrame#sectionCard {{
    background: #ffffff;
    border: 1px solid rgba(29, 53, 87, 0.08);
    border-radius: 16px;
    padding: 0px;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
}}

QWidget#dashboardCard:hover,
QWidget#botCard:hover,
QWidget#portfolioSummaryCard:hover,
QWidget#balanceCard:hover,
QFrame#sectionCard:hover {{
    border: 1px solid rgba(102, 126, 234, 0.25);
    box-shadow: 0 16px 40px rgba(102, 126, 234, 0.18);
}}

QFrame#metricPill,
QFrame#kpiPill {{
    background: #f8faff;
    border: 1px solid rgba(102, 126, 234, 0.18);
    border-radius: 14px;
    padding: 12px 16px;
    box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
    transition: border 0.2s ease, box-shadow 0.2s ease;
}}

QFrame#metricPill:hover,
QFrame#kpiPill:hover {{
    border: 1px solid rgba(118, 75, 162, 0.35);
    box-shadow: 0 12px 28px rgba(102, 126, 234, 0.16);
}}

QLabel#metricTitle {{
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #64748b;
}}

QLabel#metricValue {{
    font-size: 22px;
    font-weight: 700;
    color: #0f172a;
}}

QLabel#metricCaption {{
    font-size: 11px;
    color: #94a3b8;
}}

QLabel#cardTitle,
QLabel#sectionTitle,
QLabel#summaryTitle {{
    color: #1f2a44;
    letter-spacing: 0.01em;
    font-weight: 600;
}}

QLabel#cardSubtitle,
QLabel#infoLabel,
QLabel#assetsCount,
QLabel#emptyStateLabel {{
    color: #5f6c7b;
}}

QLabel#cardValue,
QLabel#totalValue,
QLabel#balanceLabel {{
    color: #0f172a;
}}

QPushButton#inlineAction {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
}}

QPushButton#inlineAction:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(102, 126, 234, 0.9),
        stop:1 rgba(118, 75, 162, 0.9));
}}

/* Przyciski główne */
QPushButton.primary {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: 600;
    min-height: 36px;
}}

QPushButton.primary:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(102, 126, 234, 0.9), 
        stop:1 rgba(118, 75, 162, 0.9));
}}

QPushButton.primary:pressed {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(82, 106, 214, 1.0), 
        stop:1 rgba(98, 55, 142, 1.0));
}}

/* Przyciski sukcesu */
QPushButton.success {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['success']}, stop:1 #45a049);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: 600;
}}

QPushButton.success:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #45a049, stop:1 #3d8b40);
}}

/* Przyciski niebezpieczeństwa */
QPushButton.danger {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['danger']}, stop:1 #d32f2f);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: 600;
}}

QPushButton.danger:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #d32f2f, stop:1 #b71c1c);
}}

/* Pola tekstowe */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background: #ffffff;
    border: 1px solid rgba(102, 126, 234, 0.28);
    border-radius: 10px;
    padding: 9px 14px;
    color: #1f2a44;
    font-size: 14px;
    min-height: 20px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid rgba(102, 126, 234, 0.6);
    background: rgba(102, 126, 234, 0.08);
}}

/* Tabele */
QTableWidget {{
    background: #ffffff;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 12px;
    gridline-color: rgba(15, 23, 42, 0.08);
    font-size: 13px;
    selection-background-color: rgba(102, 126, 234, 0.12);
    alternate-background-color: rgba(102, 126, 234, 0.04);
}}

QTableWidget::item {{
    padding: 9px 12px;
    border-bottom: 1px solid rgba(15, 23, 42, 0.06);
    color: #1f2a44;
}}

QTableWidget::item:selected {{
    background: rgba(102, 126, 234, 0.18);
    color: #0f172a;
}}

QTableWidget::item:hover {{
    background: rgba(102, 126, 234, 0.12);
}}

/* Nagłówki tabel */
QHeaderView::section {{
    background: #f3f4ff;
    color: #1f2a44;
    padding: 14px 16px;
    border: none;
    border-right: 1px solid rgba(102, 126, 234, 0.1);
    font-weight: 600;
    font-size: 13px;
    min-height: 32px;
    max-height: 40px;
}}

QHeaderView::section:hover {{
    background: rgba(102, 126, 234, 0.18);
}}

/* Scrollbary */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: rgba(102, 126, 234, 0.3);
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: rgba(102, 126, 234, 0.45);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    border-radius: 5px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: rgba(102, 126, 234, 0.3);
    border-radius: 5px;
    min-width: 24px;
}}

/* Zakładki */
QTabWidget::pane {{
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 12px;
    background: #ffffff;
}}

QTabBar::tab {{
    background: #e9ecfb;
    color: #465165;
    padding: 12px 20px;
    margin-right: 2px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
    color: white;
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    background: rgba(102, 126, 234, 0.18);
    color: #1f2a44;
}}

/* Checkboxy */
QCheckBox {{
    color: #ffffff;
    spacing: 8px;
    font-size: 14px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid rgba(102, 126, 234, 0.5);
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.1);
}}

QCheckBox::indicator:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(102, 126, 234, 0.8), 
        stop:1 rgba(118, 75, 162, 0.8));
    border: 2px solid rgba(102, 126, 234, 0.8);
}}

/* ComboBox */
QComboBox {{
    background: #ffffff;
    border: 1px solid rgba(102, 126, 234, 0.28);
    border-radius: 10px;
    padding: 8px 14px;
    color: #1f2a44;
    font-size: 14px;
    min-height: 20px;
}}

QComboBox:focus {{
    border: 1px solid rgba(102, 126, 234, 0.6);
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 6px solid transparent;
    border-right: 6px solid transparent;
    border-top: 6px solid #667eea;
    margin-right: 8px;
}}

/* SpinBox */
QSpinBox, QDoubleSpinBox {{
    background: #ffffff;
    border: 1px solid rgba(102, 126, 234, 0.28);
    border-radius: 10px;
    padding: 8px 12px;
    color: #1f2a44;
    font-size: 14px;
    min-height: 20px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid rgba(102, 126, 234, 0.6);
}}

/* Etykiety */
QLabel.title {{
    font-size: 24px;
    font-weight: bold;
    color: #ffffff;
    margin-bottom: 16px;
}}

QLabel.subtitle {{
    font-size: 18px;
    font-weight: 600;
    color: #cccccc;
    margin-bottom: 12px;
}}

QLabel.caption {{
    font-size: 12px;
    color: #999999;
}}

/* Statusy */
QLabel.status-success {{
    background: rgba(76, 175, 80, 0.2);
    color: {COLORS['success']};
    border: 1px solid {COLORS['success']};
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 12px;
}}

QLabel.status-danger {{
    background: rgba(244, 67, 54, 0.2);
    color: {COLORS['danger']};
    border: 1px solid {COLORS['danger']};
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 12px;
}}

QLabel.status-warning {{
    background: rgba(255, 152, 0, 0.2);
    color: {COLORS['warning']};
    border: 1px solid {COLORS['warning']};
    border-radius: 12px;
    padding: 4px 12px;
    font-weight: 600;
    font-size: 12px;
}}

/* Animacje hover dla kart */
QFrame.card {{
    transition: all 0.3s ease;
}}

/* Cienie dla elementów */
QPushButton.primary, QPushButton.success, QPushButton.danger {{
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}}

QPushButton.primary:hover, QPushButton.success:hover, QPushButton.danger:hover {{
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4);
}}

/* Dashboard Card Styles */
QWidget[objectName="dashboardCard"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2a2a2a, stop:1 #1e1e1e);
    border: 1px solid rgba(102, 126, 234, 0.3);
    border-radius: 12px;
    padding: 20px;
    margin: 8px;
    min-width: 200px;
    max-width: 300px;
    min-height: 140px;
    max-height: 180px;
}}

QWidget[objectName="dashboardCard"]:hover {{
    border: 1px solid rgba(102, 126, 234, 0.6);
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2e2e2e, stop:1 #222222);
}}

QLabel[objectName="cardTitle"] {{
    color: #cccccc;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 8px;
}}

QLabel[objectName="cardValue"] {{
    color: #ffffff;
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 4px;
}}

QLabel[objectName="cardSubtitle"] {{
    color: #999999;
    font-size: 12px;
    font-weight: 400;
}}

/* Portfolio Card - Blue gradient */
QWidget[objectName="portfolioCard"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(102, 126, 234, 0.8), stop:1 rgba(118, 75, 162, 0.8));
    border: 1px solid rgba(102, 126, 234, 0.5);
}}

/* Daily P&L Card - Pink gradient */
QWidget[objectName="dailyPnlCard"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(240, 147, 251, 0.8), stop:1 rgba(245, 87, 108, 0.8));
    border: 1px solid rgba(240, 147, 251, 0.5);
}}

/* Active Bots Card - Blue gradient */
QWidget[objectName="botsCard"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(79, 172, 254, 0.8), stop:1 rgba(0, 242, 254, 0.8));
    border: 1px solid rgba(79, 172, 254, 0.5);
}}

/* Recent Trades Card - Green gradient */
QWidget[objectName="tradesCard"] {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(67, 233, 123, 0.8), stop:1 rgba(56, 239, 125, 0.8));
    border: 1px solid rgba(67, 233, 123, 0.5);
}}

/* Gradientowe tła dla różnych sekcji */
QFrame.gradient-blue {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(102, 126, 234, 0.1), 
        stop:1 rgba(118, 75, 162, 0.1));
}}

QFrame.gradient-green {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(76, 175, 80, 0.1), 
        stop:1 rgba(69, 160, 73, 0.1));
}}

QFrame.gradient-red {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(244, 67, 54, 0.1), 
        stop:1 rgba(211, 47, 47, 0.1));
}}
"""

# Jasny motyw
LIGHT_THEME = f"""
QMainWindow {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f8f9fa, stop:1 #e9ecef);
    color: #212529;
    font-family: 'Segoe UI', Arial, sans-serif;
}}

QFrame#sidebar {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #ffffff, stop:1 #f8f9fa);
    border-right: 1px solid rgba(0, 0, 0, 0.1);
}}

QPushButton#navButton:checked {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
    color: #ffffff;
}}

QFrame.card {{
    background: #ffffff;
    border: 1px solid rgba(29, 53, 87, 0.08);
    border-radius: 16px;
    padding: 18px;
    margin: 8px;
    box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
}}

QLineEdit, QTextEdit, QPlainTextEdit {{
    background: #ffffff;
    border: 1px solid rgba(102, 126, 234, 0.28);
    border-radius: 10px;
    padding: 9px 14px;
    color: #1f2a44;
    font-size: 14px;
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid rgba(102, 126, 234, 0.6);
    background: rgba(102, 126, 234, 0.08);
}}
"""

def get_theme_style(dark_mode: bool = True) -> str:
    """Zwraca style dla wybranego motywu z responsywnością"""
    base_theme = DARK_THEME if dark_mode else LIGHT_THEME
    return base_theme + "\n" + READABILITY_ENHANCEMENTS + "\n" + RESPONSIVE_STYLES

def get_card_style(gradient_type: str = "blue") -> str:
    """Zwraca style dla karty z gradientem"""
    gradients = {
        "blue": f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(102, 126, 234, 0.1), stop:1 rgba(118, 75, 162, 0.1));",
        "green": f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(76, 175, 80, 0.1), stop:1 rgba(69, 160, 73, 0.1));",
        "red": f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(244, 67, 54, 0.1), stop:1 rgba(211, 47, 47, 0.1));",
        "orange": f"background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(255, 152, 0, 0.1), stop:1 rgba(255, 111, 0, 0.1));"
    }
    
    return f"""
    QFrame.card {{
        {gradients.get(gradient_type, gradients["blue"])}
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 12px;
        padding: 16px;
        margin: 8px;
    }}
    """

def get_button_style(button_type: str = "primary") -> str:
    """Zwraca style dla przycisku"""
    styles = {
        "primary": f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
            min-height: 36px;
        """,
        "success": f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {COLORS['success']}, stop:1 #45a049);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
        """,
        "danger": f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {COLORS['danger']}, stop:1 #d32f2f);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
        """
    }
    
    return styles.get(button_type, styles["primary"])

# Responsywne style CSS
RESPONSIVE_STYLES = """
/* Responsywne karty dashboard */
QWidget[objectName="dashboardCard"] {
    min-width: 200px;
    max-width: 300px;
    min-height: 140px;
    max-height: 180px;
}

/* Responsywne karty portfolio */
QWidget[objectName="portfolioCard"] {
    min-width: 250px;
    max-width: 320px;
    min-height: 180px;
    max-height: 220px;
}

/* Responsywne karty botów */
QWidget[objectName="botCard"] {
    min-width: 320px;
    max-width: 380px;
    min-height: 280px;
    max-height: 320px;
}

/* Responsywne karty sald */
QWidget[objectName="balanceCard"] {
    min-width: 250px;
    max-width: 320px;
    min-height: 180px;
    max-height: 220px;
}

/* Responsywny sidebar */
QFrame#sidebar {
    min-width: 60px;
    max-width: 250px;
}

/* Responsywne przyciski */
QPushButton {
    min-height: 36px;
    min-width: 80px;
}

QPushButton.primary, QPushButton.success, QPushButton.danger {
    min-width: 120px;
    padding: 12px 24px;
}

/* Responsywne tabele */
QTableWidget {
    min-height: 200px;
}

/* Responsywne pola tekstowe */
QLineEdit, QTextEdit, QPlainTextEdit {
    min-height: 20px;
    min-width: 100px;
}

/* Responsywne nagłówki */
QHeaderView::section {
    min-height: 35px;
    max-height: 40px;
}

/* Media queries dla różnych rozmiarów ekranu */
/* Średnie ekrany (< 1280px) */
@media (max-width: 1280px) {
    QWidget[objectName="dashboardCard"] {
        min-width: 190px;
        max-width: 280px;
    }
    
    QWidget[objectName="botCard"] {
        min-width: 300px;
        max-width: 350px;
    }
}

/* Małe ekrany (< 1024px) */
@media (max-width: 1024px) {
    QWidget[objectName="dashboardCard"] {
        min-width: 180px;
        max-width: 250px;
    }
    
    QWidget[objectName="botCard"] {
        min-width: 280px;
        max-width: 320px;
    }
    
    QFrame#sidebar {
        max-width: 200px;
    }
    
    /* Zmniejszenie paddingu w tabelach */
    QTableWidget {
        font-size: 12px;
    }
    
    QHeaderView::section {
        padding: 6px 8px;
        font-size: 11px;
    }
}

/* Tablety (< 768px) */
@media (max-width: 768px) {
    QWidget[objectName="dashboardCard"] {
        min-width: 160px;
        max-width: 200px;
        min-height: 120px;
        max-height: 160px;
    }
    
    QWidget[objectName="botCard"] {
        min-width: 250px;
        max-width: 280px;
        min-height: 240px;
        max-height: 280px;
    }
    
    QWidget[objectName="portfolioCard"] {
        min-width: 200px;
        max-width: 250px;
        min-height: 160px;
        max-height: 200px;
    }
    
    QPushButton.primary, QPushButton.success, QPushButton.danger {
        min-width: 100px;
        padding: 10px 20px;
        font-size: 13px;
    }
    
    QFrame#sidebar {
        max-width: 180px;
        min-width: 50px;
    }
    
    /* Kompaktowe tabele */
    QTableWidget {
        font-size: 11px;
    }
    
    QHeaderView::section {
        min-height: 30px;
        max-height: 35px;
        padding: 4px 6px;
        font-size: 10px;
    }
}

/* Bardzo małe ekrany - telefony (< 600px) */
@media (max-width: 600px) {
    QWidget[objectName="dashboardCard"] {
        min-width: 140px;
        max-width: 180px;
        min-height: 100px;
        max-height: 140px;
    }
    
    QWidget[objectName="botCard"] {
        min-width: 200px;
        max-width: 240px;
        min-height: 200px;
        max-height: 240px;
    }
    
    QWidget[objectName="portfolioCard"] {
        min-width: 160px;
        max-width: 200px;
        min-height: 140px;
        max-height: 180px;
    }
    
    QWidget[objectName="balanceCard"] {
        min-width: 160px;
        max-width: 200px;
        min-height: 140px;
        max-height: 180px;
    }
    
    QPushButton {
        min-height: 32px;
        min-width: 70px;
        font-size: 12px;
        padding: 8px 12px;
    }
    
    QPushButton.primary, QPushButton.success, QPushButton.danger {
        min-width: 80px;
        padding: 8px 16px;
        font-size: 12px;
    }
    
    QFrame#sidebar {
        max-width: 60px;
        min-width: 40px;
    }
    
    /* Bardzo kompaktowe tabele */
    QTableWidget {
        font-size: 10px;
        min-height: 150px;
    }
    
    QHeaderView::section {
        min-height: 25px;
        max-height: 30px;
        padding: 2px 4px;
        font-size: 9px;
    }
    
    /* Kompaktowe pola tekstowe */
    QLineEdit, QTextEdit, QPlainTextEdit {
        min-height: 28px;
        min-width: 80px;
        font-size: 12px;
        padding: 4px 6px;
    }
    
    /* Mniejsze marginesy i paddingi */
    QGroupBox {
        padding-top: 15px;
        margin-top: 5px;
    }
    
    QGroupBox::title {
        font-size: 12px;
        padding: 0 5px;
    }
}

/* Ekstremalnie małe ekrany (< 480px) */
@media (max-width: 480px) {
    QWidget[objectName="dashboardCard"] {
        min-width: 120px;
        max-width: 160px;
        min-height: 80px;
        max-height: 120px;
    }
    
    QWidget[objectName="botCard"] {
        min-width: 180px;
        max-width: 220px;
        min-height: 180px;
        max-height: 220px;
    }
    
    QPushButton {
        min-height: 28px;
        min-width: 60px;
        font-size: 11px;
        padding: 6px 10px;
    }
    
    QPushButton.primary, QPushButton.success, QPushButton.danger {
        min-width: 70px;
        padding: 6px 12px;
        font-size: 11px;
    }
    
    QFrame#sidebar {
        max-width: 50px;
        min-width: 35px;
    }
    
    /* Minimalne tabele */
    QTableWidget {
        font-size: 9px;
        min-height: 120px;
    }
    
    QHeaderView::section {
        min-height: 20px;
        max-height: 25px;
        padding: 1px 2px;
        font-size: 8px;
    }
    
    QLineEdit, QTextEdit, QPlainTextEdit {
        min-height: 24px;
        min-width: 60px;
        font-size: 11px;
        padding: 2px 4px;
    }
}

/* Dashboard Card Styles */
QWidget#dashboardCard {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2a2a2a, stop:1 #1e1e1e);
    border: 1px solid rgba(102, 126, 234, 0.3);
    border-radius: 12px;
    padding: 20px;
    margin: 8px;
    min-width: 200px;
    max-width: 300px;
    min-height: 140px;
    max-height: 180px;
}

QWidget#dashboardCard:hover {
    border: 1px solid rgba(102, 126, 234, 0.6);
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #2e2e2e, stop:1 #222222);
}

QLabel#cardTitle {
    color: #cccccc;
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 8px;
}

QLabel#cardValue {
    color: #ffffff;
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 4px;
}

QLabel#cardSubtitle {
    color: #999999;
    font-size: 12px;
    font-weight: 400;
}

/* Portfolio Card - Blue gradient */
QWidget#portfolioCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(102, 126, 234, 0.8), stop:1 rgba(118, 75, 162, 0.8));
    border: 1px solid rgba(102, 126, 234, 0.5);
}

/* Daily P&L Card - Pink gradient */
QWidget#dailyPnlCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(240, 147, 251, 0.8), stop:1 rgba(245, 87, 108, 0.8));
    border: 1px solid rgba(240, 147, 251, 0.5);
}

/* Active Bots Card - Blue gradient */
QWidget#botsCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(79, 172, 254, 0.8), stop:1 rgba(0, 242, 254, 0.8));
    border: 1px solid rgba(79, 172, 254, 0.5);
}

/* Recent Trades Card - Green gradient */
QWidget#tradesCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(67, 233, 123, 0.8), stop:1 rgba(56, 239, 125, 0.8));
    border: 1px solid rgba(67, 233, 123, 0.5);
}
"""

# Dodatkowe ulepszenia czytelności – nakładka na motyw
READABILITY_ENHANCEMENTS = f"""
/* Zakładki – większa czytelność i kontrast */
QTabWidget::pane {{
    border: 1px solid #3a3a3a;
    border-radius: 10px;
    background: #181818;
}}

QTabBar::tab {{
    background: #2b2b2b;
    color: #e6e6e6;
    padding: 12px 22px;
    margin-right: 3px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    font-weight: 600;
    font-size: 14px;
}}

QTabBar::tab:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['primary']}, stop:1 {COLORS['secondary']});
    color: #ffffff;
    font-weight: 700;
    border-bottom: 2px solid {COLORS['primary']};
}}

QTabBar::tab:hover:!selected {{
    background: rgba(102, 126, 234, 0.25);
    color: #ffffff;
    border: 1px solid rgba(102, 126, 234, 0.35);
}}

/* Tabele – naprzemienne wiersze i mocniejsze nagłówki */
QTableWidget {{
    background: #1a1a1a;
    border: 1px solid #3a3a3a;
    border-radius: 10px;
    gridline-color: #2a2a2a;
    font-size: 13px;
    selection-background-color: rgba(102, 126, 234, 0.35);
    alternate-background-color: #242424;
}}

QTableWidget::item {{
    padding: 10px 14px;
    border-bottom: 1px solid #2a2a2a;
    color: #f0f0f0;
}}

QTableWidget::item:selected {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 rgba(102, 126, 234, 0.45),
        stop:1 rgba(118, 75, 162, 0.45));
}}

QHeaderView::section {{
    background: #2a2a2a;
    color: #eaeaea;
    padding: 10px 12px;
    border: none;
    font-weight: 600;
    font-size: 12px;
}}

/* Grupy (QGroupBox) – spójny wygląd */
QGroupBox {{
    color: #ffffff;
    font-weight: 600;
    border: 1px solid #3a3a3a;
    border-radius: 10px;
    margin-top: 12px;
    padding: 12px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}}

/* Etykiety ogólne */
QLabel {{
    color: #eaeaea;
    font-size: 13px;
}}

/* ScrollArea – tło przezroczyste, bez obwódek */
QScrollArea {{
    border: none;
    background: transparent;
}}
"""
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

def apply_theme(name: str = "dark"):
    app = QApplication.instance()
    if app is None:
        return
    pal = QPalette()
    if name == "light":
        pal.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.black)
        pal.setColor(QPalette.ColorRole.Base, QColor("#F5F5F5"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#FFFFFF"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.black)
        pal.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        pal.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.black)
        pal.setColor(QPalette.ColorRole.Button, QColor("#F0F0F0"))
        pal.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.black)
        pal.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#4C8BF5"))
        pal.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    else:
        pal.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        pal.setColor(QPalette.ColorRole.Base, QColor("#121212"))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#1e1e1e"))
        pal.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        pal.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        pal.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        pal.setColor(QPalette.ColorRole.Button, QColor("#2a2a2a"))
        pal.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        pal.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        pal.setColor(QPalette.ColorRole.Highlight, QColor("#7c4dff"))
        pal.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(pal)

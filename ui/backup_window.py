from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox
from PyQt6.QtCore import Qt

class BackupWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Backup & Export")
        self.resize(480, 200)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        lbl = QLabel("Zapisz kopię zapasową konfiguracji i bazy danych do pliku .zip")
        lbl.setWordWrap(True)
        layout.addWidget(lbl)
        btn = QPushButton("Utwórz backup (.zip)")
        btn.clicked.connect(self._do_backup)
        layout.addWidget(btn)

    def _do_backup(self):
        root = Path(__file__).resolve().parents[1]
        cfg_dir = root/'config'
        data_dir = root/'data'
        files = []
        for p in [cfg_dir, data_dir]:
            if p.exists():
                for f in p.rglob('*'):
                    if f.is_file():
                        files.append(f)
        out_path, _ = QFileDialog.getSaveFileName(self, "Zapisz backup", "backup.zip", "ZIP (*.zip)")
        if not out_path:
            return
        zpath = Path(out_path)
        with ZipFile(zpath, 'w', ZIP_DEFLATED) as zf:
            for f in files:
                zf.write(f, arcname=str(f.relative_to(root)))
        QMessageBox.information(self, "Backup", f"Zapisano: {zpath}")

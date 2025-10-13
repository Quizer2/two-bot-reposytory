#!/usr/bin/env python3
"""
Skrypt do automatycznego usuwania problematycznych instrukcji pass z niepoprawnym wcięciem
"""

import re

def fix_pass_statements(file_path):
    """Usuwa problematyczne instrukcje pass z niepoprawnym wcięciem"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Usuń linie zawierające tylko pass z wcięciem większym niż 8 spacji
    lines = content.split('\n')
    fixed_lines = []
    
    for line in lines:
        # Sprawdź czy linia zawiera tylko pass z dużym wcięciem
        if re.match(r'^\s{12,}pass\s*$', line):
            print(f"Usuwam problematyczną linię: '{line}'")
            continue  # Pomiń tę linię
        else:
            fixed_lines.append(line)
    
    # Zapisz naprawiony plik
    fixed_content = '\n'.join(fixed_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print(f"Naprawiono plik: {file_path}")

if __name__ == "__main__":
    fix_pass_statements("f:/new bot 1/app/database.py")
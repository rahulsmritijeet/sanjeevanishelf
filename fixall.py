#!/usr/bin/env python3
"""
Fix all screen files - Replace app.config with app.app_config
"""

import os
from pathlib import Path

# Files to fix
screen_files = [
    'ui/screens/storage_screen.py',
    'ui/screens/selling_screen.py',
    'ui/screens/buying_screen.py',
    'ui/screens/admin_screen.py',
    'ui/screens/payment_screen.py',
    'ui/screens/startup_screen.py',
]

print("🔧 Fixing all screen files...\n")

for file_path in screen_files:
    full_path = Path(file_path)
    
    if not full_path.exists():
        print(f"⚠️  SKIP {file_path} (not found)")
        continue
    
    try:
        # Read file
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace app.config with app.app_config
        original_content = content
        content = content.replace('app_instance.config', 'app_instance.app_config')
        content = content.replace('self.app.config', 'self.app.app_config')
        
        # Write back if changed
        if content != original_content:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✓ FIXED {file_path}")
        else:
            print(f"✓ OK {file_path}")
    
    except Exception as e:
        print(f"✗ ERROR {file_path}: {e}")

print("\n✅ All files fixed!")
print("\nNow run: python main.py")
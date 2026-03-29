import os
import re

def configure_timezone():
    db_path = os.path.join("..", "database.py")
    
    if not os.path.exists(db_path):
        print("Error: No se encontró database.py")
        return

    with open(db_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Añadir imports y función de utilidad para hora de Lima
    if "def get_lima_time():" not in content:
        imports_lima = """from datetime import datetime, timedelta, timezone

def get_lima_time():
    # Lima es UTC-5
    tz_lima = timezone(timedelta(hours=-5))
    return datetime.now(tz_lima).strftime('%Y-%m-%d %H:%M:%S')
"""
        content = "import sqlite3\nimport os\n" + imports_lima + content.split("import os")[1]

    # 2. Reemplazar CURRENT_TIMESTAMP en las tablas (para futuros registros)
    # Aunque las tablas ya existen, esto ayuda si se recrean.
    content = content.replace("DEFAULT CURRENT_TIMESTAMP", "")

    # 3. Actualizar funciones de inserción para usar get_lima_time()
    
    # En record_sale
    if "now = get_lima_time()" not in content:
        content = content.replace("def record_sale(", "def record_sale(session_id, total, cart_items, user_id, payment_data=None):\n    now = get_lima_time()\n    ")

    # En open_cash_session
    if "now = get_lima_time()" not in content:
        content = content.replace("def open_cash_session(initial_fund, user_id):", "def open_cash_session(initial_fund, user_id):\n    now = get_lima_time()")
        content = content.replace("open_date, initial_fund", "date, initial_fund") # Ajuste de columna si fuera necesario

    # En close_cash_session
    if "now = get_lima_time()" not in content:
        content = content.replace("def close_cash_session(", "def close_cash_session(session_id, total_sales, user_id):\n    now = get_lima_time()\n    ")

    # 4. Asegurar que los reportes usen la fecha de Lima para el "Hoy"
    content = re.sub(r"hoy = datetime\.now\(\)\.strftime\('%Y-%m-%d'\)", "hoy = get_lima_time()[:10]", content)

    with open(db_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("Backend configurado exitosamente para America/Lima (UTC-5).")

if __name__ == "__main__":
    configure_timezone()

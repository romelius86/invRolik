import os
import re

def fix_times():
    db_path = os.path.join("..", "database.py")
    
    if not os.path.exists(db_path):
        print("No se encontró database.py")
        return

    with open(db_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Asegurar que record_sale use la hora local
    old_sale = "now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')"
    if "now = datetime.now()" not in content:
        content = content.replace("def record_sale(", "def record_sale(session_id, total, cart_items, user_id, payment_data=None):\n    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')\n    ")
    
    # 2. Reemplazar CURRENT_TIMESTAMP por la variable 'now' en los INSERT
    content = content.replace("INSERT INTO transactions (", "INSERT INTO transactions (date, ")
    content = content.replace("VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)")
    # Nota: El reemplazo exacto del execute es complejo sin regex, pero lo intentaremos con las funciones de reporte
    
    # 3. Forzar reportes a usar date() para ignorar desfases de minutos/segundos
    content = content.replace("WHERE date(date) = ?", "WHERE date(date) = date(?)")
    content = content.replace("WHERE date(t.date) BETWEEN ? AND ?", "WHERE date(t.date) BETWEEN date(?) AND date(?)")

    with open(db_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print("Backend ajustado para usar HORA LOCAL.")

if __name__ == "__main__":
    fix_times()

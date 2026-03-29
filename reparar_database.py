import os

def fix():
    path = os.path.join("..", "database.py")
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    skip = False
    for i in range(len(lines)):
        line = lines[i]
        
        # Corregir la definición de la función duplicada
        if "def record_sale(" in line and "payment_data=None):" in line:
            new_lines.append("def record_sale(session_id, total, cart_items, user_id, payment_data=None):\n")
            new_lines.append("    now = get_lima_time()\n")
            skip = True
            continue
        
        if skip and "session_id, total, cart_items, user_id, payment_data=None):" in line:
            skip = False
            continue
            
        # Corregir el paso de parámetros en el INSERT de transacciones
        if "session_id, total, user_id," in line and "now," not in line and "cursor.execute" not in line:
            # Esta es la parte de los valores de la tupla
            if "payment_data.get('metodo_pago'" not in lines[i-1]: # Aseguramos que es la tupla de parámetros
                 line = line.replace("session_id, total, user_id,", "now, session_id, total, user_id,")
        
        new_lines.append(line)

    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Archivo database.py reparado exitosamente.")

if __name__ == "__main__":
    fix()

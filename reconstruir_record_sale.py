import os

def final_fix():
    path = os.path.join("..", "database.py")
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Definición limpia de la función record_sale
    clean_record_sale = """def record_sale(session_id, total, cart_items, user_id, payment_data=None):
    now = get_lima_time()
    \"\"\"Registra una venta con datos del cliente, métodos de pago y comprobante.\"\"\"
    payment_data = payment_data or {}
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Generar correlativo si es necesario
        tipo_comp = payment_data.get('tipo_comprobante', 'TICKET').upper()
        correlativo = generar_correlativo_comprobante(tipo_comp)

        # 1. Registrar la transacción con datos del cliente
        cursor.execute(\"\"\"
            INSERT INTO transactions (date, 
                session_id, total, user_id, metodo_pago, tipo_comprobante, 
                correlativo, monto_pagado, vuelto, cliente_nombre, cliente_documento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        \"\"\", (
            now, session_id, total, user_id, 
            payment_data.get('metodo_pago', 'EFECTIVO'),
            tipo_comp, correlativo,
            payment_data.get('monto_pagado', total),
            payment_data.get('vuelto', 0.0),
            payment_data.get('cliente_nombre', 'PÚBLICO EN GENERAL'),
            payment_data.get('cliente_documento', '00000000')
        ))
        transaction_id = cursor.lastrowid
        
        # 2. Detalles y Stock
        for item in cart_items:
            # item = (producto_codigo, quantity, unit_price)
            cursor.execute("INSERT INTO transaction_details (transaction_id, producto_codigo, quantity, unit_price) VALUES (?, ?, ?, ?)", (transaction_id, item[0], item[1], item[2]))
            
            # SOLO DESCONTAR STOCK SI NO ES PROFORMA
            if tipo_comp != "PROFORMA":
                cursor.execute("UPDATE products SET stock = stock - ?, stock_actual = stock_actual - ? WHERE codigo = ?", (item[1], item[1], item[0]))

        # 3. Comisiones
        seller = get_user_by_id(user_id)
        if seller and seller['commission_rate'] > 0:"""

    # Usamos regex o un reemplazo de bloque grande para limpiar el desastre
    import re
    # Buscamos desde 'def record_sale' hasta antes de las comisiones
    pattern = r"def record_sale\(session_id, total, cart_items, user_id, payment_data=None\):.*?if seller and seller\['commission_rate'\] > 0:"
    new_content = re.sub(pattern, clean_record_sale, content, flags=re.DOTALL)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Función record_sale reconstruida y corregida.")

if __name__ == "__main__":
    final_fix()

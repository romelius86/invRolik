import os

def patch_backend():
    db_path = os.path.join("..", "database.py")
    api_path = os.path.join("..", "servidor_api", "main_api.py")

    print("--- Iniciando actualización del Backend ROLIK ERP ---")

    # 1. Parchear database.py
    if os.path.exists(db_path):
        with open(db_path, "r", encoding="utf-8") as f:
            db_content = f.read()
        
        if "def get_report_sales_grouped" not in db_content:
            new_db_functions = """
def get_report_sales_by_range(start_date, end_date):
    \"\"\"Ventas detalladas por rango con cálculo de utilidad/ganancia y desglose por método.\"\"\"
    conn = get_connection()
    query_resumen = \"\"\"
        SELECT 
            SUM(t.total) as ingresos_brutos,
            SUM(t.total / 1.18 * 0.18) as total_igv,
            SUM(t.total / 1.18) as total_neto,
            SUM((td.unit_price - p.precio_compra) * td.quantity) as ganancia_estimada
        FROM transactions t
        JOIN transaction_details td ON t.id = td.transaction_id
        JOIN products p ON td.producto_codigo = p.codigo
        WHERE date(t.date) BETWEEN ? AND ?
    \"\"\"
    res = conn.execute(query_resumen, (start_date, end_date)).fetchone()
    res_dict = dict(res) if res else {}

    query_metodos = \"\"\"
        SELECT metodo_pago, SUM(total) as total
        FROM transactions
        WHERE date(date) BETWEEN ? AND ?
        GROUP BY metodo_pago
    \"\"\"
    metodos = conn.execute(query_metodos, (start_date, end_date)).fetchall()
    res_dict['por_metodo'] = {m['metodo_pago']: m['total'] for m in metodos}
    conn.close()
    return res_dict

def get_report_sales_grouped(start_date, end_date, agrupar_por='producto', ordenar_por='cantidad'):
    \"\"\"Lista de ventas agrupadas por producto o categoría con rentabilidad.\"\"\"
    conn = get_connection()
    group_col = "p.nombre" if agrupar_por == 'producto' else "COALESCE(p.categoria, 'SIN CATEGORIA')"
    order_col = "cant_vendida" if ordenar_por == 'cantidad' else "total_generado"
    
    query = f\"\"\"
        SELECT 
            {group_col} as nombre,
            SUM(td.quantity) as cant_vendida,
            SUM(td.unit_price * td.quantity) as total_generado,
            SUM(p.precio_compra * td.quantity) as costo_total
        FROM transaction_details td
        JOIN products p ON td.producto_codigo = p.codigo
        JOIN transactions t ON td.transaction_id = t.id
        WHERE date(t.date) BETWEEN ? AND ?
        GROUP BY {group_col}
        ORDER BY {order_col} DESC
    \"\"\"
    res = conn.execute(query, (start_date, end_date)).fetchall()
    conn.close()
    return res
"""
            # Reemplazar la versión vieja y añadir la nueva
            import re
            # Buscamos la función vieja para quitarla si existe
            db_content = re.sub(r'def get_report_sales_by_range\(start_date, end_date\):.*?return res', '', db_content, flags=re.DOTALL)
            
            with open(db_path, "a", encoding="utf-8") as f:
                f.write(new_db_functions)
            print("[OK] database.py actualizado.")
        else:
            print("[INFO] database.py ya estaba actualizado.")
    else:
        print("[ERROR] No se encontró database.py en la carpeta superior.")

    # 2. Parchear main_api.py
    if os.path.exists(api_path):
        with open(api_path, "r", encoding="utf-8") as f:
            api_content = f.read()
        
        if "/reportes/ventas-agrupadas" not in api_content:
            new_api_endpoint = """
@app.get("/reportes/ventas-agrupadas")
def obtener_ventas_agrupadas(inicio: str, fin: str, agrupar_por: str = 'producto', ordenar_por: str = 'cantidad'):
    try:
        res = database.get_report_sales_grouped(inicio, fin, agrupar_por, ordenar_por)
        return [dict(r) for r in res]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""
            # Insertar antes del bloque main
            if 'if __name__ == "__main__":' in api_content:
                api_content = api_content.replace('if __name__ == "__main__":', new_api_endpoint + '\nif __name__ == "__main__":')
            else:
                api_content += new_api_endpoint
                
            with open(api_path, "w", encoding="utf-8") as f:
                f.write(api_content)
            print("[OK] main_api.py actualizado.")
        else:
            print("[INFO] main_api.py ya estaba actualizado.")
    else:
        print("[ERROR] No se encontró servidor_api/main_api.py.")

    print("--- Proceso finalizado. Reinicia tu servidor de Python. ---")

if __name__ == "__main__":
    patch_backend()

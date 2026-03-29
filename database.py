import sqlite3
import os
import zipfile
import hashlib
from datetime import datetime, timedelta, timezone

def hash_password(password):
    """Genera un hash seguro para la contraseña."""
    if not password: return ""
    # SHA-256 es un estándar de seguridad robusto
    return hashlib.sha256(password.encode()).hexdigest()

def get_lima_time():
    # Lima es UTC-5
    tz_lima = timezone(timedelta(hours=-5))
    return datetime.now(tz_lima).strftime('%Y-%m-%d %H:%M:%S')

from datetime import datetime

# Obtener la ruta absoluta de la carpeta donde está este archivo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "erp_system.db")

def get_connection():
    """Obtiene una conexión a la base de datos con modo WAL y llaves foráneas habilitadas."""
    conn = sqlite3.connect(DB_NAME, timeout=10) # Mayor timeout para evitar "database is locked"
    conn.row_factory = sqlite3.Row  # Devuelve filas como diccionarios
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    """Inicializa la base de datos creando las tablas solo si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    # Tabla de Proveedores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            ruc_dni TEXT,
            direccion TEXT,
            telefono TEXT,
            email TEXT,
            deleted_at TIMESTAMP DEFAULT NULL
        )
    ''')
    # Crear índice único para RUC si no existe (para soportar ON CONFLICT)
    try:
        cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_supplier_ruc ON suppliers(ruc_dni)")
    except sqlite3.OperationalError: pass

    # Añadir columnas a suppliers si no existen
    for col, col_type in [("ruc_dni", "TEXT"), ("direccion", "TEXT"), ("telefono", "TEXT"), ("email", "TEXT"), ("deleted_at", "TIMESTAMP DEFAULT NULL")]:
        try:
            cursor.execute(f"ALTER TABLE suppliers ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError: pass

    # Tabla de Productos (Estructura Profesional)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            fabricante TEXT,
            marca TEXT,
            categoria TEXT,
            descripcion TEXT,
            precio_venta REAL DEFAULT 0.0,
            precio_compra REAL DEFAULT 0.0, -- Último precio de compra
            costo_promedio REAL DEFAULT 0.0, -- Valor contable calculado
            unidad TEXT,
            stock_actual REAL DEFAULT 0.0,
            stock_minimo REAL DEFAULT 5.0,
            stock_maximo REAL DEFAULT 100.0,
            proveedor_id INTEGER,
            fecha_ingreso TIMESTAMP,
            deleted_at TIMESTAMP DEFAULT NULL,
            FOREIGN KEY (proveedor_id) REFERENCES suppliers(id)
        )
    ''')

    # Asegurar que todas las columnas necesarias existan (Migración forzada)
    columnas_necesarias = [
        ("codigo", "TEXT UNIQUE"),
        ("marca", "TEXT"),
        ("stock_actual", "REAL DEFAULT 0.0"),
        ("stock_maximo", "REAL DEFAULT 100.0"),
        ("costo_promedio", "REAL DEFAULT 0.0"),
        ("descripcion", "TEXT"),
        ("fecha_actualizacion_precio", "TIMESTAMP"),
        ("unidad", "TEXT DEFAULT 'Und'"),
        ("deleted_at", "TIMESTAMP DEFAULT NULL")
    ]
    for col, col_type in columnas_necesarias:
        try:
            cursor.execute(f"ALTER TABLE products ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass # La columna ya existe
    
    conn.commit()

    # Tabla de Órdenes de Compra
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_oc TEXT UNIQUE,
            comprobante_proveedor TEXT, -- Nueva columna para Guía o Factura del proveedor
            proveedor_id INTEGER,
            fecha_pedido TIMESTAMP ,
            fecha_llegada TIMESTAMP,
            fecha_estimada DATE,
            estado TEXT DEFAULT 'PENDIENTE',
            condicion_pago TEXT,
            lugar_entrega TEXT,
            responsable_recibe TEXT,
            tipo_entrega TEXT,
            subtotal REAL DEFAULT 0.0,
            igv REAL DEFAULT 0.0,
            total REAL DEFAULT 0.0,
            FOREIGN KEY (proveedor_id) REFERENCES suppliers(id)
        )
    ''')

    # Añadir nuevas columnas a purchase_orders si no existen
    new_po_cols = [
        ("numero_oc", "TEXT UNIQUE"), ("comprobante_proveedor", "TEXT"), ("fecha_estimada", "DATE"), 
        ("condicion_pago", "TEXT"), ("lugar_entrega", "TEXT"), 
        ("responsable_recibe", "TEXT"), ("tipo_entrega", "TEXT"), 
        ("subtotal", "REAL DEFAULT 0.0"), ("igv", "REAL DEFAULT 0.0"), 
        ("total", "REAL DEFAULT 0.0")
    ]
    for col, col_type in new_po_cols:
        try:
            cursor.execute(f"ALTER TABLE purchase_orders ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError: pass
    
    # Detalle de Órdenes de Compra
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS purchase_order_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER,
            producto_codigo TEXT,
            cantidad INTEGER,
            precio_compra_unitario REAL,
            FOREIGN KEY (pedido_id) REFERENCES purchase_orders(id),
            FOREIGN KEY (producto_codigo) REFERENCES products(codigo)
        )
    ''')

    # Tablas de Ventas y Caja
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            open_date TIMESTAMP ,
            close_date TIMESTAMP,
            initial_fund REAL DEFAULT 0.0,
            total_sales REAL DEFAULT 0.0,
            status TEXT DEFAULT 'OPEN'
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP ,
            session_id INTEGER,
            total REAL,
            metodo_pago TEXT, -- Efectivo, Tarjeta, Yape, Mixto, etc.
            tipo_comprobante TEXT, -- Boleta, Factura, Ticket
            correlativo TEXT, -- B001-00001, etc.
            monto_pagado REAL DEFAULT 0.0,
            vuelto REAL DEFAULT 0.0,
            user_id INTEGER,
            FOREIGN KEY (session_id) REFERENCES cash_sessions(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Añadir columnas si no existen (migración)
    for col, col_type in [
        ("metodo_pago", "TEXT"), ("tipo_comprobante", "TEXT"), 
        ("correlativo", "TEXT"), ("monto_pagado", "REAL"), 
        ("vuelto", "REAL"), ("cliente_nombre", "TEXT"), 
        ("cliente_documento", "TEXT"), ("cliente_direccion", "TEXT"),
        ("cliente_telefono", "TEXT"), ("cliente_email", "TEXT"),
        ("status", "TEXT DEFAULT 'COMPLETED'"), # Nueva columna para anulación
        ("voided_by_user_id", "INTEGER"),        # Quién anuló
        ("void_reason", "TEXT")                  # Por qué anuló
    ]:
        try:
            cursor.execute(f"ALTER TABLE transactions ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError: pass

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaction_details (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER,
            producto_codigo TEXT,
            quantity INTEGER,
            unit_price REAL,
            unidad_venta TEXT, -- Nueva columna: registra si fue Unidad, Docena, etc.
            FOREIGN KEY (transaction_id) REFERENCES transactions(id),
            FOREIGN KEY (producto_codigo) REFERENCES products(codigo)
        )
    ''')
    
    # Migración: Asegurar que la columna existe
    try:
        cursor.execute("ALTER TABLE transaction_details ADD COLUMN unidad_venta TEXT")
    except sqlite3.OperationalError: pass
    
    # Tabla de Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'seller')),
            is_active INTEGER NOT NULL DEFAULT 1
        )
    ''')

    # Crear usuarios por defecto si no existen
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('admin', hash_password('admin123'), 'admin'))
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ('vendedor', hash_password('vendedor123'), 'seller'))

    # Añadir columna is_active a users si no existe
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1")
    except sqlite3.OperationalError:
        pass # La columna ya existe

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN is_discount_enabled INTEGER NOT NULL DEFAULT 0") # Nuevo campo
        cursor.execute("ALTER TABLE users ADD COLUMN max_discount_percentage INTEGER NOT NULL DEFAULT 0") # Nuevo campo
        cursor.execute("ALTER TABLE users ADD COLUMN commission_rate REAL NOT NULL DEFAULT 0.0") # Nuevo campo
    except sqlite3.OperationalError:
        pass # La columna ya existe

    # Añadir columna user_id a transactions si no existe
    try:
        cursor.execute("ALTER TABLE transactions ADD COLUMN user_id INTEGER REFERENCES users(id)")
    except sqlite3.OperationalError:
        pass

    # Añadir columnas opened_by_user_id y closed_by_user_id a cash_sessions si no existen
    try:
        cursor.execute("ALTER TABLE cash_sessions ADD COLUMN opened_by_user_id INTEGER REFERENCES users(id)")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE cash_sessions ADD COLUMN closed_by_user_id INTEGER REFERENCES users(id)")
    except sqlite3.OperationalError:
        pass

    # Tabla de Comisiones Ganadas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS commissions_earned (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            transaction_id INTEGER NOT NULL,
            commission_amount REAL NOT NULL,
            date TIMESTAMP ,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
    ''')

    # Tabla de Clientes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            documento TEXT UNIQUE,
            nombre TEXT,
            direccion TEXT,
            telefono TEXT,
            email TEXT,
            deleted_at TIMESTAMP DEFAULT NULL
        )
    ''')

    # Asegurar que la columna deleted_at existe (migración)
    try:
        cursor.execute("ALTER TABLE customers ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL")
    except sqlite3.OperationalError:
        pass

    # --- Permisos ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS permissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_permissions (
            user_id INTEGER,
            permission_id INTEGER,
            PRIMARY KEY (user_id, permission_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
        )
    ''')

    # Tabla de Movimientos de Caja (Ingresos/Retiros manuales)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cash_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            user_id INTEGER,
            tipo TEXT CHECK(tipo IN ('INGRESO', 'RETIRO')),
            monto REAL NOT NULL,
            descripcion TEXT,
            fecha TIMESTAMP ,
            FOREIGN KEY (session_id) REFERENCES cash_sessions(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Poblar tabla de permisos si está vacía
    cursor.execute("SELECT COUNT(*) FROM permissions")
    if cursor.fetchone()[0] == 0:
        all_permissions = [
            ('user.view', 'Ver la lista de usuarios'),
            ('user.create', 'Crear nuevos usuarios'),
            ('user.edit', 'Editar usuarios existentes'),
            ('user.delete', 'Eliminar usuarios'),
            ('user.manage_permissions', 'Asignar permisos a usuarios'),
            ('product.view', 'Ver inventario'),
            ('product.create', 'Crear nuevos productos'),
            ('product.edit', 'Editar productos'),
            ('product.delete', 'Eliminar productos'),
            ('product.import', 'Importar productos desde archivo'),
            ('purchase_order.view', 'Ver órdenes de compra'),
            ('purchase_order.create', 'Crear órdenes de compra'),
            ('purchase_order.receive', 'Marcar órdenes de compra como recibidas'),
            ('pos.use', 'Usar el punto de venta'),
            ('pos.apply_discount', 'Aplicar descuentos en el POS'),
            ('cash.manage', 'Abrir y cerrar caja'),
            ('report.view.sales', 'Ver reporte de ventas'),
            ('report.view.cash', 'Ver reporte de caja'),
            ('report.view.commissions', 'Ver reporte de comisiones'),
            ('sale.void', 'Anular ventas y recibos')
        ]
        cursor.executemany("INSERT INTO permissions (name, description) VALUES (?, ?)", all_permissions)

        # Asignar todos los permisos al usuario 'admin' por defecto
        admin_user = cursor.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()
        if admin_user:
            permissions_ids = cursor.execute("SELECT id FROM permissions").fetchall()
            user_perms_to_insert = [(admin_user['id'], perm_id['id']) for perm_id in permissions_ids]
            cursor.executemany("INSERT INTO user_permissions (user_id, permission_id) VALUES (?, ?)", user_perms_to_insert)
        
    # Tabla de Unidades de Medida / Presentaciones por Producto
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS product_units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_codigo TEXT NOT NULL,
            nombre_unidad TEXT NOT NULL,
            factor_conversion REAL NOT NULL DEFAULT 1.0,
            precio_venta REAL NOT NULL,
            FOREIGN KEY (producto_codigo) REFERENCES products(codigo) ON DELETE CASCADE
        )
    ''')

    # --- Configuración del Sistema ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')
    # Valor por defecto: 3 días de retención en papelera
    cursor.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('trash_retention_days', '3')")

    conn.commit()
    conn.close()

def get_setting(key, default=None):
    """Obtiene un valor de configuración del sistema."""
    conn = get_connection()
    try:
        res = conn.execute("SELECT value FROM system_settings WHERE key = ?", (key,)).fetchone()
        return res['value'] if res else default
    finally:
        conn.close()

def update_setting(key, value):
    """Actualiza un valor de configuración."""
    conn = get_connection()
    try:
        conn.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
    finally:
        conn.close()

def get_report_sales_by_range_filtered(start_date, end_date, payment_method=None):
    """Ventas detalladas por rango con filtrado opcional por método de pago."""
    conn = get_connection()
    query_resumen = """
        SELECT 
            COALESCE(SUM(t.total), 0) as ingresos_brutos,
            COALESCE(SUM(t.total / 1.18 * 0.18), 0) as total_igv,
            COALESCE(SUM(t.total / 1.18), 0) as total_neto,
            COALESCE(SUM((td.unit_price - p.precio_compra) * td.quantity), 0) as ganancia_estimada
        FROM transactions t
        JOIN transaction_details td ON t.id = td.transaction_id
        JOIN products p ON td.producto_codigo = p.codigo
        WHERE date(t.date) BETWEEN date(?) AND date(?)
          AND t.status != 'VOIDED'
    """
    params = [start_date, end_date]
    if payment_method and payment_method != "TODOS":
        query_resumen += " AND t.metodo_pago = ?"
        params.append(payment_method)
    
    res = conn.execute(query_resumen, params).fetchone()
    res_dict = dict(res) if res else {}

    query_metodos = """
        SELECT metodo_pago, SUM(total) as total
        FROM transactions
        WHERE (date(date) BETWEEN date(?) AND date(?))
          AND status != 'VOIDED'
    """
    params_metodos = [start_date, end_date]
    if payment_method and payment_method != "TODOS":
        query_metodos += " AND metodo_pago = ?"
        params_metodos.append(payment_method)
    
    query_metodos += " GROUP BY metodo_pago"
    metodos = conn.execute(query_metodos, params_metodos).fetchall()
    res_dict['por_metodo'] = {m['metodo_pago']: m['total'] for m in metodos}
    conn.close()
    return res_dict

def get_report_sales_by_product_filtered(start_date, end_date, payment_method=None):
    """Lista de productos vendidos con desglose por método de pago y rentabilidad."""
    conn = get_connection()
    query = """
        SELECT 
            p.nombre,
            p.codigo,
            SUM(td.quantity) as cant_vendida,
            COALESCE(SUM(td.unit_price * td.quantity), 0.0) as total_generado,
            COALESCE(SUM(CASE WHEN t.metodo_pago = 'EFECTIVO' THEN td.unit_price * td.quantity ELSE 0 END), 0.0) as efectivo,
            COALESCE(SUM(CASE WHEN t.metodo_pago = 'TRANSFERENCIA' THEN td.unit_price * td.quantity ELSE 0 END), 0.0) as transferencia,
            COALESCE(SUM(CASE WHEN t.metodo_pago = 'YAPE/PLIN' THEN td.unit_price * td.quantity ELSE 0 END), 0.0) as yape_plin,
            COALESCE(SUM((td.unit_price - p.precio_compra) * td.quantity), 0.0) as margen_ganancia
        FROM transaction_details td
        JOIN products p ON td.producto_codigo = p.codigo
        JOIN transactions t ON td.transaction_id = t.id
        WHERE (date(t.date) BETWEEN date(?) AND date(?))
          AND t.status != 'VOIDED'
    """
    params = [start_date, end_date]
    if payment_method and payment_method != "TODOS":
        query += " AND t.metodo_pago = ?"
        params.append(payment_method)
    
    query += " GROUP BY p.codigo ORDER BY total_generado DESC"
    res = conn.execute(query, params).fetchall()
    conn.close()
    return res

def get_product_customer_sales(codigo, start_date=None, end_date=None):
    """Obtiene los clientes que han comprado un producto específico, ordenados por cantidad descendente."""
    conn = get_connection()
    query = """
        SELECT 
            t.cliente_nombre as cliente_nombre,
            t.cliente_documento as cliente_documento,
            SUM(td.quantity) as cantidad_total,
            SUM(td.quantity * td.unit_price) as monto_total,
            MAX(t.date) as ultima_vez_comprado
        FROM transaction_details td
        JOIN transactions t ON td.transaction_id = t.id
        WHERE td.producto_codigo = ? AND t.status != 'VOIDED'
    """
    params = [codigo]
    if start_date and end_date:
        query += " AND (date(t.date) BETWEEN date(?) AND date(?)) "
        params.extend([start_date, end_date])
    
    query += " GROUP BY t.cliente_documento ORDER BY cantidad_total DESC"
    res = conn.execute(query, params).fetchall()
    conn.close()
    return res

def get_report_sales_by_customer(start_date, end_date):
    """Obtiene el acumulado de compras por cada cliente en un rango de fechas."""
    conn = get_connection()
    query = """
        SELECT 
            cliente_nombre as nombre,
            cliente_documento as documento,
            COUNT(id) as num_compras,
            SUM(total) as total_comprado,
            MAX(date) as ultima_compra
        FROM transactions
        WHERE (date(date) BETWEEN date(?) AND date(?))
          AND status != 'VOIDED'
        GROUP BY cliente_documento
        ORDER BY total_comprado DESC
    """
    res = conn.execute(query, (start_date, end_date)).fetchall()
    conn.close()
    return res

def get_customer_product_sales(documento, start_date=None, end_date=None):
    """Obtiene los productos que ha comprado un cliente específico, ordenados por cantidad descendente."""
    conn = get_connection()
    query = """
        SELECT 
            p.nombre as producto_nombre,
            p.codigo as producto_codigo,
            SUM(td.quantity) as cantidad_total,
            SUM(td.quantity * td.unit_price) as monto_total,
            MAX(t.date) as ultima_vez_comprado
        FROM transaction_details td
        JOIN products p ON td.producto_codigo = p.codigo
        JOIN transactions t ON td.transaction_id = t.id
        WHERE t.cliente_documento = ? AND t.status != 'VOIDED'
    """
    params = [documento]
    if start_date and end_date:
        query += " AND (date(t.date) BETWEEN date(?) AND date(?)) "
        params.extend([start_date, end_date])
    
    query += " GROUP BY p.codigo ORDER BY cantidad_total DESC"
    res = conn.execute(query, params).fetchall()
    conn.close()
    return res

# --- Funciones de Usuarios ---
def authenticate_user(username, password):
    """Verifica si el usuario y la contraseña son correctos y si está activo.
       Compara el hash de la contraseña proporcionada con el almacenado en la BD.
    """
    conn = get_connection()
    # Encriptamos la contraseña ingresada para compararla con el código secreto de la BD
    hashed = hash_password(password)
    user = conn.execute("SELECT id, username, role, is_active, is_discount_enabled, max_discount_percentage, commission_rate FROM users WHERE username = ? AND password = ? AND is_active = 1", (username, hashed)).fetchone()
    
    if user:
        user_data = dict(user)
        user_data['permissions'] = get_user_permissions(user_data['id'])
        conn.close()
        return user_data
    
    conn.close()
    return None

def get_all_users():
    """Devuelve la lista de todos los usuarios, incluyendo su estado, configuración de descuento y tasa de comisión."""
    conn = get_connection()
    users = conn.execute("SELECT id, username, role, is_active, is_discount_enabled, max_discount_percentage, commission_rate FROM users").fetchall()
    conn.close()
    return users

def get_user_by_id(user_id):
    """Obtiene un usuario específico por su ID, incluyendo su configuración de descuento y tasa de comisión."""
    conn = get_connection()
    user = conn.execute("SELECT id, username, role, is_active, is_discount_enabled, max_discount_percentage, commission_rate FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def add_user(username, password, role, is_discount_enabled=0, max_discount_percentage=0, commission_rate=0.0):
    """Crea un nuevo usuario (activo por defecto) con configuración de descuento y tasa de comisión."""
    conn = get_connection()
    try:
        conn.execute("INSERT INTO users (username, password, role, is_discount_enabled, max_discount_percentage, commission_rate) VALUES (?, ?, ?, ?, ?, ?)", (username, password, role, is_discount_enabled, max_discount_percentage, commission_rate))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_user(user_id, username, role, is_discount_enabled, max_discount_percentage, commission_rate):
    """Actualiza el nombre de usuario, el rol, la configuración de descuento y la tasa de comisión."""
    conn = get_connection()
    try:
        conn.execute("UPDATE users SET username = ?, role = ?, is_discount_enabled = ?, max_discount_percentage = ?, commission_rate = ? WHERE id = ?", (username, role, is_discount_enabled, max_discount_percentage, commission_rate, user_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # El nuevo username ya existe
    finally:
        conn.close()

def update_user_password(user_id, new_password):
    """Actualiza la contraseña de un usuario."""
    conn = get_connection()
    conn.execute("UPDATE users SET password = ? WHERE id = ?", (new_password, user_id))
    conn.commit()
    conn.close()

def get_all_permissions():
    """Obtiene todos los permisos disponibles en el sistema."""
    conn = get_connection()
    permissions = conn.execute("SELECT id, name, description FROM permissions ORDER BY name").fetchall()
    conn.close()
    return permissions

def get_user_permissions(user_id):
    """Obtiene los nombres de todos los permisos asignados a un usuario."""
    conn = get_connection()
    perms = conn.execute("""
        SELECT p.name
        FROM user_permissions up
        JOIN permissions p ON up.permission_id = p.id
        WHERE up.user_id = ?
    """, (user_id,)).fetchall()
    conn.close()
    return {p['name'] for p in perms} # Devuelve un set para búsquedas rápidas

def update_user_permissions(user_id, permission_ids_to_set):
    """Actualiza los permisos de un usuario, reemplazando los existentes."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Borrar todos los permisos actuales del usuario
        cursor.execute("DELETE FROM user_permissions WHERE user_id = ?", (user_id,))
        
        # 2. Insertar los nuevos permisos
        if permission_ids_to_set:
            data_to_insert = [(user_id, perm_id) for perm_id in permission_ids_to_set]
            cursor.executemany("INSERT INTO user_permissions (user_id, permission_id) VALUES (?, ?)", data_to_insert)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def set_user_active_status(user_id, is_active):
    """Activa o desactiva un usuario."""
    conn = get_connection()
    conn.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    """Elimina un usuario por ID."""
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_suppliers_full():
    """Obtiene la lista completa de proveedores activos."""
    conn = get_connection()
    suppliers = conn.execute("SELECT * FROM suppliers WHERE deleted_at IS NULL ORDER BY nombre ASC").fetchall()
    conn.close()
    return suppliers

def get_supplier_by_id(supplier_id):
    """Obtiene un proveedor específico por su ID."""
    conn = get_connection()
    supplier = conn.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,)).fetchone()
    conn.close()
    return supplier

def update_supplier(supplier_id, data):
    """Actualiza los datos de un proveedor existente."""
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE suppliers
            SET nombre = ?, ruc_dni = ?, direccion = ?, telefono = ?, email = ?
            WHERE id = ?
        """, (
            data['nombre'].upper(),
            data.get('ruc_dni'),
            data.get('direccion', '').upper(),
            data.get('telefono'),
            data.get('email', '').lower(),
            supplier_id
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al actualizar proveedor: {e}")
        return False
    finally:
        conn.close()

def add_or_update_supplier(data):
    """Guarda o actualiza la información de un proveedor."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        sup_id = data.get('id')
        if sup_id:
            cursor.execute('''
                UPDATE suppliers
                SET ruc_dni = ?, nombre = ?, direccion = ?, telefono = ?, email = ?
                WHERE id = ?
            ''', (
                str(data['ruc_dni']),
                str(data['nombre']).upper(),
                str(data.get('direccion') or '').upper(),
                str(data.get('telefono') or ''),
                str(data.get('email') or '').lower(),
                sup_id
            ))
            if cursor.rowcount > 0:
                conn.commit()
                return True

        # Si no hay ID o no se encontró el registro para actualizar, insertar
        cursor.execute('''
            INSERT INTO suppliers (ruc_dni, nombre, direccion, telefono, email)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(ruc_dni) DO UPDATE SET
                nombre=excluded.nombre,
                direccion=excluded.direccion,
                telefono=excluded.telefono,
                email=excluded.email
        ''', (
            str(data['ruc_dni']),
            str(data['nombre']).upper(),
            str(data.get('direccion') or '').upper(),
            str(data.get('telefono') or ''),
            str(data.get('email') or '').lower()
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error en add_or_update_supplier: {e}")
        raise e
    finally:
        conn.close()
def delete_supplier(supplier_id):
    """Realiza un borrado lógico (soft delete) del proveedor usando la configuración de días."""
    conn = get_connection()
    try:
        # Verificar si tiene órdenes de compra activas
        has_purchases = conn.execute("SELECT 1 FROM purchase_orders WHERE proveedor_id = ?", (supplier_id,)).fetchone()
        if has_purchases:
            raise ValueError("No se puede eliminar el proveedor porque tiene órdenes de compra registradas. Intente desactivarlo o déjelo en el sistema para mantener la integridad.")

        now = get_lima_time()
        days = get_setting('trash_retention_days', '3')
        
        conn.execute("UPDATE suppliers SET deleted_at = ? WHERE id = ?", (now, supplier_id))
        conn.commit()
        
        # Limpieza automática basada en la configuración
        conn.execute(f"DELETE FROM suppliers WHERE deleted_at IS NOT NULL AND deleted_at < datetime('now', '-{days} days')")
        conn.commit()
        return True
    except Exception as e:
        raise e
    finally:
        conn.close()

def restore_supplier(supplier_id):
    """Restaura un proveedor de la papelera."""
    conn = get_connection()
    try:
        conn.execute("UPDATE suppliers SET deleted_at = NULL WHERE id = ?", (supplier_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_deleted_suppliers():
    """Obtiene proveedores eliminados recientemente."""
    conn = get_connection()
    try:
        query = "SELECT * FROM suppliers WHERE deleted_at IS NOT NULL AND deleted_at > datetime('now', '-3 days') ORDER BY deleted_at DESC"
        res = conn.execute(query).fetchall()
        conn.close()
        return res
    except Exception:
        conn.close()
        return []

# --- Funciones de Caja y Ventas ---
def get_active_session():
    """Obtiene la sesión de caja activa, si existe."""
    conn = get_connection()
    session = conn.execute("SELECT * FROM cash_sessions WHERE status = 'OPEN' ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    return session

def open_cash_session(initial_fund, user_id):
    """Inicia una nueva sesión de caja usando la hora local."""
    conn = get_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("INSERT INTO cash_sessions (open_date, initial_fund, status, opened_by_user_id) VALUES (?, ?, 'OPEN', ?)", (now, initial_fund, user_id))
    conn.commit()
    conn.close()

def close_cash_session(session_id, total_sales, user_id):
    """Cierra la sesión de caja activa usando la hora local y genera un respaldo."""
    conn = get_connection()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("UPDATE cash_sessions SET close_date = ?, total_sales = ?, status = 'CLOSED', closed_by_user_id = ? WHERE id = ?",
                   (now, total_sales, user_id, session_id))
    conn.commit()
    conn.close()
    
    # DISPARAR RESPALDO AUTOMÁTICO AL CERRAR CAJA
    print("Iniciando respaldo automático por cierre de caja...")
    run_backup_professional()

def get_sales_for_session(session_id):
    """Calcula el total de ventas para una sesión."""
    conn = get_connection()
    total = conn.execute("SELECT SUM(total) FROM transactions WHERE session_id = ?", (session_id,)).fetchone()[0]
    conn.close()
    return total or 0.0

def get_all_purchase_orders():
    """Obtiene un resumen de todas las órdenes de compra con formato de ID robusto."""
    conn = get_connection()
    orders = conn.execute("""
        SELECT po.id, s.nombre as proveedor, po.fecha_pedido, po.estado, po.total, po.numero_oc
        FROM purchase_orders po
        JOIN suppliers s ON po.proveedor_id = s.id
        ORDER BY po.fecha_pedido DESC
    """).fetchall()
    conn.close()
    return orders

def generar_nuevo_numero_oc():
    """Genera un número de orden correlativo con formato OC-AAAA-0001, evitando duplicados por eliminación."""
    anio = datetime.now().year
    conn = get_connection()
    # Buscamos el número más alto existente para este año en lugar de solo contar
    query = "SELECT numero_oc FROM purchase_orders WHERE numero_oc LIKE ? ORDER BY numero_oc DESC LIMIT 1"
    res = conn.execute(query, (f"OC-{anio}-%",)).fetchone()
    conn.close()
    
    if not res:
        return f"OC-{anio}-0001"
    
    # Extraer el correlativo actual (los últimos 4 dígitos) e incrementar
    try:
        ultimo_correlativo = int(res['numero_oc'].split('-')[-1])
        return f"OC-{anio}-{(ultimo_correlativo + 1):04d}"
    except (ValueError, IndexError):
        # Si el formato no coincide, fallar con un conteo de seguridad
        conn = get_connection()
        count = conn.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
        conn.close()
        return f"OC-{anio}-{(count + 100):04d}"

def get_purchase_order_details(order_id):
    """Obtiene los detalles (productos) de una orden de compra específica."""
    conn = get_connection()
    details = conn.execute("""
        SELECT pod.*, p.nombre, p.unidad, p.descripcion
        FROM purchase_order_details pod
        JOIN products p ON pod.producto_codigo = p.codigo
        WHERE pod.pedido_id = ?
    """, (order_id,)).fetchall()
    conn.close()
    return details

def create_purchase_order(proveedor_nombre, ruc_dni, items, po_data=None):
    """Crea una nueva orden de compra con validaciones y cálculos automáticos."""
    # VALIDACIONES BÁSICAS
    ruc_dni = str(ruc_dni).strip()
    if not ruc_dni or not ruc_dni.isdigit() or len(ruc_dni) < 8 or len(ruc_dni) > 11:
        raise ValueError(f"El RUC/DNI '{ruc_dni}' debe tener entre 8 y 11 dígitos numéricos.")
    
    if not items:
        raise ValueError("No se puede crear una orden sin productos.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 0. Preparar Variables
        po_data = po_data or {}
        numero_oc = generar_nuevo_numero_oc()
        comp_prov = po_data.get('comprobante_proveedor')
        fecha_compra = po_data.get('fecha_compra') or get_lima_time()

        # 1. Gestionar el Proveedor (y su RUC)
        cursor.execute("SELECT id FROM suppliers WHERE nombre = ?", (proveedor_nombre,))
        supplier = cursor.fetchone()
        if not supplier:
            cursor.execute("INSERT INTO suppliers (nombre, ruc_dni) VALUES (?, ?)", (proveedor_nombre, ruc_dni))
            proveedor_id = cursor.lastrowid
        else:
            proveedor_id = supplier['id']
            # Actualizamos el RUC si ha cambiado o no existía
            cursor.execute("UPDATE suppliers SET ruc_dni = ? WHERE id = ?", (ruc_dni, proveedor_id))

        # 2. Cálculos Financieros
        subtotal = 0.0
        for item in items:
            # item = (codigo, cantidad, precio_unitario)
            cant = float(item[1])
            prec = float(item[2])
            if cant <= 0 or prec <= 0:
                raise ValueError(f"Cantidad y precio deben ser mayores a cero. Error en item: {item[0]}")
            subtotal += (cant * prec)
        
        total = round(subtotal, 2)
        subtotal_neto = round(total / 1.18, 2)
        igv = round(total - subtotal_neto, 2)

        # 3. Crear la Orden Principal
        # ... (en la inserción/actualización se usarán subtotal_neto, igv, total)
        cursor.execute('''
            INSERT INTO purchase_orders (
                proveedor_id, numero_oc, comprobante_proveedor, estado, fecha_pedido, fecha_estimada, condicion_pago, 
                lugar_entrega, responsable_recibe, subtotal, igv, total
            ) VALUES (?, ?, ?, 'PENDIENTE', ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            proveedor_id, numero_oc, comp_prov, fecha_compra,
            po_data.get('fecha_estimada'), 
            po_data.get('condicion_pago'), 
            po_data.get('lugar_entrega'),
            po_data.get('responsable_recibe'),
            subtotal_neto, igv, total
        ))
        order_id = cursor.lastrowid

        # 4. Insertar Detalles
        for item in items:
            cursor.execute("""
                INSERT INTO purchase_order_details (pedido_id, producto_codigo, cantidad, precio_compra_unitario)
                VALUES (?, ?, ?, ?)
            """, (order_id, item[0], item[1], item[2]))
        
        conn.commit()
        return order_id
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def update_purchase_order(order_id, proveedor_nombre, ruc_dni, items, po_data=None):
    """Actualiza una orden de compra pendiente (reemplaza items y actualiza cabecera)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Verificar si está pendiente
        order = cursor.execute("SELECT estado FROM purchase_orders WHERE id = ?", (order_id,)).fetchone()
        if not order: raise ValueError("La orden no existe.")
        if order['estado'] != 'PENDIENTE': raise ValueError("No se puede editar una orden ya recibida.")

        # 2. Gestionar Proveedor
        cursor.execute("SELECT id FROM suppliers WHERE nombre = ?", (proveedor_nombre,))
        supplier = cursor.fetchone()
        if not supplier:
            cursor.execute("INSERT INTO suppliers (nombre, ruc_dni) VALUES (?, ?)", (proveedor_nombre, ruc_dni))
            proveedor_id = cursor.lastrowid
        else:
            proveedor_id = supplier['id']
            cursor.execute("UPDATE suppliers SET ruc_dni = ? WHERE id = ?", (ruc_dni, proveedor_id))

        # 3. Cálculos
        subtotal = 0.0
        for item in items:
            subtotal += (float(item[1]) * float(item[2]))
        igv = 0.0
        total = round(subtotal, 2)

        # 4. Actualizar Cabecera
        po_data = po_data or {}
        fecha_compra = po_data.get('fecha_compra') or get_lima_time()
        comp_prov = po_data.get('comprobante_proveedor')
        
        cursor.execute('''
            UPDATE purchase_orders SET 
                proveedor_id = ?, fecha_pedido = ?, comprobante_proveedor = ?, subtotal = ?, igv = ?, total = ?
            WHERE id = ?
        ''', (proveedor_id, fecha_compra, comp_prov, subtotal, igv, total, order_id))

        # 5. Reemplazar Detalles
        cursor.execute("DELETE FROM purchase_order_details WHERE pedido_id = ?", (order_id,))
        for item in items:
            cursor.execute("""
                INSERT INTO purchase_order_details (pedido_id, producto_codigo, cantidad, precio_compra_unitario)
                VALUES (?, ?, ?, ?)
            """, (order_id, item[0], item[1], item[2]))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_purchase_order_by_id(order_id):
    """Obtiene toda la información de una orden de compra."""
    conn = get_connection()
    order = conn.execute("""
        SELECT po.*, s.nombre as proveedor_nombre, s.ruc_dni, s.direccion, s.telefono, s.email
        FROM purchase_orders po
        JOIN suppliers s ON po.proveedor_id = s.id
        WHERE po.id = ?
    """, (order_id,)).fetchone()
    conn.close()
    return order

def update_purchase_order_status(order_id, new_status):
    """Actualiza el estado de una orden de compra."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        if new_status == "RECIBIDA":
            receive_purchase_order(order_id)
        elif new_status == "REVERTIR":
            revert_purchase_order(order_id)
        else:
            cursor.execute("UPDATE purchase_orders SET estado = ? WHERE id = ?", (new_status, order_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def revert_purchase_order(order_id):
    """Revierte una orden 'RECIBIDO': descuenta el stock ingresado y la pone en 'PENDIENTE'."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Verificar que esté recibida
        order = cursor.execute("SELECT estado FROM purchase_orders WHERE id = ?", (order_id,)).fetchone()
        if not order or order['estado'] != 'RECIBIDO':
            raise ValueError("Solo se pueden revertir órdenes en estado RECIBIDO.")

        # 2. Obtener productos para descontar stock
        details = cursor.execute("SELECT producto_codigo, cantidad FROM purchase_order_details WHERE pedido_id = ?", (order_id,)).fetchall()
        
        for item in details:
            sku = item['producto_codigo']
            cant = item['cantidad']
            
            # Descontar del stock (Validar que no quede en negativo si es necesario, 
            # aunque en devoluciones de compra se asume que se está corrigiendo un error)
            cursor.execute("""
                UPDATE products 
                SET stock_actual = stock_actual - ?, 
                    stock = stock - ? 
                WHERE codigo = ?
            """, (cant, cant, sku))

        # 3. Regresar a PENDIENTE y limpiar fecha llegada
        cursor.execute("UPDATE purchase_orders SET estado = 'PENDIENTE', fecha_llegada = NULL WHERE id = ?", (order_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def receive_purchase_order(order_id):
    """Marca una orden como 'RECIBIDO', actualiza stock_actual y calcula el costo promedio."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Obtener productos de la orden
        details = cursor.execute("SELECT producto_codigo, cantidad, precio_compra_unitario FROM purchase_order_details WHERE pedido_id = ?", (order_id,)).fetchall()
        
        for item in details:
            sku = item['producto_codigo']
            cant_nueva = item['cantidad']
            precio_nuevo = item['precio_compra_unitario']
            
            # Obtener stock y costo actual
            prod = cursor.execute("SELECT stock_actual, costo_promedio FROM products WHERE codigo = ?", (sku,)).fetchone()
            
            if prod:
                stock_ant = prod['stock_actual'] or 0
                costo_ant = prod['costo_promedio'] or 0.0
                
                # Cálculo de Costo Promedio Ponderado
                stock_total = stock_ant + cant_nueva
                if stock_total > 0:
                    nuevo_costo_prom = ((stock_ant * costo_ant) + (cant_nueva * precio_nuevo)) / stock_total
                else:
                    nuevo_costo_prom = precio_nuevo
                
                # Actualizar producto
                cursor.execute("""
                    UPDATE products 
                    SET stock_actual = stock_actual + ?, 
                        stock = stock + ?,
                        precio_compra = ?, 
                        costo_promedio = ? 
                    WHERE codigo = ?
                """, (cant_nueva, cant_nueva, precio_nuevo, nuevo_costo_prom, sku))

        # 2. Marcar orden como recibida
        cursor.execute("UPDATE purchase_orders SET estado = 'RECIBIDO', fecha_llegada = CURRENT_TIMESTAMP WHERE id = ?", (order_id,))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def generar_correlativo_comprobante(tipo):
    """Genera el correlativo siguiente según el tipo (B=Boleta, F=Factura, T=Ticket)."""
    prefijos = {"BOLETA": "B001", "FACTURA": "F001", "TICKET": "T001"}
    prefijo = prefijos.get(tipo.upper(), "T001")
    
    conn = get_connection()
    count = conn.execute("SELECT COUNT(*) FROM transactions WHERE tipo_comprobante = ?", (tipo.upper(),)).fetchone()[0]
    conn.close()
    
    return f"{prefijo}-{(count + 1):06d}"

def record_sale(session_id, total, cart_items, user_id, payment_data=None):
    """Registra una venta con validación de stock y existencia de productos."""
    now = get_lima_time()
    payment_data = payment_data or {}
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Validar Stock y Existencia de Productos antes de cualquier cambio
        tipo_comp = payment_data.get('tipo_comprobante', 'TICKET').upper()
        no_discount_types = ["PROFORMA", "COTIZACION", "COTIZACIÓN"]

        if tipo_comp not in no_discount_types:
            for item in cart_items:
                # item puede ser (codigo, cantidad, precio, factor)
                codigo = item[0]
                cantidad = item[1]
                factor_venta = item[3] if len(item) > 3 else 1.0
                cantidad_solicitada_und = cantidad * factor_venta
                
                prod = cursor.execute("SELECT nombre, stock_actual, unidad FROM products WHERE codigo = ?", (codigo,)).fetchone()
                
                if not prod:
                    raise ValueError(f"El producto con código '{codigo}' no existe.")
                
                # Obtener factor de la unidad BASE del producto
                u_base = (prod['unidad'] or "").upper()
                f_base = 1.0
                if "MILLAR" in u_base: f_base = 1000.0
                elif "CIENTO" in u_base: f_base = 100.0
                elif "DOCENA" in u_base: f_base = 12.0
                
                stock_disponible_und = prod['stock_actual'] * f_base
                
                if stock_disponible_und < cantidad_solicitada_und:
                    # Formatear mensaje para que sea claro
                    msg_disp = f"{prod['stock_actual']} {prod['unidad']}"
                    if f_base > 1: msg_disp += f" ({int(stock_disponible_und)} UND)"
                    
                    raise ValueError(f"Stock insuficiente para '{prod['nombre']}'. Disponible: {msg_disp}, Requerido: {cantidad_solicitada_und} UND")

        # 2. Generar correlativo
        correlativo = generar_correlativo_comprobante(tipo_comp)

        # 3. Registrar la transacción con datos del cliente
        cursor.execute("""
            INSERT INTO transactions (date, 
                session_id, total, user_id, metodo_pago, tipo_comprobante, 
                correlativo, monto_pagado, vuelto, cliente_nombre, cliente_documento
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            now, session_id, total, user_id, 
            payment_data.get('metodo_pago', 'EFECTIVO'),
            tipo_comp, correlativo,
            payment_data.get('monto_pagado', total),
            payment_data.get('vuelto', 0.0),
            payment_data.get('cliente_nombre', 'PÚBLICO EN GENERAL'),
            payment_data.get('cliente_documento', '00000000')
        ))
        transaction_id = cursor.lastrowid
        
        # 4. Detalles y Actualización de Stock
        for item in cart_items:
            # item = (producto_codigo, quantity, unit_price, factor, unidad_nombre)
            # Nota: Si el factor no viene en la tupla, por defecto es 1.0
            factor = item[3] if len(item) > 3 else 1.0
            u_nombre = item[4] if len(item) > 4 else None
            cantidad_base = item[1] * factor
            
            cursor.execute("""
                INSERT INTO transaction_details (transaction_id, producto_codigo, quantity, unit_price, unidad_venta) 
                VALUES (?, ?, ?, ?, ?)
            """, (transaction_id, item[0], item[1], item[2], u_nombre))
            
            # SOLO DESCONTAR STOCK SI NO ES UN DOCUMENTO INFORMATIVO
            if tipo_comp not in no_discount_types:
                # Obtener factor de la unidad BASE del producto para descontar correctamente
                prod_info = cursor.execute("SELECT unidad FROM products WHERE codigo = ?", (item[0],)).fetchone()
                u_base_p = (prod_info['unidad'] or "").upper()
                f_base_p = 1.0
                if "MILLAR" in u_base_p: f_base_p = 1000.0
                elif "CIENTO" in u_base_p: f_base_p = 100.0
                elif "DOCENA" in u_base_p: f_base_p = 12.0
                
                # Convertir las unidades vendidas al equivalente en la unidad base (ej: 12 und -> 0.012 millares)
                descuento_proporcional = cantidad_base / f_base_p
                
                cursor.execute("UPDATE products SET stock = stock - ?, stock_actual = stock_actual - ? WHERE codigo = ?", (descuento_proporcional, descuento_proporcional, item[0]))

        # 5. Comisiones (Solo si no es informativo)
        if tipo_comp not in no_discount_types:
            seller = cursor.execute("SELECT commission_rate FROM users WHERE id = ?", (user_id,)).fetchone()
            if seller and seller['commission_rate'] > 0:
                cursor.execute("INSERT INTO commissions_earned (user_id, transaction_id, commission_amount) VALUES (?, ?, ?)", (user_id, transaction_id, total * seller['commission_rate']))
            
        conn.commit()
        return transaction_id, correlativo
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def delete_purchase_order(order_id):
    """Elimina físicamente una orden de compra y sus detalles (solo si está PENDIENTE)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Verificar estado
        order = cursor.execute("SELECT estado FROM purchase_orders WHERE id = ?", (order_id,)).fetchone()
        if not order: raise ValueError("La orden no existe.")
        if order['estado'] != 'PENDIENTE':
            raise ValueError("No se puede eliminar una orden que ya ha sido recibida.")

        # 2. Eliminar detalles y cabecera
        cursor.execute("DELETE FROM purchase_order_details WHERE pedido_id = ?", (order_id,))
        cursor.execute("DELETE FROM purchase_orders WHERE id = ?", (order_id,))
        
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_commissions_history(user_id=None, start_date=None, end_date=None):
    """Obtiene el historial de comisiones ganadas, opcionalmente filtrado por usuario y rango de fechas."""
    conn = get_connection()
    query = """
        SELECT
            ce.id AS commission_id,
            ce.date AS commission_date,
            ce.commission_amount,
            u.username AS seller_name,
            t.id AS transaction_id,
            t.total AS transaction_total
        FROM commissions_earned ce
        JOIN users u ON ce.user_id = u.id
        JOIN transactions t ON ce.transaction_id = t.id
        WHERE 1=1
    """
    params = []

    if user_id:
        query += " AND ce.user_id = ?"
        params.append(user_id)
    if start_date:
        query += " AND ce.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND ce.date <= ?"
        params.append(end_date)
    
    query += " ORDER BY ce.date DESC"
    commissions = conn.execute(query, params).fetchall()
    conn.close()
    return commissions

def get_sales_history(user_id=None, start_date=None, end_date=None):
    """Obtiene el historial de ventas, opcionalmente filtrado por usuario y rango de fechas."""
    conn = get_connection()
    query = """
        SELECT
            t.id AS transaction_id,
            t.date AS transaction_date,
            t.total AS transaction_total,
            t.status,
            u.username AS seller_name
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        WHERE 1=1
    """
    params = []

    if user_id:
        query += " AND t.user_id = ?"
        params.append(user_id)
    if start_date:
        query += " AND t.date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND t.date <= ?"
        params.append(end_date)
    
    query += " ORDER BY t.date DESC"
    sales = conn.execute(query, params).fetchall()
    conn.close()
    return sales

def add_cash_movement(session_id, user_id, tipo, monto, descripcion):
    """Registra un ingreso o retiro manual de efectivo."""
    conn = get_connection()
    conn.execute("INSERT INTO cash_movements (session_id, user_id, tipo, monto, descripcion) VALUES (?, ?, ?, ?, ?)",
                   (session_id, user_id, tipo, monto, descripcion))
    conn.commit()
    conn.close()

def get_cash_session_summary(session_id):
    """Obtiene un resumen completo de la sesión actual (Corte X)."""
    conn = get_connection()
    
    # 1. Ventas por método de pago
    sales = conn.execute("""
        SELECT metodo_pago, SUM(total) as total 
        FROM transactions 
        WHERE session_id = ? 
          AND status != 'VOIDED'
        GROUP BY metodo_pago
    """, (session_id,)).fetchall()
    
    # 2. Movimientos manuales
    movements = conn.execute("""
        SELECT tipo, SUM(monto) as total 
        FROM cash_movements 
        WHERE session_id = ? 
        GROUP BY tipo
    """, (session_id,)).fetchall()
    
    # 3. Datos de la sesión (Fondo inicial)
    session = conn.execute("SELECT initial_fund FROM cash_sessions WHERE id = ?", (session_id,)).fetchone()
    
    conn.close()
    
    # Organizar resultados
    res = {
        'ventas': {r['metodo_pago']: r['total'] for r in sales},
        'movimientos': {r['tipo']: r['total'] for r in movements},
        'inicial': session['initial_fund'] if session else 0.0
    }
    
    # Calcular Efectivo Real esperado
    efectivo_ventas = res['ventas'].get('EFECTIVO', 0.0)
    ingresos = res['movimientos'].get('INGRESO', 0.0)
    retiros = res['movimientos'].get('RETIRO', 0.0)
    
    res['efectivo_esperado'] = res['inicial'] + efectivo_ventas + ingresos - retiros
    res['total_general'] = sum(res['ventas'].values()) + ingresos - retiros
    
    return res

def get_cash_sessions_history(user_id=None, start_date=None, end_date=None):
    """Obtiene el historial de sesiones de caja, opcionalmente filtrado por usuario y rango de fechas."""
    conn = get_connection()
    query = """
        SELECT
            cs.id AS session_id,
            cs.open_date,
            cs.close_date,
            cs.initial_fund,
            cs.total_sales,
            cs.status,
            u_open.username AS opened_by_username,
            u_close.username AS closed_by_username
        FROM cash_sessions cs
        LEFT JOIN users u_open ON cs.opened_by_user_id = u_open.id
        LEFT JOIN users u_close ON cs.closed_by_user_id = u_close.id
        WHERE 1=1
    """
    params = []

    if user_id:
        # Buscar sesiones donde el user_id abrió o cerró la caja
        query += " AND (cs.opened_by_user_id = ? OR cs.closed_by_user_id = ?)"
        params.append(user_id)
        params.append(user_id) # Se usa dos veces para la condición OR
    if start_date:
        query += " AND cs.open_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND cs.open_date <= ?"
        params.append(end_date)
    
    query += " ORDER BY cs.open_date DESC"
    sessions = conn.execute(query, params).fetchall()
    conn.close()
    return sessions

# --- Nuevas Funciones de Gestión ---

# --- MÓDULO DE REPORTES AVANZADOS ---

def get_report_daily_sales():
    """Obtiene el resumen de ventas del día actual por método de pago."""
    conn = get_connection()
    # Fecha de hoy en formato YYYY-MM-DD
    hoy = get_lima_time()[:10]
    
    query = """
        SELECT 
            COUNT(id) as total_transacciones,
            SUM(total) as monto_total,
            SUM(CASE WHEN metodo_pago = 'EFECTIVO' THEN total ELSE 0 END) as efectivo,
            SUM(CASE WHEN metodo_pago = 'TRANSFERENCIA' THEN total ELSE 0 END) as transferencia,
            SUM(CASE WHEN metodo_pago NOT IN ('EFECTIVO', 'TRANSFERENCIA') THEN total ELSE 0 END) as otros
        FROM transactions 
        WHERE date(date) = date(?)
          AND status != 'VOIDED'
    """
    res = conn.execute(query, (hoy,)).fetchone()
    conn.close()
    return res

def get_report_sales_by_range(start_date, end_date):
    """Ventas detalladas por rango con cálculo de utilidad/ganancia y desglose por método."""
    conn = get_connection()
    query_resumen = """
        SELECT 
            COALESCE(SUM(t.total), 0) as ingresos_brutos,
            COALESCE(SUM(t.total / 1.18 * 0.18), 0) as total_igv,
            COALESCE(SUM(t.total / 1.18), 0) as total_neto,
            COALESCE(SUM((td.unit_price - p.precio_compra) * td.quantity), 0) as ganancia_estimada
        FROM transactions t
        JOIN transaction_details td ON t.id = td.transaction_id
        JOIN products p ON td.producto_codigo = p.codigo
        WHERE date(t.date) BETWEEN date(?) AND date(?)
          AND t.status != 'VOIDED'
    """
    res = conn.execute(query_resumen, (start_date, end_date)).fetchone()
    res_dict = dict(res) if res else {}

    query_metodos = """
        SELECT metodo_pago, SUM(total) as total
        FROM transactions
        WHERE (date(date) BETWEEN ? AND ?)
          AND status != 'VOIDED'
        GROUP BY metodo_pago
    """
    metodos = conn.execute(query_metodos, (start_date, end_date)).fetchall()
    res_dict['por_metodo'] = {m['metodo_pago']: m['total'] for m in metodos}
    conn.close()
    return res_dict

def get_report_sales_by_category(start_date, end_date, payment_method=None):
    """Obtiene el resumen de ventas agrupado por categorías con desglose de pagos."""
    conn = get_connection()
    query = """
        SELECT 
            COALESCE(p.categoria, 'SIN CATEGORÍA') as categoria,
            SUM(td.quantity) as cant_vendida,
            COALESCE(SUM(CASE WHEN t.metodo_pago = 'EFECTIVO' THEN td.unit_price * td.quantity ELSE 0 END), 0.0) as efectivo,
            COALESCE(SUM(CASE WHEN t.metodo_pago = 'TRANSFERENCIA' OR t.metodo_pago = 'TARJETA' THEN td.unit_price * td.quantity ELSE 0 END), 0.0) as transferencia,
            COALESCE(SUM(CASE WHEN t.metodo_pago = 'YAPE/PLIN' THEN td.unit_price * td.quantity ELSE 0 END), 0.0) as yape_plin,
            SUM(td.unit_price * td.quantity) as total_generado,
            SUM((td.unit_price - p.precio_compra) * td.quantity) as margen_ganancia
        FROM transaction_details td
        JOIN products p ON td.producto_codigo = p.codigo
        JOIN transactions t ON td.transaction_id = t.id
        WHERE (date(t.date) BETWEEN date(?) AND date(?))
          AND t.status != 'VOIDED'
    """
    params = [start_date, end_date]
    if payment_method and payment_method != "TODOS":
        query += " AND t.metodo_pago = ?"
        params.append(payment_method)
    
    query += " GROUP BY categoria ORDER BY total_generado DESC"
    res = conn.execute(query, params).fetchall()
    conn.close()
    return res

def get_report_sales_by_category_details(category, start_date, end_date):
    """Obtiene el detalle de productos vendidos dentro de una categoría específica con costos y margen."""
    conn = get_connection()
    query = """
        SELECT 
            p.codigo,
            p.nombre,
            SUM(td.quantity) as cant_vendida,
            SUM(td.unit_price * td.quantity) as total_generado,
            p.precio_compra as costo_unitario,
            SUM((td.unit_price - p.precio_compra) * td.quantity) as utilidad_item
        FROM transaction_details td
        JOIN products p ON td.producto_codigo = p.codigo
        JOIN transactions t ON td.transaction_id = t.id
        WHERE COALESCE(p.categoria, 'SIN CATEGORÍA') = ?
          AND (date(t.date) BETWEEN date(?) AND date(?))
          AND t.status != 'VOIDED'
        GROUP BY p.codigo
        ORDER BY utilidad_item ASC
    """
    res = conn.execute(query, (category, start_date, end_date)).fetchall()
    conn.close()
    return res

    conn.close()
    return res

def get_report_top_products(limit=10):
    """Obtiene los 10 productos más vendidos por cantidad (Excluye anuladas)."""
    conn = get_connection()
    query = """
        SELECT p.nombre, SUM(td.quantity) as total_qty
        FROM transaction_details td
        JOIN products p ON td.producto_codigo = p.codigo
        JOIN transactions t ON td.transaction_id = t.id
        WHERE t.status != 'VOIDED'
        GROUP BY p.codigo
        ORDER BY total_qty DESC
        LIMIT ?
    """
    res = conn.execute(query, (limit,)).fetchall()
    conn.close()
    return res

def get_report_low_stock():
    """Productos que están por debajo de su stock mínimo."""
    conn = get_connection()
    query = """
        SELECT codigo, nombre, stock, stock_minimo, (stock_minimo - stock) as faltante
        FROM products 
        WHERE stock <= stock_minimo
        ORDER BY stock ASC
    """
    res = conn.execute(query).fetchall()
    conn.close()
    return res

def get_report_kardex():
    """Reporte de movimientos consolidado con ID de referencia (Excluye ventas anuladas)."""
    conn = get_connection()
    query = """
        SELECT t.id as ref_id, t.date, 'SALIDA (VENTA)' as tipo, td.producto_codigo, td.quantity as cant, td.unit_price as precio
        FROM transaction_details td
        JOIN transactions t ON td.transaction_id = t.id
        WHERE t.status != 'VOIDED'
        
        UNION ALL
        
        SELECT po.id as ref_id, po.fecha_pedido as date, 'ENTRADA (COMPRA)' as tipo, pod.producto_codigo, pod.cantidad as cant, pod.precio_compra_unitario as precio
        FROM purchase_order_details pod
        JOIN purchase_orders po ON pod.pedido_id = po.id
        
        ORDER BY date DESC
    """
    res = conn.execute(query).fetchall()
    conn.close()
    return res

def buscar_cliente_local(documento):
    """Busca un cliente en la tabla dedicada de clientes devolviendo todos sus campos."""
    conn = get_connection()
    try:
        # Ahora incluimos id y documento en la consulta
        res = conn.execute("SELECT id, documento, nombre, direccion, telefono, email FROM customers WHERE documento = ?", (documento,)).fetchone()
        conn.close()
        return dict(res) if res else None
    except Exception as e:
        print(f"Error al buscar cliente: {e}")
        conn.close()
        return None

def get_all_customers(search_term=""):
    """Devuelve la lista de clientes activos, opcionalmente filtrada."""
    conn = get_connection()
    try:
        # Solo clientes donde deleted_at sea NULL
        if search_term:
            query = "SELECT * FROM customers WHERE deleted_at IS NULL AND (nombre LIKE ? OR documento LIKE ?) ORDER BY nombre ASC"
            res = conn.execute(query, (f"%{search_term}%", f"%{search_term}%")).fetchall()
        else:
            res = conn.execute("SELECT * FROM customers WHERE deleted_at IS NULL ORDER BY nombre ASC").fetchall()
        conn.close()
        return res
    except Exception:
        conn.close()
        return []

def get_customer(documento):
    """Obtiene un cliente específico por su documento."""
    conn = get_connection()
    try:
        res = conn.execute("SELECT * FROM customers WHERE documento = ? AND deleted_at IS NULL", (documento,)).fetchone()
        conn.close()
        return res
    except Exception:
        conn.close()
        return None

def get_deleted_customers():
    """Obtiene clientes eliminados en los últimos 3 días."""
    conn = get_connection()
    try:
        # Clientes eliminados hace menos de 3 días
        query = "SELECT * FROM customers WHERE deleted_at IS NOT NULL AND deleted_at > datetime('now', '-3 days') ORDER BY deleted_at DESC"
        res = conn.execute(query).fetchall()
        conn.close()
        return res
    except Exception:
        conn.close()
        return []

def delete_customer(documento):
    """Realiza una eliminación temporal (Soft Delete) del cliente."""
    conn = get_connection()
    try:
        now = get_lima_time()
        conn.execute("UPDATE customers SET deleted_at = ? WHERE documento = ?", (now, documento))
        conn.commit()
        
        # Limpieza automática de clientes eliminados hace más de 3 días
        conn.execute("DELETE FROM customers WHERE deleted_at IS NOT NULL AND deleted_at < datetime('now', '-3 days')")
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def restore_customer(documento):
    """Restaura un cliente de la papelera."""
    conn = get_connection()
    try:
        conn.execute("UPDATE customers SET deleted_at = NULL WHERE documento = ?", (documento,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def add_or_update_customer(data):
    """Guarda o actualiza la información completa de un cliente usando ID o Documento."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Si viene un ID, intentamos actualizar ese registro específico
        client_id = data.get('id')
        if client_id:
            cursor.execute('''
                UPDATE customers 
                SET documento = ?, nombre = ?, direccion = ?, telefono = ?, email = ?
                WHERE id = ?
            ''', (
                str(data['documento']), 
                str(data['nombre']).upper(), 
                str(data.get('direccion') or '').upper(), 
                str(data.get('telefono') or ''), 
                str(data.get('email') or '').lower(),
                client_id
            ))
            # Si no se actualizó nada (ID no existe), procedemos al INSERT
            if cursor.rowcount > 0:
                conn.commit()
                return True

        # 2. Si no hay ID o la actualización falló, usamos el comportamiento anterior (INSERT or UPDATE por documento)
        cursor.execute('''
            INSERT INTO customers (documento, nombre, direccion, telefono, email)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(documento) DO UPDATE SET
                nombre=excluded.nombre,
                direccion=excluded.direccion,
                telefono=excluded.telefono,
                email=excluded.email
        ''', (
            str(data['documento']), 
            str(data['nombre']).upper(), 
            str(data.get('direccion') or '').upper(), 
            str(data.get('telefono') or ''), 
            str(data.get('email') or '').lower()
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError as ie:
        print(f"Error de integridad al guardar cliente: {ie}")
        raise ValueError("El DNI/RUC ya pertenece a otro cliente.")
    except Exception as e:
        print(f"Error general al guardar cliente: {e}")
        return False
    finally:
        conn.close()

def get_sale_full_details(transaction_id):
    """Obtiene toda la información de una venta, sus items y pago para reconstruir el recibo."""
    conn = get_connection()
    # 1. Datos de cabecera
    sale = conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
    if not sale:
        conn.close()
        return None, None
    
    # 2. Detalles de productos
    items = conn.execute("""
        SELECT p.codigo, p.nombre, td.quantity, td.unit_price, p.fabricante, 
               COALESCE(td.unidad_venta, p.unidad) as unidad_venta, p.stock
        FROM transaction_details td
        JOIN products p ON td.producto_codigo = p.codigo
        WHERE td.transaction_id = ?
    """, (transaction_id,)).fetchall()
    
    conn.close()
    return sale, items

def update_sale(transaction_id, total, cart_items, payment_data):
    """Actualiza una venta existente, revierte stock anterior y aplica el nuevo."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. REVERTIR STOCK ANTERIOR
        old_items = cursor.execute("SELECT producto_codigo, quantity FROM transaction_details WHERE transaction_id = ?", (transaction_id,)).fetchall()
        for item in old_items:
            cursor.execute("UPDATE products SET stock = stock + ?, stock_actual = stock_actual + ? WHERE codigo = ?", (item['quantity'], item['quantity'], item['producto_codigo']))
        
        # 2. LIMPIAR DETALLES ANTERIORES
        cursor.execute("DELETE FROM transaction_details WHERE transaction_id = ?", (transaction_id,))

        # 3. ACTUALIZAR CABECERA DE LA TRANSACCIÓN
        cursor.execute("""
            UPDATE transactions 
            SET total = ?, metodo_pago = ?, tipo_comprobante = ?, 
                monto_pagado = ?, vuelto = ?, cliente_nombre = ?, cliente_documento = ?
            WHERE id = ?
        """, (
            total, payment_data['metodo_pago'], payment_data['tipo_comprobante'],
            payment_data['monto_pagado'], payment_data['vuelto'],
            payment_data['cliente_nombre'], payment_data['cliente_documento'],
            transaction_id
        ))

        # 4. INSERTAR NUEVOS DETALLES Y DESCONTAR NUEVO STOCK
        for item in cart_items:
            # item = (producto_codigo, quantity, unit_price)
            cursor.execute("INSERT INTO transaction_details (transaction_id, producto_codigo, quantity, unit_price) VALUES (?, ?, ?, ?)", (transaction_id, item[0], item[1], item[2]))
            cursor.execute("UPDATE products SET stock = stock - ?, stock_actual = stock_actual - ? WHERE codigo = ?", (item[1], item[1], item[0]))

        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_report_sales_by_seller():
    """Ventas totales acumuladas por cada usuario/vendedor."""
    conn = get_connection()
    query = """
        SELECT u.username, COUNT(t.id) as num_ventas, SUM(t.total) as total_vendido
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        GROUP BY u.id
        ORDER BY total_vendido DESC
    """
    res = conn.execute(query).fetchall()
    conn.close()
    return res

def get_product(codigo):
    """Obtiene un producto específico por su código, incluyendo el nombre del proveedor."""
    conn = get_connection()
    # Unir con la tabla de proveedores para obtener el nombre en lugar de solo el ID
    product = conn.execute("""
        SELECT p.codigo as id, p.codigo as sku, p.*, s.nombre as proveedor_nombre 
        FROM products p 
        LEFT JOIN suppliers s ON p.proveedor_id = s.id 
        WHERE p.codigo = ?
    """, (codigo,)).fetchone()
    conn.close()
    return product

def get_product_by_name(nombre):
    """Obtiene un producto específico por su nombre exacto."""
    conn = get_connection()
    product = conn.execute("""
        SELECT p.codigo as id, p.codigo as sku, p.*, s.nombre as proveedor_nombre 
        FROM products p 
        LEFT JOIN suppliers s ON p.proveedor_id = s.id 
        WHERE p.nombre = ?
    """, (nombre,)).fetchone()
    conn.close()
    return product

def delete_product(codigo):
    """Realiza un borrado lógico (soft delete) del producto."""
    conn = get_connection()
    try:
        now = get_lima_time()
        conn.execute("UPDATE products SET deleted_at = ? WHERE codigo = ?", (now, codigo))
        conn.commit()
        
        # Limpieza automática de productos eliminados hace más de 3 días
        conn.execute("DELETE FROM products WHERE deleted_at IS NOT NULL AND deleted_at < datetime('now', '-3 days')")
        conn.commit()
        return True
    except Exception as e:
        raise e
    finally:
        conn.close()

def restore_product(codigo):
    """Restaura un producto de la papelera."""
    conn = get_connection()
    try:
        conn.execute("UPDATE products SET deleted_at = NULL WHERE codigo = ?", (codigo,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def get_deleted_products():
    """Obtiene productos eliminados en los últimos 3 días."""
    conn = get_connection()
    try:
        query = "SELECT * FROM products WHERE deleted_at IS NOT NULL AND deleted_at > datetime('now', '-3 days') ORDER BY deleted_at DESC"
        res = conn.execute(query).fetchall()
        conn.close()
        return res
    except Exception:
        conn.close()
        return []

def get_next_product_code():
    """Genera el siguiente código SKU disponible con el formato R_XXXX."""
    conn = get_connection()
    # Buscamos códigos que empiecen con R_ y tengan números
    cursor = conn.execute("SELECT codigo FROM products WHERE codigo LIKE 'R_%'")
    codes = cursor.fetchall()
    conn.close()
    
    max_num = 0
    for row in codes:
        codigo = row['codigo']
        # Extraer la parte numérica si es posible
        parts = codigo.split('_')
        if len(parts) >= 2:
            num_part = parts[1]
            # Si tiene letras al final (ej: R_mad01), intentamos extraer el prefijo numérico o solo números
            # Pero basándonos en R_0950, el formato es R_XXXX
            import re
            match = re.search(r'(\d+)', num_part)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
    
    # Retornamos el siguiente con formato R_XXXX (rellenando con ceros a la izquierda)
    # Si max_num es 0 (no hay códigos R_ o todos son inválidos), empezamos en 0001
    return f"R_{str(max_num + 1).zfill(4)}"

def get_unit_factor(unidad_nombre):
    """Retorna el factor numérico de una unidad por su nombre."""
    if not unidad_nombre: return 1.0
    u = unidad_nombre.lower().strip()
    # Priorizar términos más largos para evitar falsos positivos (ej: 'medio millar' vs 'millar')
    if 'medio millar' in u: return 500.0
    if 'millar' in u: return 1000.0
    if 'medio ciento' in u: return 50.0
    if 'ciento' in u: return 100.0
    if 'docena' in u: return 12.0
    return 1.0

def add_or_update_product(product_data):
    """Añade o actualiza un producto, guardando el stock en unidades físicas directas."""
    conn = get_connection()
    cursor = conn.cursor()

    codigo = _clean_value(product_data.get('codigo'))
    unidad = _clean_value(product_data.get('unidad'))
    
    # El stock se guarda tal cual lo ingresa el usuario (en piezas sueltas)
    stock_real = _clean_value(product_data.get('stock_actual') or product_data.get('stock'), 'float')
    
    nuevo_precio_venta = _clean_value(product_data.get('precio_venta'), 'float')
    
    # 1. Verificar si existe
    cursor.execute("SELECT precio_venta, fecha_actualizacion_precio FROM products WHERE codigo = ?", (codigo,))
    row = cursor.fetchone()
    
    exists = row is not None
    fecha_precio = None
    if exists:
        precio_actual = row['precio_venta']
        fecha_precio = row['fecha_actualizacion_precio']
        if precio_actual != nuevo_precio_venta or not fecha_precio:
            fecha_precio = get_lima_time()
    else:
        fecha_precio = get_lima_time()

    # 2. Gestionar Proveedor
    proveedor_id = product_data.get('proveedor_id')
    if not proveedor_id:
        proveedor_nombre = _clean_value(product_data.get('proveedor_nombre'))
        if proveedor_nombre:
            cursor.execute("SELECT id FROM suppliers WHERE nombre = ?", (proveedor_nombre,))
            supplier_row = cursor.fetchone()
            if supplier_row:
                proveedor_id = supplier_row['id']
            else:
                cursor.execute("INSERT INTO suppliers (nombre) VALUES (?)", (proveedor_nombre,))
                proveedor_id = cursor.lastrowid
    
    if exists:
        # ACTUALIZACIÓN (Usamos UPDATE para proteger las llaves foráneas ON DELETE CASCADE)
        cursor.execute('''
            UPDATE products SET 
                nombre=?, fabricante=?, marca=?, categoria=?, descripcion=?, precio_venta=?, 
                precio_compra=?, unidad=?, stock=?, stock_actual=?, stock_minimo=?, 
                proveedor_id=?, fecha_actualizacion_precio=?
            WHERE codigo=?
        ''', (
            _clean_value(product_data.get('nombre')), 
            _clean_value(product_data.get('fabricante')),
            _clean_value(product_data.get('marca')),
            _clean_value(product_data.get('categoria')), 
            _clean_value(product_data.get('descripcion')),
            nuevo_precio_venta, 
            _clean_value(product_data.get('precio_compra'), 'float'),
            unidad, 
            stock_real,
            stock_real,
            _clean_value(product_data.get('stock_minimo'), 'int') or 5, 
            proveedor_id, 
            fecha_precio,
            codigo
        ))
    else:
        # INSERCIÓN
        fecha_ingreso = product_data.get('fecha_ingreso') or get_lima_time()
        cursor.execute('''
            INSERT INTO products (
                codigo, nombre, fabricante, marca, categoria, descripcion, precio_venta, 
                precio_compra, unidad, stock, stock_actual, stock_minimo, proveedor_id, 
                fecha_ingreso, fecha_actualizacion_precio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            codigo, 
            _clean_value(product_data.get('nombre')), 
            _clean_value(product_data.get('fabricante')),
            _clean_value(product_data.get('marca')),
            _clean_value(product_data.get('categoria')), 
            _clean_value(product_data.get('descripcion')),
            nuevo_precio_venta, 
            _clean_value(product_data.get('precio_compra'), 'float'),
            unidad, 
            stock_real,
            stock_real,
            _clean_value(product_data.get('stock_minimo'), 'int') or 5, 
            proveedor_id, 
            fecha_ingreso,
            fecha_precio
        ))
    
    conn.commit()
    conn.close()

def get_similar_products(nombre, limit=5):
    """Busca productos con nombres similares para evitar duplicados."""
    if not nombre or len(nombre) < 3:
        return []
    conn = get_connection()
    # Usamos LIKE con comodines para buscar coincidencias parciales
    query = """
        SELECT codigo, nombre, precio_venta, stock_actual 
        FROM products 
        WHERE nombre LIKE ? 
        ORDER BY nombre ASC 
        LIMIT ?
    """
    res = conn.execute(query, (f"%{nombre}%", limit)).fetchall()
    conn.close()
    return res

def get_all_products_for_display(search_term: str = "", sort_by: str = "nombre_asc"):
    """
    Obtiene productos para la tabla principal con búsqueda inteligente por palabras.
    """
    conn = get_connection()
    
    sort_map = {
        "nombre_asc": "p.nombre ASC",
        "nombre_desc": "p.nombre DESC",
        "stock_asc": "p.stock ASC",
        "stock_desc": "p.stock DESC",
        "codigo_asc": "p.codigo ASC",
        "codigo_desc": "p.codigo DESC",
    }
    order_clause = sort_map.get(sort_by, "p.nombre ASC")

    base_query = f"""
        SELECT 
            p.codigo, p.codigo as id, p.codigo as sku, p.nombre, p.categoria, p.fabricante, p.marca, p.descripcion,
            p.precio_venta, p.precio_compra, p.costo_promedio, p.unidad, 
            p.stock, p.stock_actual, p.stock_minimo, p.stock_maximo, p.fecha_ingreso, 
            s.nombre as proveedor_nombre,
            (p.stock_actual * p.precio_venta / 
                CASE 
                    WHEN UPPER(p.unidad) LIKE '%MILLAR%' THEN 1000.0
                    WHEN UPPER(p.unidad) LIKE '%CIENTO%' THEN 100.0
                    WHEN UPPER(p.unidad) LIKE '%DOCENA%' THEN 12.0
                    ELSE 1.0 
                END
            ) as valor_inventario
        FROM products p
        LEFT JOIN suppliers s ON p.proveedor_id = s.id
        WHERE p.deleted_at IS NULL
    """
    
    params = []
    if search_term:
        # Dividimos el término en palabras para una búsqueda más flexible
        words = search_term.split()
        for word in words:
            # Cada palabra debe estar presente en nombre, código o descripción
            base_query += " AND (p.nombre LIKE ? OR p.codigo LIKE ? OR p.descripcion LIKE ?)"
            params.extend([f"%{word}%", f"%{word}%", f"%{word}%"])
    
    base_query += f" ORDER BY {order_clause}"
    
    products = conn.execute(base_query, params).fetchall()
    conn.close()
    return products

def add_product_from_import(product_data):
    """Añade o actualiza un producto desde la importación de Excel."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Asegurar que el proveedor exista y obtener su ID
    proveedor_id = None
    if product_data.get('proveedor'):
        proveedor_id = add_supplier(product_data['proveedor'])

    # Intentar obtener la marca de diferentes posibles nombres de columna
    marca = product_data.get('Marca') or product_data.get('MARCA') or product_data.get('marca')

    # Construir la tupla de datos en el orden correcto
    data_tuple = (
        product_data.get('Codigo'),
        product_data.get('NOMBRE'),
        product_data.get('FABRICANTE'),
        marca,
        product_data.get('categoria'),
        product_data.get('DESCRIPCIÓN'),
        float(product_data.get('P.Venta articulo', 0.0)),
        float(product_data.get('Precio Compra', 0.0)),
        product_data.get('unidad'),
        int(product_data.get('STOCK EN ALMACEN', 0)),
        int(product_data.get('STOCK EN ALMACEN', 0)), # stock_actual
        int(product_data.get('stock_minimo', 5)), # Valor por defecto
        proveedor_id,
        product_data.get('FECHA INGRESO')
    )

    # Usar INSERT OR REPLACE para añadir o actualizar si el código ya existe
    cursor.execute('''
        INSERT OR REPLACE INTO products (
            codigo, nombre, fabricante, marca, categoria, descripcion, 
            precio_venta, precio_compra, unidad, stock, stock_actual, stock_minimo, proveedor_id, fecha_ingreso
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', data_tuple)
    
    conn.commit()
    conn.close()

def _clean_value(value, value_type='str'):
    """Limpia y convierte un valor, manejando errores."""
    if value is None:
        return 0.0 if value_type == 'float' else (0 if value_type == 'int' else "")
    
    if value_type in ['float', 'int']:
        if isinstance(value, (int, float)):
            return value
        
        # Eliminar símbolos de moneda, espacios, comas de miles
        cleaned_str = "".join(filter(lambda char: char in '0123456789.', str(value)))
        try:
            if value_type == 'float':
                return float(cleaned_str)
            else: # int
                return int(float(cleaned_str)) # Convertir a float primero por si hay decimales
        except (ValueError, TypeError):
            return 0.0 if value_type == 'float' else 0
    
    return str(value)

def add_product_from_flexible_import(product_data):
    """
    Prepara un diccionario de datos de producto para ser insertado en la base de datos.
    No realiza la conexión, solo prepara los datos.
    """
    fecha_ingreso = product_data.get('fecha_ingreso')
    if fecha_ingreso:
        if isinstance(fecha_ingreso, (datetime, sqlite3.Date)):
            fecha_ingreso = fecha_ingreso.strftime("%Y-%m-%d %H:%M:%S")
        else:
            try:
                fecha_ingreso = datetime.strptime(str(fecha_ingreso).split(" ")[0], "%Y-%m-%d").strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                fecha_ingreso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    else:
        fecha_ingreso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return {
        "codigo": _clean_value(product_data.get('codigo')),
        "nombre": _clean_value(product_data.get('nombre')),
        "fabricante": _clean_value(product_data.get('fabricante')),
        "marca": _clean_value(product_data.get('marca') or product_data.get('MARCA')),
        "categoria": _clean_value(product_data.get('categoria')),
        "descripcion": _clean_value(product_data.get('descripcion')),
        "precio_venta": _clean_value(product_data.get('precio_venta'), 'float'),
        "precio_compra": _clean_value(product_data.get('precio_compra'), 'float'),
        "unidad": _clean_value(product_data.get('unidad')),
        "stock": _clean_value(product_data.get('stock'), 'int'),
        "stock_minimo": _clean_value(product_data.get('stock_minimo'), 'int') or 5,
        "proveedor_nombre": _clean_value(product_data.get('proveedor_nombre')),
        "fecha_ingreso": fecha_ingreso
    }

def bulk_add_products(products):
    """
    Añade o actualiza una lista de productos en una única transacción para mayor eficiencia.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Cache para proveedores para no consultar la BD en cada fila
    supplier_cache = {}

    try:
        for p_data in products:
            proveedor_id = None
            proveedor_nombre = p_data.get('proveedor_nombre')
            
            if proveedor_nombre:
                if proveedor_nombre in supplier_cache:
                    proveedor_id = supplier_cache[proveedor_nombre]
                else:
                    cursor.execute("SELECT id FROM suppliers WHERE nombre = ?", (proveedor_nombre,))
                    supplier_row = cursor.fetchone()
                    if supplier_row:
                        proveedor_id = supplier_row['id']
                    else:
                        cursor.execute("INSERT INTO suppliers (nombre) VALUES (?)", (proveedor_nombre,))
                        proveedor_id = cursor.lastrowid
                    supplier_cache[proveedor_nombre] = proveedor_id

            params = (
                p_data['codigo'], p_data['nombre'], p_data['fabricante'], p_data.get('marca'), p_data['categoria'], 
                p_data['descripcion'], p_data['precio_venta'], p_data['precio_compra'], 
                p_data['unidad'], p_data['stock'], p_data['stock'], # stock_actual
                p_data['stock_minimo'], 
                proveedor_id, p_data['fecha_ingreso']
            )

            cursor.execute('''
                INSERT OR REPLACE INTO products (
                    codigo, nombre, fabricante, marca, categoria, descripcion, 
                    precio_venta, precio_compra, unidad, stock, stock_actual, stock_minimo, proveedor_id, fecha_ingreso
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', params)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e # Re-lanza la excepción para que la UI la capture
    finally:
        conn.close()

def get_profitability_report(start_date=None, end_date=None):
    """Calcula la utilidad real basada en (Precio Venta - Costo Promedio)."""
    conn = get_connection()
    query = """
        SELECT 
            p.codigo, 
            p.nombre, 
            SUM(td.quantity) as total_vendido,
            AVG(td.unit_price) as precio_venta_promedio,
            p.costo_promedio,
            SUM(td.quantity * (td.unit_price - p.costo_promedio)) as utilidad_total
        FROM transaction_details td
        JOIN transactions t ON td.transaction_id = t.id
        JOIN products p ON td.producto_codigo = p.codigo
        WHERE t.status != 'VOIDED'
    """
    params = []
    if start_date and end_date:
        query += " AND t.date BETWEEN ? AND ?"
        params.extend([start_date, end_date])
    
    query += " GROUP BY p.codigo ORDER BY utilidad_total DESC"
    
    report = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in report]

def get_product_kardex(producto_codigo):
    """Obtiene el historial completo de entradas y salidas de un producto."""
    conn = get_connection()
    # Entradas (Compras)
    query_entries = """
        SELECT 
            po.fecha_pedido as fecha,
            'ENTRADA (COMPRA)' as tipo,
            po.numero_oc as documento,
            pod.cantidad,
            pod.precio_compra_unitario as precio,
            'Proveedor: ' || s.nombre as detalle
        FROM purchase_order_details pod
        JOIN purchase_orders po ON pod.pedido_id = po.id
        JOIN suppliers s ON po.proveedor_id = s.id
        WHERE pod.producto_codigo = ? AND po.estado = 'RECIBIDO'
    """
    
    # Salidas (Ventas)
    query_exits = """
        SELECT 
            t.date as fecha,
            'SALIDA (VENTA)' as tipo,
            t.tipo_comprobante || ' ' || t.correlativo as documento,
            td.quantity as cantidad,
            td.unit_price as precio,
            'Cliente: ' || t.cliente_nombre as detalle
        FROM transaction_details td
        JOIN transactions t ON td.transaction_id = t.id
        WHERE td.producto_codigo = ? AND t.status != 'VOIDED'
    """
    
    entries = conn.execute(query_entries, (producto_codigo,)).fetchall()
    exits = conn.execute(query_exits, (producto_codigo,)).fetchall()
    
    conn.close()
    
    movements = [dict(e) for e in entries] + [dict(x) for x in exits]
    # Ordenar por fecha descendente
    movements.sort(key=lambda x: x['fecha'], reverse=True)
    return movements

if __name__ == "__main__":
    init_db()

def get_report_sales_grouped(start_date, end_date, agrupar_por='producto', ordenar_por='cantidad'):
    """Lista de ventas agrupadas por producto o categoría con rentabilidad (Protegida contra Inyección SQL)."""
    conn = get_connection()
    
    # VALIDACIÓN: Lista blanca para evitar inyección SQL por parámetros dinámicos
    allowed_groups = {
        'producto': 'p.nombre',
        'categoria': "COALESCE(p.categoria, 'SIN CATEGORIA')"
    }
    allowed_orders = {
        'cantidad': 'cant_vendida',
        'total': 'total_generado'
    }
    
    group_col = allowed_groups.get(agrupar_por, 'p.nombre')
    order_col = allowed_orders.get(ordenar_por, 'cant_vendida')
    
    query = f"""
        SELECT 
            {group_col} as nombre,
            SUM(td.quantity) as cant_vendida,
            SUM(td.unit_price * td.quantity) as total_generado,
            SUM(p.precio_compra * td.quantity) as costo_total
        FROM transaction_details td
        JOIN products p ON td.producto_codigo = p.codigo
        JOIN transactions t ON td.transaction_id = t.id
        WHERE (date(t.date) BETWEEN date(?) AND date(?))
          AND t.status != 'VOIDED'
        GROUP BY {group_col}
        ORDER BY {order_col} DESC
    """
    res = conn.execute(query, (start_date, end_date)).fetchall()
    conn.close()
    return res

def run_backup_professional(backup_dir="backups_sistema", keep_days=7):
    """Realiza un respaldo seguro de la base de datos usando la API de SQLite y lo comprime."""
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(f"Carpeta '{backup_dir}' creada.")

    today_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    temp_db_path = os.path.join(backup_dir, f"temp_erp_{today_str}.db")
    zip_path = os.path.join(backup_dir, f"erp_system_{today_str}.zip")

    try:
        # 1. Backup seguro usando la API de SQLite (funciona aunque la DB esté abierta)
        src = get_connection()
        dst = sqlite3.connect(temp_db_path)
        with dst:
            src.backup(dst)
        dst.close()
        src.close()

        # 2. Comprimir en ZIP para ahorrar espacio
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(temp_db_path, arcname="erp_system.db")
        
        # 3. Eliminar el temporal .db
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        
        print(f"Respaldo comprimido creado: {zip_path}")
        
        # 4. Limpieza de antiguos
        cleanup_old_backups(backup_dir, keep_days)
        
        return zip_path
    except Exception as e:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
        print(f"Error en respaldo profesional: {e}")
        return None

def void_sale(transaction_id, authorizing_user_id, reason):
    """Anula una venta, devuelve el stock al inventario y anula comisiones."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Verificar si la venta ya está anulada
        sale = cursor.execute("SELECT status, correlativo FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        if not sale:
            raise ValueError("La venta no existe.")
        if sale['status'] == 'VOIDED':
            raise ValueError("La venta ya se encuentra anulada.")

        # 2. Devolver Stock al inventario
        items = cursor.execute("SELECT producto_codigo, quantity, unidad_venta FROM transaction_details WHERE transaction_id = ?", (transaction_id,)).fetchall()
        for item in items:
            u_venta = item['unidad_venta']
            # Si no hay unidad_venta guardada (caso raro de registros antiguos), usar la unidad base del producto
            if not u_venta:
                p_info = cursor.execute("SELECT unidad FROM products WHERE codigo = ?", (item['producto_codigo'],)).fetchone()
                u_venta = p_info['unidad'] if p_info else "UND"
                
            # Obtener factor de la unidad con la que se VENDIÓ
            f_venta = get_unit_factor(u_venta)
            
            # Obtener factor de la unidad BASE del producto para devolver proporcionalmente
            prod_info = cursor.execute("SELECT unidad FROM products WHERE codigo = ?", (item['producto_codigo'],)).fetchone()
            f_base_p = get_unit_factor(prod_info['unidad'] if prod_info else "UND")
            
            # Cantidad total en unidades individuales = cantidad vendida * factor de venta
            # Cantidad a devolver al stock base = total unidades / factor base del producto
            devolucion_proporcional = (item['quantity'] * f_venta) / f_base_p
            
            cursor.execute("""
                UPDATE products 
                SET stock = stock + ?, 
                    stock_actual = stock_actual + ? 
                WHERE codigo = ?
            """, (devolucion_proporcional, devolucion_proporcional, item['producto_codigo']))

        # 3. Anular comisiones generadas por esta venta
        cursor.execute("DELETE FROM commissions_earned WHERE transaction_id = ?", (transaction_id,))

        # 4. Actualizar estado de la transacción y registrar auditoría
        cursor.execute("""
            UPDATE transactions 
            SET status = 'VOIDED', 
                voided_by_user_id = ?, 
                void_reason = ? 
            WHERE id = ?
        """, (authorizing_user_id, reason, transaction_id))

        conn.commit()
        return True, f"Venta {sale['correlativo']} anulada exitosamente."
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def cleanup_old_backups(backup_dir, keep_days):
    """Elimina respaldos más antiguos que keep_days."""
    cutoff = datetime.now() - timedelta(days=keep_days)
    files = os.listdir(backup_dir)
    for f in files:
        f_path = os.path.join(backup_dir, f)
        # Procesar .zip y .db que empiecen con erp_system o temp_erp
        if os.path.isfile(f_path) and (f.endswith(".zip") or f.endswith(".db")):
            file_time = datetime.fromtimestamp(os.path.getctime(f_path))
            if file_time < cutoff:
                try:
                    os.remove(f_path)
                    print(f"Respaldo antiguo eliminado: {f}")
                except Exception as e:
                    print(f"No se pudo eliminar {f}: {e}")

def get_product_units(codigo):
    """Obtiene todas las presentaciones/unidades de un producto."""
    conn = get_connection()
    res = conn.execute("SELECT * FROM product_units WHERE producto_codigo = ? ORDER BY factor_conversion ASC", (codigo,)).fetchall()
    conn.close()
    return res

def add_product_unit(codigo, nombre, factor, precio):
    """Añade una nueva presentación a un producto."""
    conn = get_connection()
    try:
        conn.execute("INSERT INTO product_units (producto_codigo, nombre_unidad, factor_conversion, precio_venta) VALUES (?, ?, ?, ?)",
                   (codigo, nombre, factor, precio))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()

def delete_product_unit(unit_id):
    """Elimina una presentación específica."""
    conn = get_connection()
    conn.execute("DELETE FROM product_units WHERE id = ?", (unit_id,))
    conn.commit()
    conn.close()

def get_today_clients_details():
    """Lista de clientes únicos atendidos el día de hoy."""
    conn = get_connection()
    hoy = get_lima_time()[:10]
    query = """
        SELECT 
            cliente_nombre, 
            cliente_documento, 
            SUM(total) as total_dia,
            COUNT(id) as transacciones,
            MAX(date) as hora_ultima
        FROM transactions 
        WHERE date(date) = date(?) AND status != 'VOIDED'
        GROUP BY cliente_documento
        ORDER BY total_dia DESC
    """
    res = conn.execute(query, (hoy,)).fetchall()
    conn.close()
    return res

def get_today_products_details():
    """Desglose de productos vendidos el día de hoy."""
    conn = get_connection()
    hoy = get_lima_time()[:10]
    query = """
        SELECT 
            p.nombre,
            p.codigo,
            SUM(td.quantity) as cantidad_total,
            SUM(td.quantity * td.unit_price) as monto_total
        FROM transaction_details td
        JOIN transactions t ON td.transaction_id = t.id
        JOIN products p ON td.producto_codigo = p.codigo
        WHERE date(t.date) = date(?) AND t.status != 'VOIDED'
        GROUP BY p.codigo
        ORDER BY cantidad_total DESC
    """
    res = conn.execute(query, (hoy,)).fetchall()
    conn.close()
    return res

def get_dashboard_stats():
    """Calcula estadísticas generales para el dashboard incluyendo clientes ATENDIDOS hoy."""
    conn = get_connection()
    try:
        hoy = get_lima_time()[:10]

        # 1. Ventas de hoy
        res_sales = conn.execute("SELECT SUM(total) FROM transactions WHERE date(date) = date(?) AND status != 'VOIDED'", (hoy,)).fetchone()
        sales_today = res_sales[0] if res_sales and res_sales[0] is not None else 0.0

        # 2. Desglose por método
        res_methods = conn.execute("""
            SELECT metodo_pago, SUM(total) as total 
            FROM transactions 
            WHERE date(date) = date(?) AND status != 'VOIDED'
            GROUP BY metodo_pago
        """, (hoy,)).fetchall()
        methods_today = {row['metodo_pago']: row['total'] for row in res_methods}

        # 3. Clientes ATENDIDOS hoy (Únicos)
        res_clients_today = conn.execute("SELECT COUNT(DISTINCT cliente_documento) FROM transactions WHERE date(date) = date(?) AND status != 'VOIDED'", (hoy,)).fetchone()
        clients_today = res_clients_today[0] if res_clients_today else 0

        # 4. Total productos alerta
        res_low = conn.execute("SELECT COUNT(*) FROM products WHERE stock <= stock_minimo AND deleted_at IS NULL").fetchone()
        
        return {
            "sales_today": sales_today,
            "methods_today": methods_today,
            "total_clients_today": clients_today,
            "alerta_stock": res_low[0] if res_low else 0
        }
    finally:
        conn.close()


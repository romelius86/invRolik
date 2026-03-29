import sys
import os
import html

# Como ahora todo está en el mismo nivel, añadimos el directorio actual al path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import database

from pydantic import BaseModel

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield

app = FastAPI(title="ERP ROLIK API", lifespan=lifespan)

# --- CONFIGURACIÓN CORS ---
# Esto permite que tu web en GitHub Pages entre al servidor de Render
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Luego puedes poner tu URL de GitHub aquí por seguridad
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELOS PYDANTIC ---
class SaleItemSchema(BaseModel):
    producto_codigo: str
    cantidad: float
    precio_unitario: float
    factor: float | None = 1.0
    unidad_nombre: str | None = None

class SaleRequest(BaseModel):
    user_id: int
    session_id: int | None = None
    total: float
    metodo_pago: str
    tipo_comprobante: str
    cliente_nombre: str | None = "PÚBLICO EN GENERAL"
    cliente_documento: str | None = "00000000"
    monto_pagado: float
    vuelto: float
    items: list[SaleItemSchema]

class LoginRequest(BaseModel):
    username: str
    password: str

class UnitSchema(BaseModel):
    nombre_unidad: str
    factor_conversion: float
    precio_venta: float

class ProductSchema(BaseModel):
    codigo: str
    nombre: str
    fabricante: str | None = None
    marca: str | None = None
    categoria: str | None = None
    descripcion: str | None = None
    precio_venta: float
    precio_compra: float | None = 0.0
    unidad: str | None = "UND"
    stock: float | None = 0.0
    stock_actual: float | None = 0.0
    stock_minimo: float = 5.0
    proveedor_nombre: str | None = None
    proveedor_id: int | None = None

class UserSchema(BaseModel):
    id: int | None = None
    username: str
    password: str | None = None
    role: str
    is_active: int = 1

class CashMovementSchema(BaseModel):
    user_id: int
    tipo: str
    monto: float
    descripcion: str

class POItemSchema(BaseModel):
    codigo: str
    cantidad: float
    precio_compra: float

class POSchema(BaseModel):
    proveedor_nombre: str
    ruc_dni: str
    items: list[POItemSchema]
    po_data: dict | None = {}

class CustomerSchema(BaseModel):
    id: int | None = None
    documento: str
    nombre: str
    direccion: str | None = ""
    telefono: str | None = ""
    email: str | None = ""

class SupplierSchema(BaseModel):
    id: int | None = None
    ruc_dni: str
    nombre: str
    direccion: str | None = ""
    telefono: str | None = ""
    email: str | None = ""

# --- MODULO: CAJA ---
@app.get("/caja/sesion-activa")
def obtener_caja_activa():
    try:
        session = database.get_active_session()
        if not session: return {"active": False}
        return {"active": True, "session": dict(session)}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/caja/abrir")
def abrir_caja(req: dict):
    try:
        database.open_cash_session(float(req.get('fondo_inicial', 0.0)), int(req.get('user_id')))
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/caja/cerrar")
def cerrar_caja(req: dict):
    try:
        session = database.get_active_session()
        if not session: raise HTTPException(status_code=404, detail="No hay sesión activa")
        summary = database.get_cash_session_summary(session['id'])
        database.close_cash_session(session['id'], summary['total_general'], int(req.get('user_id')))
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/caja/resumen")
def obtener_resumen_caja():
    try:
        session = database.get_active_session()
        if not session: raise HTTPException(status_code=404, detail="No hay sesión activa")
        return database.get_cash_session_summary(session['id'])
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/caja/movimiento")
def movimiento_caja(req: CashMovementSchema):
    try:
        session = database.get_active_session()
        database.add_cash_movement(session['id'], req.user_id, req.tipo, req.monto, req.descripcion)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/caja/historial")
def historial_cajas():
    try: return [dict(h) for h in database.get_cash_sessions_history()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --- MODULO: PRODUCTOS ---
@app.get("/productos")
def listar_productos(search: str = ""):
    try: return [dict(p) for p in database.get_all_products_for_display(search_term=search)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/productos")
def guardar_producto(prod: ProductSchema):
    try:
        database.add_or_update_product(prod.model_dump())
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.put("/productos/{codigo}")
def actualizar_producto(codigo: str, prod: ProductSchema):
    try:
        data = prod.model_dump()
        data['codigo'] = codigo 
        database.add_or_update_product(data)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/producto/{codigo}")
def obtener_producto(codigo: str):
    try:
        p = database.get_product(codigo)
        return dict(p) if p else None
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/productos/proximo-codigo")
def proximo_codigo():
    try: return {"codigo": database.get_next_product_code()}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/productos/{codigo}/unidades")
def obtener_unidades(codigo: str):
    try: return [dict(u) for u in database.get_product_units(codigo)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/productos-eliminados")
def listar_productos_eliminados():
    try: return [dict(r) for r in database.get_deleted_products()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/productos/restaurar/{codigo}")
def restaurar_producto(codigo: str):
    try:
        database.restore_product(codigo)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/productos/exportar")
def exportar_inventario():
    try:
        import csv
        import io
        from fastapi.responses import StreamingResponse
        
        products = database.get_all_products_for_display()
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Cabeceras actualizadas
        writer.writerow(["Codigo", "Nombre", "Descripcion", "Categoria", "Marca", "Unidad Base", "Presentaciones Adicionales", "Proveedor", "Stock", "Stock Minimo", "Precio Compra", "Precio Venta"])
        
        for p in products:
            # Obtener presentaciones adicionales de la base de datos
            units = database.get_product_units(p['codigo'])
            presentaciones_str = ""
            if units:
                presentaciones_str = " | ".join([
                    f"{u['nombre_unidad']} ({u['factor_conversion']} un.): S/ {u['precio_venta']:.2f}" 
                    for u in units
                ])
            
            writer.writerow([
                p['codigo'], p['nombre'], p['descripcion'] if 'descripcion' in p.keys() else '', p['categoria'], p['marca'], 
                p['unidad'], presentaciones_str, p['proveedor_nombre'], p['stock_actual'], 
                p['stock_minimo'], p['precio_compra'], p['precio_venta']
            ])
            
        output.seek(0)
        return StreamingResponse(
            output, 
            media_type="text/csv", 
            headers={"Content-Disposition": "attachment; filename=inventario_rolik_completo.csv"}
        )
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/productos/{codigo}/unidades")
def guardar_unidad(codigo: str, unit: UnitSchema):
    try:
        database.add_product_unit(codigo, unit.nombre_unidad, unit.factor_conversion, unit.precio_venta)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.delete("/productos/unidades/{id}")
def eliminar_unidad(id: int):
    try:
        database.delete_product_unit(id)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --- MODULO: CLIENTES ---
@app.get("/clientes-lista")
def listar_clientes(search: str = ""):
    try: return [dict(r) for r in database.get_all_customers(search_term=search)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/clientes/{documento}")
def obtener_cliente(documento: str):
    try:
        c = database.get_customer(documento)
        if not c: raise HTTPException(status_code=404, detail="Cliente no encontrado")
        return dict(c)
    except HTTPException as he: raise he
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/clientes")
def guardar_cliente(cli: CustomerSchema):
    try:
        database.add_or_update_customer(cli.model_dump())
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/clientes-eliminados")
def listar_clientes_eliminados():
    try: return [dict(r) for r in database.get_deleted_customers()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/clientes/restaurar/{documento}")
def restaurar_cliente(documento: str):
    try:
        database.restore_customer(documento)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --- MODULO: PROVEEDORES ---
@app.get("/proveedores-lista-completa")
def listar_proveedores_completo():
    try: return [dict(r) for r in database.get_all_suppliers_full()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/proveedores")
def guardar_proveedor(sup: SupplierSchema):
    try:
        database.add_or_update_supplier(sup.model_dump())
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.put("/proveedores/{id}")
def actualizar_proveedor(id: int, sup: SupplierSchema):
    try:
        data = sup.model_dump()
        data['id'] = id
        database.add_or_update_supplier(data)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/proveedores-detalles")
def listar_proveedores_detalles():
    try: return [dict(r) for r in database.get_all_suppliers_full()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/proveedores-lista")
def listar_proveedores_simple():
    try:
        res = database.get_all_suppliers_full()
        return [{"id": r["id"], "nombre": r["nombre"]} for r in res]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.delete("/proveedores/{id}")
def eliminar_proveedor(id: int):
    try:
        database.delete_supplier(id)
        return {"success": True}
    except ValueError as ve: raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/proveedores-eliminados")
def listar_proveedores_eliminados():
    try: return [dict(r) for r in database.get_deleted_suppliers()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/proveedores/restaurar/{id}")
def restaurar_proveedor(id: int):
    try:
        database.restore_supplier(id)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --- MODULO: COMPRAS ---
@app.get("/compras/ordenes")
def listar_compras():
    try: return [dict(o) for o in database.get_all_purchase_orders()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/compras/ordenes/{id}")
def obtener_detalles_compra(id: int):
    try:
        order = database.get_purchase_order_by_id(id)
        if not order: raise HTTPException(status_code=404, detail="Orden no encontrada")
        items = database.get_purchase_order_details(id)
        return {"orden": dict(order), "items": [dict(i) for i in items]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.patch("/compras/ordenes/{id}/estado")
def actualizar_estado_compra(id: int, estado: str):
    try:
        database.update_purchase_order_status(id, estado)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/compras/ordenes")
def crear_compra(req: POSchema):
    try:
        items_list = [(item.codigo, item.cantidad, item.precio_compra) for item in req.items]
        database.create_purchase_order(req.proveedor_nombre, req.ruc_dni, items_list, req.po_data)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.put("/compras/ordenes/{id}")
def actualizar_compra(id: int, req: POSchema):
    try:
        items_list = [(item.codigo, item.cantidad, item.precio_compra) for item in req.items]
        database.update_purchase_order(id, req.proveedor_nombre, req.ruc_dni, items_list, req.po_data)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.delete("/compras/ordenes/{id}")
def eliminar_compra(id: int):
    try:
        database.delete_purchase_order(id)
        return {"success": True}
    except ValueError as e: raise HTTPException(status_code=400, detail=str(e))
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --- MODULO: VENTAS ---
@app.get("/ventas/{id}/detalles")
def obtener_detalles_venta(id: int):
    try:
        sale, items = database.get_sale_full_details(id)
        if not sale: raise HTTPException(status_code=404, detail="No encontrada")
        return {"venta": dict(sale), "items": [dict(i) for i in items]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/ventas/{id}/anular")
def anular_venta(id: int, req: dict):
    try:
        success, msg = database.void_sale(id, req.get('user_id'), req.get('reason', 'Sin motivo'))
        if not success: raise HTTPException(status_code=400, detail=msg)
        return {"success": True, "message": msg}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.patch("/ventas/{id}/editar-basico")
def editar_basica_venta(id: int, req: dict):
    try:
        conn = database.get_connection()
        conn.execute("UPDATE transactions SET cliente_nombre = ?, cliente_documento = ?, tipo_comprobante = ?, metodo_pago = ? WHERE id = ?", 
                     (req.get('cliente_nombre'), req.get('cliente_documento'), req.get('tipo_comprobante'), req.get('metodo_pago'), id))
        conn.commit(); conn.close()
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/ventas")
def registrar_venta(req: SaleRequest):
    try:
        session = database.get_active_session()
        if not session:
            database.open_cash_session(0.0, req.user_id)
            session = database.get_active_session()
        
        if not session:
            raise Exception("No se pudo abrir ni obtener una sesión de caja activa.")

        cart_items = [(item.producto_codigo, item.cantidad, item.precio_unitario, item.factor or 1.0, item.unidad_nombre) for item in req.items]
        payment_data = {
            "metodo_pago": req.metodo_pago,
            "tipo_comprobante": req.tipo_comprobante,
            "cliente_nombre": req.cliente_nombre,
            "cliente_documento": req.cliente_documento,
            "monto_pagado": req.monto_pagado,
            "vuelto": req.vuelto
        }
        trans_id, correlativo = database.record_sale(session['id'], req.total, cart_items, req.user_id, payment_data)
        return {"success": True, "transaction_id": trans_id, "correlativo": correlativo}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- MODULO: USUARIOS ---
@app.get("/usuarios")
def listar_usuarios():
    try:
        conn = database.get_connection()
        res = conn.execute("SELECT id, username, role, is_active FROM users ORDER BY username ASC").fetchall()
        conn.close()
        return [dict(r) for r in res]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/usuarios")
def guardar_usuario(u: UserSchema):
    try:
        if u.id: database.update_user(u.id, u.username, u.password, u.role, u.is_active)
        else: database.add_user(u.username, u.password, u.role)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.delete("/usuarios/{user_id}")
def eliminar_usuario(user_id: int):
    try:
        # No permitir que el usuario elimine su propio usuario si es el último admin (opcional, pero buena práctica)
        database.delete_user(user_id)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/permisos")
def listar_permisos_disponibles():
    try: return [dict(p) for p in database.get_all_permissions()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/usuarios/{user_id}/permisos")
def obtener_permisos_usuario(user_id: int):
    try:
        # Obtener los nombres de los permisos
        perm_names = database.get_user_permissions(user_id)
        # También necesitamos los IDs para que el checkbox funcione en el frontend
        conn = database.get_connection()
        res = conn.execute("""
            SELECT permission_id FROM user_permissions WHERE user_id = ?
        """, (user_id,)).fetchall()
        conn.close()
        return {"names": list(perm_names), "ids": [r[0] for r in res]}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/usuarios/{user_id}/permisos")
def actualizar_permisos_usuario(user_id: int, perm_ids: list[int]):
    try:
        database.update_user_permissions(user_id, perm_ids)
        return {"success": True}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.post("/login")
def login(req: LoginRequest):
    try:
        user = database.authenticate_user(req.username, req.password)
        if not user: raise HTTPException(status_code=401, detail="Error")
        user['permissions'] = list(user['permissions'])
        return {"success": True, "user": user}
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --- MODULO: REPORTES ---
@app.get("/reportes/dashboard")
def obtener_dashboard():
    try:
        stats = database.get_dashboard_stats()
        return {
            "sales_today": stats['sales_today'], 
            "methods_today": stats['methods_today'],
            "total_clients_today": stats['total_clients_today'], 
            "alerta_stock": stats['alerta_stock']
        }
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/hoy/clientes")
def report_hoy_clientes():
    try: return [dict(r) for r in database.get_today_clients_details()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/hoy/productos")
def report_hoy_productos():
    try: return [dict(r) for r in database.get_today_products_details()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/stock-bajo")
def obtener_stock_bajo():
    try: return [dict(r) for r in database.get_report_low_stock()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/ventas-rango")
def report_ventas_rango(inicio: str, fin: str, metodo_pago: str = "TODOS"):
    try: return database.get_report_sales_by_range_filtered(inicio, fin, metodo_pago)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/ventas-por-producto")
def report_ventas_producto(inicio: str, fin: str, metodo_pago: str = "TODOS"):
    try: return [dict(r) for r in database.get_report_sales_by_product_filtered(inicio, fin, metodo_pago)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/ventas-por-categoria")
def report_ventas_categoria(inicio: str, fin: str, metodo_pago: str = "TODOS"):
    try: return [dict(r) for r in database.get_report_sales_by_category(inicio, fin, metodo_pago)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/ventas-por-categoria/detalles")
def report_ventas_categoria_detalles(categoria: str, inicio: str, fin: str):
    try: return [dict(r) for r in database.get_report_sales_by_category_details(categoria, inicio, fin)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/ventas-por-cliente")
def report_ventas_cliente(inicio: str, fin: str):
    try: return [dict(r) for r in database.get_report_sales_by_customer(inicio, fin)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/productos-por-cliente")
def report_productos_cliente(documento: str, inicio: str | None = None, fin: str | None = None):
    try: return [dict(r) for r in database.get_customer_product_sales(documento, inicio, fin)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/clientes-por-producto")
def report_clientes_producto(codigo: str, inicio: str | None = None, fin: str | None = None):
    try: return [dict(r) for r in database.get_product_customer_sales(codigo, inicio, fin)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/top-productos")
def report_top_productos(limit: int = 10):
    try: return [dict(r) for r in database.get_report_top_products(limit)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/vendedores")
def report_vendedores():
    try: return [dict(r) for r in database.get_report_sales_by_seller()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/utilidades")
def report_utilidades(inicio: str, fin: str):
    try: return [dict(r) for r in database.get_profitability_report(inicio, fin)]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/kardex")
def report_kardex():
    try: return [dict(r) for r in database.get_report_kardex()]
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/productos/{codigo}/kardex")
def obtener_kardex_producto(codigo: str):
    try: return database.get_product_kardex(codigo)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

@app.get("/reportes/historial-ventas")
def obtener_historial_ventas(inicio: str | None = None, fin: str | None = None):
    try:
        res = database.get_sales_history(start_date=inicio, end_date=fin)
        conn = database.get_connection(); ventas = []
        for v in res:
            v_dict = dict(v)
            extra = conn.execute("SELECT tipo_comprobante, correlativo, cliente_nombre, status FROM transactions WHERE id = ?", (v_dict['transaction_id'],)).fetchone()
            if extra: v_dict['comprobante'] = f"{extra['tipo_comprobante']} {extra['correlativo']}"; v_dict['cliente'] = extra['cliente_nombre']; v_dict['status'] = extra['status']
            ventas.append(v_dict)
        conn.close(); return ventas
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

def numero_a_letras(numero):
    from decimal import Decimal
    enteros = int(numero)
    centimos = int(round((numero - enteros) * 100))
    unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
    decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
    especiales = {11: "ONCE", 12: "DOCE", 13: "TRECE", 14: "CATORCE", 15: "QUINCE", 16: "DIECISEIS", 17: "DIECISIETE", 18: "DIECIOCHO", 19: "DIECINUEVE"}
    centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]
    def convertir_grupo(n):
        if n == 100: return "CIEN"
        res = ""
        c = n // 100; d = (n % 100) // 10; u = n % 10
        if c > 0: res += centenas[c] + " "
        if d == 1 and u > 0: res += especiales[d*10 + u]
        else:
            if d > 0: 
                res += decenas[d]
                if u > 0: res += " Y "
            if u > 0: res += unidades[u]
        return res.strip()
    if enteros == 0: texto = "CERO"
    elif enteros < 1000: texto = convertir_grupo(enteros)
    else:
        mif = enteros // 1000; resto = enteros % 1000
        prefijo = "MIL" if mif == 1 else convertir_grupo(mif) + " MIL"
        texto = f"{prefijo} {convertir_grupo(resto)}"
    return f"SON: {texto.strip()} CON {str(centimos).zfill(2)}/100 SOLES"

# --- MODULO: RECIBOS ---
@app.get("/ventas/{id}/ticket")
def obtener_ticket_html(id: int, format: str = "80mm"):
    try:
        sale_raw, items = database.get_sale_full_details(id)
        if not sale_raw: raise HTTPException(status_code=404, detail="No encontrada")
        sale = dict(sale_raw); items_list = [dict(item) for item in items]; is_a4 = format.upper() == "A4"
        seller_name = sale.get('seller_name') or "ADMINISTRADOR"
        monto_letras = numero_a_letras(sale['total'])
        st_b = "color: #000000 !important; -webkit-text-fill-color: #000000 !important; opacity: 1 !important; font-weight: 900 !important;"
        reset_st = "* { background-color: #ffffff !important; color: #000000 !important; -webkit-print-color-adjust: exact !important; }"
        if is_a4:
            primary_teal = "#00a896"
            html = f"""<html><head><meta charset="UTF-8"><meta name="color-scheme" content="light"><style>{reset_st} @media print {{ .no-print {{ display: none !important; }} }} body {{ margin: 0; padding: 40px; background-color: #ffffff !important; font-family: Arial, sans-serif !important; }} .ticket-container {{ max-width: 850px; margin: 0 auto; background-color: #ffffff !important; }}</style></head>
            <body style="background-color: #ffffff !important;">
                <div class="no-print" style="text-align: center; padding: 15px; background: #eee; margin-bottom: 20px;"><button onclick="window.print()" style="padding: 10px 25px; background: #000; color: #fff !important; border: none; cursor: pointer; border-radius: 4px; font-weight: bold;">IMPRIMIR A4</button></div>
                <div class="ticket-container">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 30px;"><div style="{st_b}"><h1 style="margin: 0; font-size: 42px; {st_b} letter-spacing: -1px;">ROLIK</h1><div style="font-size: 13px; {st_b} line-height: 1.4; margin-top: 5px;">RUC: 10440809320 | Telf: 988352912<br>PQ IND. MADERA MZ A LT 26 - ATE</div></div><div style="border: 2px solid #000; padding: 15px 30px; text-align: center; min-width: 280px; border-radius: 8px; background-color: #ffffff !important;"><h2 style="{st_b}">{sale['tipo_comprobante']}</h2><h1 style="{st_b}">N° {sale['correlativo']}</h1></div></div>
                    <div style="display: flex; justify-content: space-between; margin-bottom: 40px; padding: 15px; border-top: 1px solid #000; border-bottom: 1px solid #000; background-color: #ffffff !important;"><div style="line-height: 1.8; {st_b}"><div>ADQUIRIENTE: {sale['cliente_nombre'] or "PÚBLICO EN GENERAL"}</div><div>DNI/RUC: {sale['cliente_documento'] or "00000000"}</div></div><div style="text-align: right; line-height: 1.8; {st_b}"><div>FECHA: {sale['date'][:10]}</div><div>MÉTODO: {sale['metodo_pago']}</div></div></div>
                    <table style="width: 100%; border-collapse: collapse; margin-top: 20px; background-color: #ffffff !important;"><thead><tr><th style="background-color: {primary_teal} !important; color: white !important; padding: 12px; text-align: left; border: none;">NO.</th><th style="background-color: {primary_teal} !important; color: white !important; padding: 12px; text-align: left; border: none;">PRODUCT DESCRIPTION</th><th style="background-color: {primary_teal} !important; color: white !important; padding: 12px; text-align: right; border: none;">PRICE</th><th style="background-color: {primary_teal} !important; color: white !important; padding: 12px; text-align: center; border: none;">QTY.</th><th style="background-color: {primary_teal} !important; color: white !important; padding: 12px; text-align: right; border: none;">TOTAL</th></tr></thead><tbody>
            """
            for i, item in enumerate(items_list):
                sub = item['quantity'] * item['unit_price']; desc = f"{item['nombre']} ({item['unidad_venta']})" if item.get('unidad_venta') else item['nombre']; bg = "#f8fafc" if i % 2 != 0 else "#ffffff"
                html += f"<tr style='background-color: {bg} !important;'><td style='padding: 12px; border-bottom: 1px solid #000; text-align: center; {st_b}'>{str(i+1).zfill(2)}</td><td style='padding: 12px; border-bottom: 1px solid #000; {st_b}'>{desc}</td><td style='padding: 12px; border-bottom: 1px solid #000; text-align: right; {st_b}'>{item['unit_price']:,.2f}</td><td style='padding: 12px; border-bottom: 1px solid #000; text-align: center; {st_b}'>{item['quantity']}</td><td style='padding: 12px; border-bottom: 1px solid #000; text-align: right; {st_b}'>{sub:,.2f}</td></tr>"
            html += f"""</tbody></table><div style="display: flex; flex-direction: column; align-items: flex-end; margin-top: 30px;"><div style="font-size: 32px; font-weight: 900; color: {primary_teal} !important; padding-top: 20px;">TOTAL: S/ {sale['total']:,.2f}</div></div></div><script>window.onload = function() {{ if(!window.location.search.includes('no_print')) setTimeout(() => {{ window.print(); }}, 500); }}</script></body></html>"""
            return HTMLResponse(content=html)
        else:
            st_t = "color: #000000 !important; background-color: #ffffff !important; font-family: 'Courier New', Courier, monospace !important; font-size: 10px; font-weight: 900 !important;"
            html = f"""<html><head><meta charset="UTF-8"><meta name="color-scheme" content="light"><style>{reset_st} @media print {{ .no-print {{ display: none !important; }} }} body {{ width: 275px; margin: 0 auto; }}</style></head>
            <body style="padding: 10px; {st_t} background-color: #ffffff !important;">
                <div class="no-print" style="text-align: center; padding: 15px; background: #eee; border-bottom: 1px solid #ccc;"><button onclick="window.print()" style="padding: 10px 20px; background: #22c55e; color: white !important; border: none; cursor: pointer; font-weight:bold;">IMPRIMIR</button></div>
                <div class="ticket-container" style="background-color: #ffffff !important; {st_b}">
                    <div style="text-align: center; {st_b}"><div style="font-size: 16px; {st_b}">FERRETERÍA ROLIK</div><div style="font-size: 11px; {st_b}">RUC: 10440809320 | Tel: 988352912</div></div>
                    <div style="border-top: 1.5px solid #000 !important; margin: 8px 0;"></div>
                    <div style="text-align: center; {st_b}"><div style="font-size: 13px; {st_b}">{sale['tipo_comprobante']} INTERNA</div><div style="font-size: 13px; {st_b}">{sale['correlativo']}</div></div>
                    <div style="border-top: 1.5px solid #000 !important; margin: 8px 0;"></div>
                    <div style="font-size: 11px; line-height: 1.4; {st_b}"><div style="{st_b}">FECHA: {sale['date']}</div><div style="{st_b}">CLI : {sale['cliente_nombre'][:22]}</div><div style="{st_b}">DOC : {sale['cliente_documento']}</div></div>
                    <div style="border-top: 1.5px solid #000 !important; margin: 8px 0;"></div>
                    <div style="display: flex; font-weight: 900; font-size: 11px; border-bottom: 1.5px solid #000 !important; padding-bottom: 3px; {st_b}"><div style="width: 30px; {st_b}">CT.</div><div style="flex: 1; padding-left: 4px; {st_b}">DESC.</div><div style="width: 50px; text-align: right; {st_b}">P.U.</div><div style="width: 60px; text-align: right; {st_b}">TOTAL</div></div>
            """
            for item in items_list:
                sub = item['quantity'] * item['unit_price']; unidad = f" ({item['unidad_venta']})" if item.get('unidad_venta') else ""
                html += f"""<div style="display: flex; margin-top: 5px; align-items: flex-start; font-size: 10.5px; {st_b}"><div style="width: 30px; {st_b}">{item['quantity']}</div><div style="flex: 1; padding-left: 4px; word-wrap: break-word; {st_b}">{item['nombre']}{unidad}</div><div style="width: 50px; text-align: right; {st_b}">{item['unit_price']:,.2f}</div><div style="width: 60px; text-align: right; {st_b}">{sub:,.2f}</div></div>"""
            html += f"""<div style="border-top: 1.5px solid #000 !important; margin: 10px 0 5px 0; padding-top: 5px; text-align: right;"><strong style="font-size: 16px; {st_b}">TOTAL: S/ {sale['total']:,.2f}</strong></div><div style="text-align: center; margin-top: 30px; {st_b} font-size: 11px;">¡GRACIAS POR SU COMPRA!</div></div><script>window.onload = function() {{ if(!window.location.search.includes('no_print')) setTimeout(() => {{ window.print(); }}, 500); }}</script></body></html>"""
            return HTMLResponse(content=html)
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))

# --- SERVIR FRONTEND ---
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pagina_web"))
print(f"DEBUG: Sirviendo archivos estáticos desde: {frontend_path}")

if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
else:
    print(f"CRITICAL: No se encontró la carpeta del frontend en {frontend_path}")

if __name__ == "__main__":
    import uvicorn
    # Cambiamos al puerto 8001 para evitar conflictos
    uvicorn.run(app, host="0.0.0.0", port=8001)

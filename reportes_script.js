// reportes_script.js - Lógica para reportes avanzados en ROLIK ERP

let currentReportType = '';
let selectedReceiptId = null;

document.addEventListener('DOMContentLoaded', () => {
    const hoy = new Date().toISOString().split('T')[0];
    const startInput = document.getElementById('rep_start');
    const endInput = document.getElementById('rep_end');
    
    if (startInput) startInput.value = hoy;
    if (endInput) endInput.value = hoy;

    const applyBtn = document.getElementById('btn_apply_filter');
    if (applyBtn) {
        applyBtn.addEventListener('click', () => loadReportData());
    }
    
    const searchInput = document.getElementById('report_search_input');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(() => filterReportTable(), 300));
    }

    // Búsqueda de clientes en edición de recibo
    const editClienteNombre = document.getElementById('edit_cliente_nombre');
    if (editClienteNombre) {
        editClienteNombre.addEventListener('input', (e) => buscarClientesAutocompleteReportes(e.target.value));
        editClienteNombre.addEventListener('blur', () => setTimeout(() => ocultarSugerenciasReportes(), 200));
    }

    // Cerrar modal al hacer clic fuera
    window.onclick = function(event) {
        const modal = document.getElementById('receipt_modal');
        if (event.target == modal) closeReceiptModal();
    }
});

function showMenu() {
    document.getElementById('view_menu').classList.add('active-view');
    document.getElementById('view_report_detail').classList.remove('active-view');
    document.getElementById('view_title').innerText = "Reportes del Sistema";
    selectedReceiptId = null;
}

function showReport(type) {
    currentReportType = type;
    document.getElementById('view_menu').classList.remove('active-view');
    document.getElementById('view_report_detail').classList.add('active-view');
    
    const searchInput = document.getElementById('report_search_input');
    if (searchInput) searchInput.value = "";
    
    const filters = document.getElementById('report_filters');
    const grpMetodo = document.getElementById('grp_metodo_pago');
    const searchContainer = document.getElementById('report_search_container');
    const historialActions = document.getElementById('historial_actions');

    if (filters) filters.style.display = 'flex';
    if (grpMetodo) grpMetodo.style.display = 'block';
    if (searchContainer) searchContainer.style.display = 'none'; 
    if (historialActions) historialActions.style.display = 'none';

    let title = "";
    switch(type) {
        case 'ventas_hoy': title = "Ventas del Día"; if (filters) filters.style.display = 'none'; break;
        case 'ventas_rango': title = "Resumen de Ventas y Ganancias"; break;
        case 'utilidades': title = "Reporte de Ganancias Reales"; if (grpMetodo) grpMetodo.style.display = 'none'; break;
        case 'ventas_producto': title = "Ventas por Producto"; if (searchContainer) searchContainer.style.display = 'block'; break;
        case 'ventas_categoria': title = "Ventas por Categoría"; if (searchContainer) searchContainer.style.display = 'block'; break;
        case 'ventas_cliente': title = "Compras por Cliente"; if (grpMetodo) grpMetodo.style.display = 'none'; if (searchContainer) searchContainer.style.display = 'block'; break;
        case 'top_productos': title = "Top 10 Productos"; if (filters) filters.style.display = 'none'; break;
        case 'bajo_stock': title = "Alerta de Stock Bajo"; if (filters) filters.style.display = 'none'; break;
        case 'kardex': title = "Kardex de Inventario"; if (filters) filters.style.display = 'none'; break;
        case 'historial_recibos': 
            title = "Historial de Recibos"; 
            if (historialActions) {
                historialActions.style.display = 'flex';
                historialActions.className = 'action-bar-bottom active'; // Asegurar que sea visible
            }
            break;
        case 'ventas_vendedor': title = "Ventas por Vendedor"; if (filters) filters.style.display = 'none'; break;
    }

    document.getElementById('view_title').innerText = title;
    loadReportData();
}

async function loadReportData() {
    const start = document.getElementById('rep_start').value;
    const end = document.getElementById('rep_end').value;
    const metodo = document.getElementById('rep_metodo').value;
    const tbody = document.getElementById('report_tbody');
    const stats = document.getElementById('report_stats');

    if (tbody) tbody.innerHTML = '<tr><td colspan="10" class="loading">Cargando datos...</td></tr>';
    if (stats) stats.style.display = 'none';
    selectedReceiptId = null;

    try {
        let url = "";
        switch(currentReportType) {
            case 'ventas_hoy': url = `${API_URL}/reportes/dashboard`; break;
            case 'ventas_rango': url = `${API_URL}/reportes/ventas-rango?inicio=${start}&fin=${end}&metodo_pago=${metodo}`; break;
            case 'ventas_producto': url = `${API_URL}/reportes/ventas-por-producto?inicio=${start}&fin=${end}&metodo_pago=${metodo}`; break;
            case 'ventas_categoria': url = `${API_URL}/reportes/ventas-por-categoria?inicio=${start}&fin=${end}&metodo_pago=${metodo}`; break;
            case 'ventas_cliente': url = `${API_URL}/reportes/ventas-por-cliente?inicio=${start}&fin=${end}`; break;
            case 'top_productos': url = `${API_URL}/reportes/top-productos?limit=10`; break;
            case 'bajo_stock': url = `${API_URL}/reportes/stock-bajo`; break;
            case 'kardex': url = `${API_URL}/reportes/kardex`; break;
            case 'historial_recibos': url = `${API_URL}/reportes/historial-ventas?inicio=${start}&fin=${end}`; break;
            case 'ventas_vendedor': url = `${API_URL}/reportes/vendedores`; break;
            case 'utilidades': url = `${API_URL}/reportes/utilidades?inicio=${start}&fin=${end}`; break;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        switch(currentReportType) {
            case 'ventas_hoy': renderVentasHoy(data); break;
            case 'ventas_rango': renderVentasRango(data); break;
            case 'ventas_producto': renderVentasProducto(data); break;
            case 'ventas_categoria': renderVentasCategoria(data); break;
            case 'ventas_cliente': renderVentasCliente(data); break;
            case 'top_productos': renderTopProductos(data); break;
            case 'bajo_stock': renderBajoStock(data); break;
            case 'kardex': renderKardex(data); break;
            case 'historial_recibos': renderHistorialRecibos(data); break;
            case 'ventas_vendedor': renderVendedores(data); break;
            case 'utilidades': renderUtilidades(data); break;
        }
    } catch (error) {
        if (tbody) tbody.innerHTML = '<tr><td colspan="10" class="error">Error al cargar el reporte</td></tr>';
        notify.error("Error al procesar los datos");
    }
}

// ... (renderVentasHoy, renderVentasRango, etc. se mantienen igual o se ajustan mínimamente)

function renderHistorialRecibos(data) {
    const columns = [
        { key: 'transaction_id', label: 'ID' },
        { key: 'transaction_date', label: 'Fecha', formatter: val => `<small>${val}</small>` },
        { key: 'comprobante', label: 'Comprobante', formatter: val => `<strong>${val}</strong>` },
        { key: 'cliente', label: 'Cliente' },
        { key: 'transaction_total', label: 'Total', formatter: val => `S/ ${val.toFixed(2)}` },
        { 
            key: 'status', 
            label: 'Estado',
            formatter: val => `<span class="badge ${val === 'COMPLETED' ? 'badge-green' : 'badge-red'}">${val === 'COMPLETED' ? 'PAGADO' : 'ANULADO'}</span>` 
        },
        {
            key: 'transaction_id',
            label: 'PDF',
            formatter: val => `
                <div style="display:flex; gap:5px;">
                    <button class="action-btn" style="background:#ef4444;" onclick="event.stopPropagation(); descargarPDF(${val}, '80mm')" title="Ticket"><i class="fas fa-file-pdf"></i></button>
                    <button class="action-btn" style="background:#dc2626;" onclick="event.stopPropagation(); descargarPDF(${val}, 'A4')" title="A4"><i class="fas fa-file-invoice"></i></button>
                </div>
            `
        }
    ];

    const tbody = document.getElementById('report_tbody');
    tbody.innerHTML = "";
    
    data.forEach(item => {
        const tr = document.createElement('tr');
        tr.style.cursor = "pointer";
        tr.onclick = () => selectReceiptRow(tr, item.transaction_id);
        
        columns.forEach(col => {
            const td = document.createElement('td');
            const val = item[col.key];
            td.innerHTML = col.formatter ? col.formatter(val, item) : val;
            tr.appendChild(td);
        });
        tbody.appendChild(tr);
    });
}

function selectReceiptRow(row, id) {
    document.querySelectorAll('#report_tbody tr').forEach(r => r.classList.remove('selected-row'));
    row.classList.add('selected-row');
    selectedReceiptId = id;
    notify.info(`Recibo #${id} seleccionado`);
}

// --- Funciones de Acción de Recibos ---

async function viewSelectedReceipt() {
    if (!selectedReceiptId) return notify.warn("Seleccione un recibo de la lista");
    window.open(`${API_URL}/ventas/${selectedReceiptId}/ticket?format=80mm`, '_blank');
}

async function editSelectedReceipt() {
    if (!selectedReceiptId) return notify.warn("Seleccione un recibo");
    try {
        const res = await fetch(`${API_URL}/ventas/${selectedReceiptId}/detalles`);
        const data = await res.json();
        const v = data.venta;
        
        document.getElementById('edit_sale_id').value = v.id;
        document.getElementById('edit_cliente_nombre').value = v.cliente_nombre || "";
        document.getElementById('edit_cliente_doc').value = v.cliente_documento || "";
        document.getElementById('edit_tipo_comp').value = v.tipo_comprobante;
        document.getElementById('edit_metodo').value = v.metodo_pago;
        
        document.getElementById('receipt_items_body').innerHTML = data.items.map(item => `
            <tr>
                <td>${item.nombre}</td>
                <td>${item.quantity}</td>
                <td>S/ ${item.unit_price.toFixed(2)}</td>
                <td>S/ ${(item.quantity * item.unit_price).toFixed(2)}</td>
            </tr>
        `).join('');
        
        document.getElementById('receipt_total').innerText = v.total.toFixed(2);
        document.getElementById('receipt_modal').style.display = 'block';
        document.getElementById('receipt_modal_title').innerText = v.status === 'VOIDED' ? "Recibo (ANULADO)" : "Detalle de Recibo";
        
        // Habilitar botón de guardar si no está anulado
        const btnSave = document.getElementById('btn_save_receipt');
        if (btnSave) btnSave.style.display = v.status === 'VOIDED' ? 'none' : 'inline-block';
        
    } catch (error) { notify.error("Error al cargar detalles"); }
}

async function guardarEdicionRecibo() {
    const id = document.getElementById('edit_sale_id').value;
    const data = {
        cliente_nombre: document.getElementById('edit_cliente_nombre').value,
        cliente_documento: document.getElementById('edit_cliente_doc').value,
        tipo_comprobante: document.getElementById('edit_tipo_comp').value,
        metodo_pago: document.getElementById('edit_metodo').value
    };

    try {
        const res = await fetch(`${API_URL}/ventas/${id}/editar-basico`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            notify.success("Recibo actualizado correctamente");
            closeReceiptModal();
            loadReportData();
        } else { notify.error("No se pudo actualizar"); }
    } catch (e) { notify.error("Error de conexión"); }
}

// Agregar el listener al formulario del modal
document.addEventListener('DOMContentLoaded', () => {
    const editForm = document.getElementById('receipt_edit_form');
    if (editForm) {
        editForm.onsubmit = (e) => {
            e.preventDefault();
            guardarEdicionRecibo();
        };
    }
});

async function voidSelectedSale() {
    if (!selectedReceiptId) return notify.warn("Seleccione un recibo");
    const reason = prompt("Motivo de anulación:");
    if (!reason) return;
    
    if (!confirm("¿Estás seguro de anular este recibo? Esta acción revertirá el stock.")) return;
    
    try {
        const user = getLoggedInUser();
        const response = await fetch(`${API_URL}/ventas/${selectedReceiptId}/anular`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id, reason: reason })
        });
        
        if (response.ok) {
            notify.success("Recibo anulado correctamente");
            loadReportData();
        } else {
            const err = await response.json();
            notify.error("Error: " + (err.detail || "No se pudo anular"));
        }
    } catch (error) { notify.error("Error de conexión"); }
}

function closeReceiptModal() {
    document.getElementById('receipt_modal').style.display = 'none';
}

function printFromModal() {
    const id = document.getElementById('edit_sale_id').value;
    window.open(`${API_URL}/ventas/${id}/ticket`, '_blank');
}

// ... (Resto de funciones renderVentasHoy, renderVentasRango, etc. se mantienen)

function renderVentasHoy(dash) {
    const stats = document.getElementById('report_stats');
    const methods = dash.methods_today || {};
    let methodsHtml = '';
    const icons = { 'EFECTIVO': '💸', 'TRANSFERENCIA': '💳', 'YAPE/PLIN': '📱', 'TARJETA': '💳' };
    
    // Tarjeta principal (Todas las ventas)
    let html = `<div class="stat-card" style="background: var(--accent-color); cursor:pointer;" onclick="openTodayProductsModal()" title="Ver productos vendidos hoy">
        <h3>Total Ventas Hoy</h3>
        <p class="value">S/ ${(dash.sales_today || 0).toFixed(2)}</p>
    </div>`;

    // Tarjetas por método
    Object.keys(methods).forEach(m => {
        html += `
        <div class="stat-card" style="cursor:pointer;" onclick="openTodayProductsModal('${m}')" title="Ver productos vendidos con ${m}">
            <h3>${icons[m] || '💰'} ${m}</h3>
            <p class="value">S/ ${methods[m].toFixed(2)}</p>
        </div>`;
    });
    
    stats.innerHTML = html;
    stats.style.display = 'grid';

    // Tabla de indicadores
    document.getElementById('report_thead').innerHTML = '<tr><th>Indicador</th><th>Valor</th></tr>';
    document.getElementById('report_tbody').innerHTML = `
        <tr onclick="openTodayClientsModal()" style="cursor:pointer;" title="Click para ver quiénes son">
            <td><i class="fas fa-users"></i> Total Clientes Atendidos</td>
            <td><strong>${dash.total_clients_today || 0}</strong></td>
        </tr>
        <tr onclick="showReport('bajo_stock')" style="cursor:pointer;">
            <td><i class="fas fa-exclamation-triangle"></i> Productos en Alerta de Stock</td>
            <td><strong style="color:#ef4444">${dash.alerta_stock || 0}</strong></td>
        </tr>
        <tr onclick="openTodayProductsModal()" style="cursor:pointer;" title="Ver desglose de productos">
            <td><i class="fas fa-box"></i> Desglose de Productos Vendidos Hoy</td>
            <td><i class="fas fa-chevron-right"></i></td>
        </tr>
    `;
}

async function openTodayClientsModal() {
    const modal = document.getElementById('today_clients_modal');
    const tbody = document.getElementById('tc_tbody');
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px;">Cargando clientes...</td></tr>';
    modal.style.display = 'block';

    try {
        const res = await fetch(`${API_URL}/reportes/hoy/clientes`);
        const data = await res.json();
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px;">No hubo clientes atendidos hoy.</td></tr>';
            return;
        }
        tbody.innerHTML = data.map(c => `
            <tr>
                <td><strong>${c.cliente_nombre}</strong><br><small>${c.cliente_documento}</small></td>
                <td style="text-align:center;">${c.transacciones}</td>
                <td style="text-align:right;">S/ ${c.total_dia.toFixed(2)}</td>
                <td><small>${c.hora_ultima.split(' ')[1]}</small></td>
            </tr>
        `).join('');
    } catch (e) { tbody.innerHTML = '<tr><td colspan="4" class="error">Error al cargar.</td></tr>'; }
}

async function openTodayProductsModal(filtroMetodo = null) {
    const modal = document.getElementById('today_products_modal');
    const tbody = document.getElementById('tp_tbody');
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:20px;">Cargando productos...</td></tr>';
    modal.style.display = 'block';

    try {
        // Por ahora usamos el endpoint de hoy, si quisiéramos filtrar por método 
        // podríamos usar el reporte de productos por rango con fechas de hoy
        let url = `${API_URL}/reportes/hoy/productos`;
        if (filtroMetodo) {
            const hoy = new Date().toISOString().split('T')[0];
            url = `${API_URL}/reportes/ventas-por-producto?inicio=${hoy}&fin=${hoy}&metodo_pago=${filtroMetodo}`;
        }

        const res = await fetch(url);
        const data = await res.json();
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:20px;">No hay productos registrados hoy.</td></tr>';
            return;
        }

        // Normalizar nombres de campos si vienen del reporte general
        tbody.innerHTML = data.map(p => `
            <tr>
                <td><strong>${p.nombre || p.producto_nombre}</strong><br><small>${p.codigo || p.producto_codigo}</small></td>
                <td style="text-align:center;">${p.cantidad_total || p.cant_vendida}</td>
                <td style="text-align:right;">S/ ${(p.monto_total || p.total_generado).toFixed(2)}</td>
            </tr>
        `).join('');
    } catch (e) { tbody.innerHTML = '<tr><td colspan="3" class="error">Error al cargar.</td></tr>'; }
}

function closeModal(id) {
    document.getElementById(id).style.display = 'none';
}

function renderVentasRango(data) {
    const stats = document.getElementById('report_stats');
    // Los datos ahora vienen en la raíz del objeto retornado por la API
    const ingresos = data.ingresos_brutos !== undefined ? data.ingresos_brutos : (data.resumen ? data.resumen.ingresos_brutos : 0);
    const ganancia = data.ganancia_estimada !== undefined ? data.ganancia_estimada : (data.resumen ? data.resumen.ganancia_estimada : 0);
    
    stats.innerHTML = `<div class="stat-card"><h3>Ingresos Brutos</h3><p class="value">S/ ${ingresos.toFixed(2)}</p></div><div class="stat-card" style="background: rgba(34, 197, 94, 0.1); border: 1px solid var(--success);"><h3>Utilidad Estimada</h3><p class="value" style="color:var(--success)">S/ ${ganancia.toFixed(2)}</p></div>`;
    stats.style.display = 'grid';
    document.getElementById('report_thead').innerHTML = '<tr><th>Método de Pago</th><th>Monto Total</th></tr>';
    const metodos = data.por_metodo || {};
    document.getElementById('report_tbody').innerHTML = Object.keys(metodos).map(m => `<tr><td>${m}</td><td><strong>S/ ${metodos[m].toFixed(2)}</strong></td></tr>`).join('') || '<tr><td colspan="2" style="text-align:center">Sin ventas en este rango</td></tr>';
}

function renderVentasProducto(data) {
    document.getElementById('report_thead').innerHTML = '<tr><th>Producto</th><th style="text-align:center;">Cant. Vendida</th><th style="text-align:right;">Total Generado</th><th style="text-align:right;">Utilidad Est.</th></tr>';
    document.getElementById('report_tbody').innerHTML = data.map(p => `
        <tr onclick="openProductCustomersModal('${p.codigo}', '${p.nombre}')" style="cursor:pointer;" title="Click para ver clientes que compraron este producto">
            <td><strong>${p.nombre}</strong><br><small class="text-muted">${p.codigo}</small></td>
            <td style="text-align:center;">${p.cant_vendida}</td>
            <td style="text-align:right;">S/ ${p.total_generado.toFixed(2)}</td>
            <td style="text-align:right; color:var(--success); font-weight:bold;">S/ ${p.margen_ganancia.toFixed(2)}</td>
        </tr>
    `).join('');
}

async function openProductCustomersModal(codigo, nombre) {
    const modal = document.getElementById('product_customers_modal');
    const tbody = document.getElementById('pc_tbody');
    const title = document.getElementById('pc_modal_title');
    
    title.innerText = `Clientes: ${nombre}`;
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px;">Cargando clientes...</td></tr>';
    modal.style.display = 'block';

    try {
        const start = document.getElementById('rep_start').value;
        const end = document.getElementById('rep_end').value;
        const response = await fetch(`${API_URL}/reportes/clientes-por-producto?codigo=${codigo}&inicio=${start}&fin=${end}`);
        const customers = await response.json();

        if (!customers || customers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px;">Ningún cliente ha comprado este producto en este rango de fechas.</td></tr>';
            return;
        }

        tbody.innerHTML = customers.map(c => `
            <tr>
                <td>
                    <strong>${c.cliente_nombre}</strong><br>
                    <small>${c.cliente_documento}</small>
                </td>
                <td style="text-align:center; font-weight:bold; color:#10b981;">${c.cantidad_total}</td>
                <td style="text-align:right;">S/ ${c.monto_total.toFixed(2)}</td>
                <td><small>${c.ultima_vez_comprado}</small></td>
            </tr>
        `).join('');
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px; color:#ef4444;">Error al cargar ranking de clientes.</td></tr>';
    }
}

function closeProductCustomersModal() {
    document.getElementById('product_customers_modal').style.display = 'none';
}

function renderVentasCategoria(data) {
    document.getElementById('report_thead').innerHTML = '<tr><th>Categoría</th><th style="text-align:center;">Cant. Vendida</th><th style="text-align:right;">Total Generado S/</th><th style="text-align:right;">Utilidad Est.</th></tr>';
    document.getElementById('report_tbody').innerHTML = data.map(c => `
        <tr onclick="openCategoryProductsModal('${c.categoria}')" style="cursor:pointer;" title="Click para ver productos de esta categoría">
            <td><strong>${c.categoria}</strong></td>
            <td style="text-align:center;">${c.cant_vendida}</td>
            <td style="text-align:right;">S/ ${c.total_generado.toFixed(2)}</td>
            <td style="text-align:right; color:var(--success); font-weight:bold;">S/ ${c.margen_ganancia.toFixed(2)}</td>
        </tr>
    `).join('');
}

async function openCategoryProductsModal(categoria) {
    const modal = document.getElementById('category_products_modal');
    const tbody = document.getElementById('catp_tbody');
    const title = document.getElementById('catp_modal_title');

    title.innerText = `Productos en: ${categoria}`;
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:20px;">Cargando productos...</td></tr>';
    modal.style.display = 'block';

    try {
        const start = document.getElementById('rep_start').value;
        const end = document.getElementById('rep_end').value;
        // Reutilizamos el endpoint de detalles de categoría que creamos en main_api.py
        const response = await fetch(`${API_URL}/reportes/ventas-por-categoria/detalles?categoria=${encodeURIComponent(categoria)}&inicio=${start}&fin=${end}`);
        const products = await response.json();

        if (!products || products.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:20px;">No se encontraron productos vendidos en esta categoría.</td></tr>';
            return;
        }

        tbody.innerHTML = products.map(p => `
            <tr>
                <td><strong>${p.nombre}</strong><br><small class="text-muted">${p.codigo}</small></td>
                <td style="text-align:center;">${p.cant_vendida}</td>
                <td style="text-align:right;">S/ ${p.total_generado.toFixed(2)}</td>
            </tr>
        `).join('');
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:20px; color:#ef4444;">Error al cargar productos.</td></tr>';
    }
}

function renderVentasCliente(data) {

    document.getElementById('report_thead').innerHTML = '<tr><th>Cliente</th><th style="text-align:center;">N° Compras</th><th style="text-align:right;">Inversión Total</th><th>Última Visita</th></tr>';
    document.getElementById('report_tbody').innerHTML = data.map(c => `
        <tr onclick="openCustomerProductsModal('${c.documento}', '${c.nombre}')" style="cursor:pointer;" title="Click para ver detalle de productos">
            <td><strong>${c.nombre}</strong><br><small>${c.documento}</small></td>
            <td style="text-align:center;">${c.num_compras}</td>
            <td style="text-align:right;"><strong>S/ ${c.total_comprado.toFixed(2)}</strong></td>
            <td><small>${c.ultima_compra}</small></td>
        </tr>
    `).join('');
}

async function openCustomerProductsModal(documento, nombre) {
    const modal = document.getElementById('customer_products_modal');
    const tbody = document.getElementById('cp_tbody');
    const title = document.getElementById('cp_modal_title');
    
    title.innerText = `Productos Comprados: ${nombre}`;
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px;">Cargando productos...</td></tr>';
    modal.style.display = 'block';

    try {
        const start = document.getElementById('rep_start').value;
        const end = document.getElementById('rep_end').value;
        const response = await fetch(`${API_URL}/reportes/productos-por-cliente?documento=${documento}&inicio=${start}&fin=${end}`);
        const products = await response.json();

        if (!products || products.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px;">No se encontraron productos comprados en este rango de fechas.</td></tr>';
            return;
        }

        tbody.innerHTML = products.map(p => `
            <tr>
                <td>
                    <strong>${p.producto_nombre}</strong><br>
                    <small>${p.producto_codigo}</small>
                </td>
                <td style="text-align:center; font-weight:bold; color:#3b82f6;">${p.cantidad_total}</td>
                <td style="text-align:right;">S/ ${p.monto_total.toFixed(2)}</td>
                <td><small>${p.ultima_vez_comprado}</small></td>
            </tr>
        `).join('');
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding:20px; color:#ef4444;">Error al cargar detalles de productos.</td></tr>';
    }
}

function closeCustomerProductsModal() {
    document.getElementById('customer_products_modal').style.display = 'none';
}

function renderTopProductos(data) {
    document.getElementById('report_thead').innerHTML = '<tr><th>#</th><th>Producto</th><th>Vendidos</th></tr>';
    document.getElementById('report_tbody').innerHTML = data.map((p, i) => `<tr><td>${i+1}</td><td><strong>${p.nombre}</strong></td><td><span class="badge badge-blue">${p.total_qty}</span></td></tr>`).join('');
}

function renderBajoStock(data) {
    document.getElementById('report_thead').innerHTML = '<tr><th>Producto</th><th>Stock</th><th>Mínimo</th></tr>';
    document.getElementById('report_tbody').innerHTML = data.map(p => `<tr><td><strong>${p.nombre}</strong><br><small>${p.codigo}</small></td><td><span class="badge badge-red">${p.stock}</span></td><td>${p.stock_minimo}</td></tr>`).join('');
}

function renderKardex(data) {
    document.getElementById('report_thead').innerHTML = '<tr><th>Fecha</th><th>Tipo</th><th>Producto</th><th>Cant.</th></tr>';
    document.getElementById('report_tbody').innerHTML = data.map(k => `<tr><td><small>${k.date}</small></td><td><span class="badge ${k.tipo.includes('ENTRADA') ? 'badge-blue' : 'badge-orange'}">${k.tipo}</span></td><td><code>${k.producto_codigo}</code></td><td><strong>${k.cant}</strong></td></tr>`).join('');
}

function renderVendedores(data) {
    document.getElementById('report_thead').innerHTML = '<tr><th>Vendedor</th><th>Ventas</th><th>Total</th></tr>';
    document.getElementById('report_tbody').innerHTML = data.map(v => `<tr><td><strong>${v.username}</strong></td><td>${v.num_ventas}</td><td><strong>S/ ${v.total_vendido.toFixed(2)}</strong></td></tr>`).join('');
}

function renderUtilidades(data) {
    document.getElementById('report_thead').innerHTML = '<tr><th>Producto</th><th>Vendidos</th><th>Ganancia Total</th></tr>';
    document.getElementById('report_tbody').innerHTML = data.map(p => `<tr><td><strong>${p.nombre}</strong></td><td>${p.total_vendido}</td><td style="color:var(--success); font-weight:bold;">S/ ${p.utilidad_total.toFixed(2)}</td></tr>`).join('');
}

function filterReportTable() {
    const query = document.getElementById('report_search_input').value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const words = query.split(/\s+/).filter(w => w.length > 0);
    
    const tbody = document.getElementById('report_tbody');
    const rows = tbody.querySelectorAll('tr');
    
    rows.forEach(row => {
        const text = row.innerText.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        
        // El buscador es inteligente: todas las palabras buscadas deben estar en la fila (en cualquier orden)
        const matchesAll = words.every(word => text.includes(word));
        
        row.style.display = matchesAll ? '' : 'none';
    });
}

// --- Autocompletado de Clientes en Edición de Recibos ---

async function buscarClientesAutocompleteReportes(query) {
    let suggestionsDiv = document.getElementById('suggestions_cliente_edit');
    
    if (!suggestionsDiv) {
        suggestionsDiv = document.createElement('div');
        suggestionsDiv.id = 'suggestions_cliente_edit';
        suggestionsDiv.style = "position: absolute; width: 100%; background: #1e293b; border: 1px solid #3b82f6; z-index: 1050; max-height: 200px; overflow-y: auto; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); border-radius: 4px; margin-top: 2px;";
        const input = document.getElementById('edit_cliente_nombre');
        input.parentNode.style.position = 'relative';
        input.parentNode.appendChild(suggestionsDiv);
    }

    if (query.length < 2) {
        suggestionsDiv.style.display = 'none';
        return;
    }

    try {
        const response = await fetch(`${API_URL}/clientes-lista?search=${encodeURIComponent(query)}`);
        const clientes = await response.json();
        
        if (clientes.length === 0) {
            suggestionsDiv.style.display = 'none';
            return;
        }

        suggestionsDiv.innerHTML = "";
        clientes.slice(0, 8).forEach(c => {
            const item = document.createElement('div');
            item.style = "padding: 10px; border-bottom: 1px solid #334155; cursor: pointer; color: white; transition: background 0.2s;";
            item.innerHTML = `<strong>${c.nombre}</strong><br><small style="color: #94a3b8;">${c.documento}</small>`;
            item.onmouseover = () => item.style.background = "#334155";
            item.onmouseout = () => item.style.background = "transparent";
            item.onclick = () => {
                document.getElementById('edit_cliente_nombre').value = c.nombre;
                document.getElementById('edit_cliente_doc').value = c.documento;
                suggestionsDiv.style.display = 'none';
            };
            suggestionsDiv.appendChild(item);
        });
        suggestionsDiv.style.display = 'block';
    } catch (e) {
        console.error("Error buscando clientes:", e);
    }
}

function ocultarSugerenciasReportes() {
    const div = document.getElementById('suggestions_cliente_edit');
    if (div) div.style.display = 'none';
}

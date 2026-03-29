// compras_script.js - Lógica completa para Gestión de Compras ROLIK

let poItems = [];
let suppliersData = [];
let selectedProduct = null;
let editingOrderId = null; // Para saber si estamos editando

document.addEventListener('DOMContentLoaded', () => {
    fetchOrders();
    fetchSuppliers();
    
    document.addEventListener('click', (e) => {
        const results = document.getElementById('po_search_results');
        if (results && !results.contains(e.target) && e.target.id !== 'item_search') {
            results.style.display = 'none';
        }
    });

    const form = document.getElementById('order_form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (poItems.length === 0) return notify.warn("Añade al menos un producto");

            const orderData = {
                proveedor_nombre: document.getElementById('o_proveedor').value,
                ruc_dni: document.getElementById('o_ruc').value,
                items: poItems.map(item => ({
                    codigo: item.codigo,
                    cantidad: item.cantidad,
                    precio_compra: item.precio_compra
                })),
                po_data: {
                    fecha_compra: document.getElementById('o_fecha_compra').value,
                    comprobante_proveedor: document.getElementById('o_comprobante_proveedor').value
                }
            };

            try {
                const url = editingOrderId ? `${API_URL}/compras/ordenes/${editingOrderId}` : `${API_URL}/compras/ordenes`;
                const method = editingOrderId ? 'PUT' : 'POST';

                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(orderData)
                });

                if (response.ok) {
                    closeOrderModal();
                    fetchOrders();
                    notify.success(editingOrderId ? "Orden actualizada" : "Orden generada con éxito");
                } else {
                    const err = await response.json();
                    notify.error("Error: " + (err.detail || "No se pudo guardar la orden"));
                }
            } catch (error) { 
                notify.error("Error de conexión"); 
            }
        });
    }

    const qpForm = document.getElementById('quick_product_form');
    if (qpForm) {
        qpForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const productData = {
                codigo: document.getElementById('qp_codigo').value,
                nombre: document.getElementById('qp_nombre').value,
                categoria: document.getElementById('qp_categoria').value,
                unidad: document.getElementById('qp_unidad').value,
                precio_venta: parseFloat(document.getElementById('qp_precio_venta').value) || 0,
                precio_compra: 0,
                stock: 0
            };

            try {
                const response = await fetch(`${API_URL}/productos`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(productData)
                });

                if (response.ok) {
                    notify.success("Producto creado");
                    selectedProduct = {
                        codigo: productData.codigo,
                        nombre: productData.nombre,
                        precio_compra: 0
                    };
                    document.getElementById('item_search').value = productData.nombre;
                    closeQuickProductModal();
                } else {
                    notify.error("Error al crear producto");
                }
            } catch (error) { notify.error("Error de conexión"); }
        });
    }
});

async function fetchOrders() {
    const tbody = document.getElementById('orders_body');
    if (!tbody) return;
    try {
        const response = await fetch(`${API_URL}/compras/ordenes`);
        const orders = await response.json();
        renderOrders(orders);
    } catch (error) {
        tbody.innerHTML = '<tr><td colspan="6" class="error">Error al cargar compras</td></tr>';
    }
}

function renderOrders(orders) {
    const columns = [
        { key: 'numero_oc', formatter: val => `<code>${val}</code>` },
        { key: 'fecha_pedido', formatter: val => val ? val.split(' ')[0] : '-' },
        { key: 'proveedor', formatter: val => `<strong style="color:white;">${val}</strong>` },
        { key: 'total', formatter: val => `<span class="price">S/ ${val.toFixed(2)}</span>` },
        { 
            key: 'estado', 
            formatter: val => {
                let cls = 'badge-orange';
                if (val === 'RECIBIDO') cls = 'badge-green';
                if (val === 'ANULADO') cls = 'badge-red'; // Asumiendo que badge-red existe o se maneja por color directo
                
                // Usar las clases de estilo definidas en el HTML si prefieres
                let statusClass = 'status-pendiente';
                if (val === 'RECIBIDO') statusClass = 'status-recibida';
                if (val === 'ANULADO') statusClass = 'status-anulado';

                return `<span class="status-badge ${statusClass}">${val}</span>`;
            }
        },
        { 
            key: 'id', 
            label: 'Acciones',
            formatter: (val, row) => `
                <div style="display: flex; gap: 5px;">
                    <button class="action-btn edit-btn" onclick="viewOrderDetails(${val})" title="Ver Detalles"><i class="fas fa-eye"></i></button>
                    ${row.estado === 'PENDIENTE' ? `
                        <button class="action-btn edit-btn" onclick="editOrder(${val})" title="Editar Orden" style="background: var(--warning);"><i class="fas fa-edit"></i></button>
                        <button class="action-btn delete-btn" onclick="deleteOrder(${val}, '${row.numero_oc}')" title="Eliminar Orden" style="background: #ef4444;"><i class="fas fa-trash-alt"></i></button>
                    ` : ''}
                </div>
            `
        }
    ];
    renderTable(orders, columns, 'orders_body');
}

async function deleteOrder(id, numero) {
    if (!confirm(`¿ESTÁ SEGURO DE ELIMINAR LA ORDEN ${numero}?\n\nEsta acción es irreversible y borrará todos los productos registrados en esta orden.`)) return;
    
    try {
        const res = await fetch(`${API_URL}/compras/ordenes/${id}`, { method: 'DELETE' });
        if (res.ok) {
            notify.success("Orden eliminada correctamente");
            fetchOrders();
        } else {
            const err = await res.json();
            notify.error(err.detail || "No se pudo eliminar la orden");
        }
    } catch (e) {
        notify.error("Error de conexión al eliminar");
    }
}

async function fetchSuppliers() {
    try {
        const response = await fetch(`${API_URL}/proveedores-detalles`);
        suppliersData = await response.json();
        const select = document.getElementById('o_proveedor');
        if (select) {
            select.innerHTML = '<option value="">Selecciona Proveedor...</option>';
            suppliersData.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s.nombre;
                opt.textContent = s.nombre;
                select.appendChild(opt);
            });
        }
    } catch (error) {}
}

function updateRUC() {
    const nombreSelect = document.getElementById('o_proveedor');
    const rucInput = document.getElementById('o_ruc');
    if (!nombreSelect || !rucInput) return;

    const nombreBuscado = nombreSelect.value.trim().toUpperCase();
    
    // Buscar en el array de proveedores cargado previamente
    const supplier = suppliersData.find(s => s.nombre.trim().toUpperCase() === nombreBuscado);
    
    if (supplier) {
        rucInput.value = supplier.ruc_dni || "";
    } else {
        rucInput.value = "";
    }
}

const searchProductsForPODebounced = debounce(async (query) => {
    const resultsDiv = document.getElementById('po_search_results');
    if (query.length < 2) { resultsDiv.style.display = 'none'; return; }
    try {
        const response = await fetch(`${API_URL}/productos?search=${encodeURIComponent(query)}`);
        let products = await response.json();
        
        const q = query.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        const qWords = q.split(/\s+/).filter(w => w.length > 0);

        // Sistema de puntuación por relevancia
        products.forEach(p => {
            let score = 0;
            const n = p.nombre.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
            const c = p.codigo.toLowerCase();

            if (c === q) score += 100; // SKU exacto
            if (n === q) score += 90;  // Nombre exacto
            if (n.startsWith(q)) score += 80; // Empieza por
            
            // Puntos por cada palabra encontrada
            let wordsMatched = 0;
            qWords.forEach(word => {
                if (n.includes(word)) {
                    wordsMatched++;
                    // Bonus si la palabra está al inicio de otra palabra en el nombre
                    if (n.startsWith(word) || n.includes(" " + word)) score += 10;
                    else score += 5;
                }
            });
            
            if (wordsMatched === qWords.length && qWords.length > 1) score += 50; // Contiene todas las palabras
            
            p._score = score;
        });

        // Ordenar por puntuación (descendente) y luego alfabéticamente
        products.sort((a, b) => {
            if (b._score !== a._score) return b._score - a._score;
            return a.nombre.localeCompare(b.nombre);
        });

        resultsDiv.innerHTML = '';
        if (products.length > 0) {
            products.forEach(p => {
                const div = document.createElement('div');
                div.style = "padding:10px; border-bottom:1px solid #334155; cursor:pointer; color:white; transition: background 0.2s;";
                div.onmouseover = () => div.style.background = "#334155";
                div.onmouseout = () => div.style.background = "transparent";
                div.innerHTML = `<strong>${p.nombre}</strong><br><small style="color:#94a3b8;">SKU: ${p.codigo} | Unidad: ${p.unidad || 'und'} | Stock: ${p.stock_actual}</small>`;
                div.onclick = () => selectProductForPO(p);
                resultsDiv.appendChild(div);
            });
            resultsDiv.style.display = 'block';
        } else { resultsDiv.style.display = 'none'; }
    } catch (e) {
        console.error("Error en búsqueda:", e);
    }
}, 300);

function searchProductsForPO(query) { searchProductsForPODebounced(query); }

function selectProductForPO(p) {
    selectedProduct = p;
    document.getElementById('item_search').value = p.nombre;
    document.getElementById('item_price').value = (p.precio_compra || 0).toFixed(2);
    document.getElementById('item_qty').value = 1;
    document.getElementById('item_unit_display').textContent = p.unidad || 'und';
    document.getElementById('po_search_results').style.display = 'none';
}

function openOrderModal() {
    poItems = [];
    editingOrderId = null;
    renderPOItems();
    selectedProduct = null;
    document.getElementById('order_form').reset();
    const title = document.getElementById('order_modal_title');
    if (title) title.innerText = "Nueva Orden de Compra";
    document.getElementById('item_unit_display').textContent = 'und';
    document.getElementById('o_fecha_compra').value = new Date().toISOString().split('T')[0];
    document.getElementById('order_modal').style.display = "block";
}

function closeOrderModal() { 
    document.getElementById('order_modal').style.display = "none"; 
    editingOrderId = null;
    poItems = [];
    selectedProduct = null;
}

async function editOrder(id) {
    try {
        const response = await fetch(`${API_URL}/compras/ordenes/${id}`);
        const data = await response.json();
        const o = data.orden;
        
        if (o.estado !== 'PENDIENTE') {
            return notify.warn("Solo se pueden editar órdenes en estado PENDIENTE");
        }

        editingOrderId = id;
        const title = document.getElementById('order_modal_title');
        if (title) title.innerText = "Editar Orden: " + o.numero_oc;

        // Llenar cabecera
        document.getElementById('o_proveedor').value = o.proveedor_nombre;
        document.getElementById('o_ruc').value = o.ruc_dni || "";
        document.getElementById('o_fecha_compra').value = o.fecha_pedido.split(' ')[0];
        const compInput = document.getElementById('o_comprobante_proveedor');
        if (compInput) compInput.value = o.comprobante_proveedor || "";

        // Llenar items
        poItems = data.items.map(i => ({
            codigo: i.producto_codigo,
            nombre: i.nombre,
            unidad: i.unidad || 'und',
            cantidad: i.cantidad,
            precio_compra: i.precio_compra_unitario
        }));

        renderPOItems();
        document.getElementById('order_modal').style.display = "block";
    } catch (e) {
        notify.error("Error al cargar la orden para editar");
    }
}

function openQuickProductModal() {
    document.getElementById('quick_product_form').reset();
    document.getElementById('quick_product_modal').style.display = "block";
}

function closeQuickProductModal() { document.getElementById('quick_product_modal').style.display = "none"; }

async function addItemToOrder() {
    const qtyInput = document.getElementById('item_qty');
    const priceInput = document.getElementById('item_price');
    const qty = parseFloat(qtyInput.value);
    const price = parseFloat(priceInput.value);
    
    if (!selectedProduct) return notify.warn("Selecciona un producto");
    if (isNaN(qty) || qty <= 0) return notify.warn("Cantidad inválida");

    // Verificar si ya existe en la lista para sumar
    const existingIndex = poItems.findIndex(item => item.codigo === selectedProduct.codigo);
    if (existingIndex !== -1) {
        poItems[existingIndex].cantidad += qty;
        // Opcional: actualizar precio si el nuevo es diferente
        if (price > 0) poItems[existingIndex].precio_compra = price;
        notify.info(`Se aumentó la cantidad de ${selectedProduct.nombre}`);
    } else {
        poItems.push({
            codigo: selectedProduct.codigo,
            nombre: selectedProduct.nombre,
            unidad: selectedProduct.unidad || 'und',
            cantidad: qty,
            precio_compra: price || 0
        });
    }
    
    document.getElementById('item_search').value = "";
    qtyInput.value = "";
    priceInput.value = "";
    document.getElementById('item_unit_display').textContent = "und";
    selectedProduct = null;
    renderPOItems();
}

function updatePOItem(index, field, value) {
    const num = parseFloat(value);
    if (isNaN(num) || num < 0) {
        renderPOItems();
        return;
    }
    if (field === 'cantidad') poItems[index].cantidad = num;
    if (field === 'precio') poItems[index].precio_compra = num;
    renderPOItems();
}

function renderPOItems() {
    const tbody = document.getElementById('po_items_body');
    const totalSpan = document.getElementById('po_total');
    if (!tbody) return;
    
    tbody.innerHTML = "";
    let total = 0;
    poItems.forEach((item, index) => {
        const sub = item.cantidad * item.precio_compra;
        total += sub;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><strong>${item.nombre}</strong><br><small style="color:#94a3b8">${item.codigo}</small></td>
            <td><span class="badge badge-blue">${item.unidad}</span></td>
            <td>
                <input type="number" step="0.01" value="${item.cantidad}" 
                    onchange="updatePOItem(${index}, 'cantidad', this.value)"
                    style="width: 70px; background: #0f172a; border: 1px solid #334155; color: white; border-radius: 4px; padding: 2px; text-align: center;">
            </td>
            <td>
                <input type="number" step="0.01" value="${item.precio_compra.toFixed(2)}" 
                    onchange="updatePOItem(${index}, 'precio', this.value)"
                    style="width: 90px; background: #0f172a; border: 1px solid #334155; color: white; border-radius: 4px; padding: 2px; text-align: right;">
            </td>
            <td style="text-align: right;">S/ ${sub.toFixed(2)}</td>
            <td style="text-align: center;"><button onclick="removeItem(${index})" class="text-danger" style="background:none; border:none; cursor:pointer;"><i class="fas fa-trash"></i></button></td>
        `;
        tbody.appendChild(tr);
    });
    if (totalSpan) totalSpan.textContent = total.toFixed(2);
}

function removeItem(index) {
    poItems.splice(index, 1);
    renderPOItems();
}

async function viewOrderDetails(id) {
    try {
        const response = await fetch(`${API_URL}/compras/ordenes/${id}`);
        const data = await response.json();
        const o = data.orden;
        
        const tbody = document.getElementById('det_items_body');
        let calculatedTotal = 0;
        
        tbody.innerHTML = data.items.map(i => {
            const sub = i.cantidad * i.precio_compra_unitario;
            calculatedTotal += sub;
            return `
                <tr>
                    <td><strong>${i.nombre}</strong><br><small style="color:#94a3b8">${i.producto_codigo}</small></td>
                    <td>${i.unidad || 'und'}</td>
                    <td style="text-align:center;">${i.cantidad}</td>
                    <td style="text-align:right;">S/ ${i.precio_compra_unitario.toFixed(2)}</td>
                    <td style="text-align:right; font-weight:bold;">S/ ${sub.toFixed(2)}</td>
                </tr>
            `;
        }).join('');

        // Sobrescribir el total mostrado con el cálculo real de los items (Cantidad * Precio)
        document.getElementById('det_info').innerHTML = `
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <p style="margin:5px 0; color:#94a3b8;">N° Orden de Compra</p>
                    <h3 style="margin:0; color:white;">${o.numero_oc}</h3>
                    <p style="margin:15px 0 5px 0; color:#94a3b8;">Proveedor</p>
                    <h3 style="margin:0; color:white;">${o.proveedor_nombre}</h3>
                </div>
                <div style="text-align: right;">
                    <p style="margin:5px 0; color:#94a3b8;">N° Guía / Factura</p>
                    <h3 style="margin:0; color:var(--warning);">${o.comprobante_proveedor || "---"}</h3>
                    
                    <div style="margin-top: 20px; border-top: 1px solid #334155; padding-top: 10px;">
                        <p style="margin:2px 0; font-size:14px; color:#94a3b8;">Subtotal: S/ ${(calculatedTotal / 1.18).toFixed(2)}</p>
                        <p style="margin:2px 0; font-size:14px; color:#94a3b8;">IGV (18%): S/ ${(calculatedTotal - (calculatedTotal / 1.18)).toFixed(2)}</p>
                        <p style="margin:5px 0; font-size:20px; font-weight:bold; color:var(--success);">Total a Pagar: S/ ${calculatedTotal.toFixed(2)}</p>
                    </div>
                </div>
            </div>
        `;

        const actions = document.getElementById('det_actions');
        actions.innerHTML = '<button class="btn btn-secondary" onclick="closeDetailModal()">Cerrar</button>';
        if (o.estado === 'PENDIENTE') {
            actions.innerHTML += `
                <button class="btn btn-danger" onclick="changeStatus(${o.id}, 'ANULADO')" style="margin-left:10px; background: #ef4444;"><i class="fas fa-ban"></i> ANULAR ORDEN</button>
                <button class="btn btn-primary" onclick="changeStatus(${o.id}, 'RECIBIDA')" style="margin-left:10px;"><i class="fas fa-check"></i> RECIBIR MERCADERÍA</button>
            `;
        } else if (o.estado === 'RECIBIDO') {
            actions.innerHTML += `
                <button class="btn btn-warning" onclick="changeStatus(${o.id}, 'REVERTIR')" style="margin-left:10px; background: var(--warning); color: #000; font-weight: bold;"><i class="fas fa-undo"></i> REVERTIR RECEPCIÓN</button>
            `;
        }

        document.getElementById('detail_modal').style.display = "block";
    } catch (e) { notify.error("Error al cargar detalles"); }
}

function closeDetailModal() { 
    document.getElementById('detail_modal').style.display = "none"; 
}

async function changeStatus(id, estado) {
    if (!confirm(`¿Confirmar recepción de mercadería? Esto incrementará el stock.`)) return;
    try {
        const res = await fetch(`${API_URL}/compras/ordenes/${id}/estado?estado=${estado}`, { method: 'PATCH' });
        if (res.ok) {
            notify.success("Mercadería recibida y stock actualizado");
            closeDetailModal();
            fetchOrders();
        } else { notify.error("Error al actualizar estado"); }
    } catch (e) { notify.error("Error de conexión"); }
}

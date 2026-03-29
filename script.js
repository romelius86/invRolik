// 1. ESTA LÍNEA ES LA MÁS IMPORTANTE (Agrégala al puro inicio)
const API_URL = 'https://invrolik-2.onrender.com'; 

// --- ABAJO PEGAS TODO TU CÓDIGO ---
let allInventory = [];

document.addEventListener('DOMContentLoaded', () => {
    fetchProducts();
    // ... resto del código que me pasaste
// script.js - Lógica para Inventario ROLIK con Integración de Proveedores

let allInventory = [];

document.addEventListener('DOMContentLoaded', () => {
    fetchProducts();
    fetchSuppliersForSelect(); // Cargar proveedores para el modal
    
    const searchInput = document.getElementById('inventory_search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(() => filterInventory(), 300));
    }
});

async function fetchProducts() {
    const tbody = document.getElementById('inventory_body');
    if (!tbody) return;
    
    try {
        const response = await fetch(`${API_URL}/productos`);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Error del servidor: ${response.status}`);
        }
        allInventory = await response.json();
        renderInventory(allInventory);
    } catch (error) {
        console.error("Error en fetchProducts:", error);
        tbody.innerHTML = `<tr><td colspan="13" style="color:red; text-align:center; padding:20px;">
            <strong>Error:</strong> ${error.message}<br>
            <small>Asegúrese de que el servidor esté corriendo y la base de datos actualizada.</small>
        </td></tr>`;
    }
}

function renderInventory(products) {
    const columns = [
        { key: 'codigo', formatter: val => `<code>${val}</code>` },
        { 
            key: 'nombre', 
            formatter: (val, p) => `<strong>${val}</strong>` 
        },
        { 
            key: 'descripcion', 
            formatter: val => `<small style="display:block; max-width:150px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${val || ''}">${val || '-'}</small>` 
        },
        { key: 'categoria', formatter: val => `<span class="badge badge-blue">${val || 'Sin Cat.'}</span>` },
        { key: 'marca', formatter: val => `<strong>${val || '-'}</strong>` },
        { key: 'unidad', formatter: val => val || 'unidad' },
        { key: 'proveedor_nombre', formatter: val => val || '-' },
        { 
            key: 'stock_actual', 
            style: 'text-align:center; font-weight:bold;', 
            formatter: (val, p) => {
                const unidadLabel = (p.unidad || 'unidad').toLowerCase();
                let factor = 1.0;
                if (unidadLabel.includes('millar')) factor = 1000.0;
                else if (unidadLabel.includes('ciento')) factor = 100.0;
                else if (unidadLabel.includes('docena')) factor = 12.0;

                const stockReal = parseFloat(val || 0);
                const stockEnUnidades = stockReal * factor;
                const stockMinimo = parseFloat(p.stock_minimo || 5);
                const isLow = stockReal <= stockMinimo;
                
                return `<span class="stock-badge ${isLow ? 'stock-low' : 'stock-ok'}">${parseFloat(stockEnUnidades.toFixed(2))}</span>`;
            }
        },
        { key: 'stock_minimo', style: 'text-align:center; color:var(--text-muted)', formatter: val => val || 5 },
        { key: 'precio_compra', formatter: val => `S/ ${parseFloat(val || 0).toFixed(2)}` },
        { key: 'precio_venta', formatter: val => `S/ ${parseFloat(val || 0).toFixed(2)}` },
        { 
            key: 'id', 
            label: 'Valor Total',
            formatter: (_, p) => {
                const stock = parseFloat(p.stock_actual || 0);
                const precio = parseFloat(p.precio_venta || 0);
                const total = stock * precio;
                return `<strong>S/ ${total.toFixed(2)}</strong>`;
            }
        },
        {
            key: 'codigo',
            label: 'Acciones',
            formatter: (val, p) => {
                const escapedName = p.nombre.replace(/'/g, "\\'").replace(/"/g, "&quot;");
                return `
                <div style="display:flex; gap:5px;">
                    <button class="btn btn-secondary" title="Historial / Kardex" style="padding:5px 10px; background:#10b981;" onclick="openKardexModal('${val}', '${escapedName}')"><i class="fas fa-history"></i></button>
                    <button class="btn btn-secondary" title="Presentaciones y Precios" style="padding:5px 10px; background:#3b82f6;" onclick="openUnitsModal('${val}', '${escapedName}')"><i class="fas fa-layer-group"></i></button>
                    <button class="btn btn-secondary" style="padding:5px 10px;" onclick="openProductModal('${val}')" title="Editar"><i class="fas fa-edit"></i></button>
                    <button class="btn btn-secondary text-danger" style="padding:5px 10px;" onclick="deleteProduct('${val}')" title="Eliminar"><i class="fas fa-trash-alt"></i></button>
                </div>
                `;
            }
        }
    ];

    renderTable(products, columns, 'inventory_body');
}

function filterInventory() {
    const query = document.getElementById('inventory_search').value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    if (!query) { renderInventory(allInventory); return; }
    const filtered = allInventory.filter(p => {
        const text = (p.nombre + " " + p.codigo + " " + p.categoria + " " + (p.marca || "")).toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        return text.includes(query);
    });
    renderInventory(filtered);
}

// --- MODAL DE UNIDADES Y PRECIOS ---
let currentProductUnitsCode = null;

async function openUnitsModal(codigo, nombre) {
    currentProductUnitsCode = codigo;
    const modal = document.getElementById('units_modal');
    if (!modal) return notify.error("Modal de unidades no encontrado");
    
    document.getElementById('units_modal_title').innerText = `Presentaciones: ${nombre}`;
    document.getElementById('unit_form').reset();
    
    // Escuchador para autocompletar factor según nombre
    const nameInput = document.getElementById('u_nombre');
    const factorInput = document.getElementById('u_factor');
    if (nameInput) {
        nameInput.oninput = () => {
            const val = nameInput.value.toLowerCase().trim();
            if (val === 'millar') factorInput.value = 1000;
            else if (val === 'ciento') factorInput.value = 100;
            else if (val === 'docena') factorInput.value = 12;
        };
    }

    loadProductUnits();
    modal.style.display = 'block';
}

async function loadProductUnits() {
    try {
        const res = await fetch(`${API_URL}/productos/${currentProductUnitsCode}/unidades`);
        const units = await res.json();
        const tbody = document.getElementById('units_tbody');
        tbody.innerHTML = units.map(u => `
            <tr>
                <td><strong>${u.nombre_unidad}</strong></td>
                <td>${u.factor_conversion} unidades</td>
                <td><strong>S/ ${u.precio_venta.toFixed(2)}</strong></td>
                <td>
                    <button onclick="deleteUnit(${u.id})" class="btn btn-secondary" style="padding:2px 8px; color:#ef4444;"><i class="fas fa-times"></i></button>
                </td>
            </tr>
        `).join('') || '<tr><td colspan="4" style="text-align:center">No hay presentaciones adicionales.</td></tr>';
    } catch (e) { console.error(e); }
}

async function saveNewUnit() {
    const data = {
        nombre_unidad: document.getElementById('u_nombre').value,
        factor_conversion: parseFloat(document.getElementById('u_factor').value),
        precio_venta: parseFloat(document.getElementById('u_precio').value)
    };

    if (!data.nombre_unidad || !data.factor_conversion) return notify.warn("Nombre y Factor son obligatorios");

    try {
        const res = await fetch(`${API_URL}/productos/${currentProductUnitsCode}/unidades`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            document.getElementById('unit_form').reset();
            loadProductUnits();
            notify.success("Presentación añadida");
        } else {
            const err = await res.json();
            notify.error("Error: " + (err.detail || "No se pudo guardar"));
        }
    } catch (e) { notify.error("Error de conexión"); }
}

async function deleteUnit(id) {
    if (!confirm("¿Eliminar esta presentación?")) return;
    try {
        await fetch(`${API_URL}/productos/unidades/${id}`, { method: 'DELETE' });
        loadProductUnits();
        notify.success("Presentación eliminada");
    } catch (e) { notify.error("Error al eliminar"); }
}

function closeUnitsModal() { document.getElementById('units_modal').style.display = 'none'; }

// --- RESTO DE FUNCIONES (Producto, Kardex, Proveedores) ---

async function fetchSuppliersForSelect() {
    try {
        const response = await fetch(`${API_URL}/proveedores-lista-completa`);
        const suppliers = await response.json();
        const select = document.getElementById('p_proveedor_id');
        if (!select) return;
        select.innerHTML = '<option value="">-- Sin Proveedor --</option>';
        suppliers.forEach(s => {
            const opt = document.createElement('option'); opt.value = s.id; opt.textContent = s.nombre;
            select.appendChild(opt);
        });
    } catch (error) {}
}

function openProductModal(codigo = null) {
    const modal = document.getElementById('product_modal');
    const form = document.getElementById('product_form');
    if (form) form.reset();
    if (codigo) {
        document.getElementById('modal_title').innerText = "Editar Producto";
        loadProductToForm(codigo);
    } else {
        document.getElementById('modal_title').innerText = "Añadir Nuevo Producto";
        document.getElementById('p_codigo').readOnly = false;
        fetch(`${API_URL}/productos/proximo-codigo`).then(res => res.json()).then(data => {
            if (data.codigo) document.getElementById('p_codigo').value = data.codigo;
        });
    }
    modal.style.display = "block";
}

function closeProductModal() {
    const modal = document.getElementById('product_modal');
    if (modal) modal.style.display = "none";
}

async function loadProductToForm(codigo) {
    try {
        const response = await fetch(`${API_URL}/producto/${codigo}`);
        const p = await response.json();
        document.getElementById('p_codigo').value = p.codigo;
        document.getElementById('p_nombre').value = p.nombre;
        document.getElementById('p_categoria').value = p.categoria || "";
        document.getElementById('p_marca').value = p.marca || "";
        document.getElementById('p_proveedor_id').value = p.proveedor_id || "";
        document.getElementById('p_unidad').value = p.unidad || "unidad";
        document.getElementById('p_stock').value = p.stock_actual;
        document.getElementById('p_stock_min').value = p.stock_minimo;
        document.getElementById('p_precio_compra').value = p.precio_compra || 0;
        document.getElementById('p_precio').value = p.precio_venta;
        document.getElementById('p_descripcion').value = p.descripcion || "";
        document.getElementById('p_codigo').readOnly = true;
    } catch (error) { notify.error("Error al cargar producto"); }
}

async function deleteProduct(codigo) {
    if (!confirm(`¿Mover el producto ${codigo} a la papelera?`)) return;
    try {
        const response = await fetch(`${API_URL}/productos/${codigo}`, { method: 'DELETE' });
        if (response.ok) { fetchProducts(); notify.success("Producto movido a papelera"); }
    } catch (error) { notify.error("Error de conexión"); }
}

async function openKardexModal(codigo, nombre) {
    const modal = document.getElementById('kardex_modal');
    document.getElementById('kardex_title').innerText = `Kardex: ${nombre}`;
    try {
        const res = await fetch(`${API_URL}/productos/${codigo}/kardex`);
        const movements = await res.json();
        document.getElementById('kardex_tbody').innerHTML = movements.map(m => `
            <tr>
                <td><small>${m.fecha}</small></td>
                <td><span class="badge ${m.tipo.includes('ENTRADA') ? 'badge-blue' : 'badge-orange'}">${m.tipo}</span></td>
                <td><strong>${m.documento}</strong></td>
                <td>${m.cantidad}</td>
                <td>S/ ${m.precio.toFixed(2)}</td>
                <td><small>${m.detalle}</small></td>
            </tr>
        `).join('') || '<tr><td colspan="6" style="text-align:center">Sin movimientos</td></tr>';
        modal.style.display = 'block';
    } catch (e) { notify.error("Error al cargar Kardex"); }
}

function closeKardexModal() {
    const modal = document.getElementById('kardex_modal');
    if (modal) modal.style.display = 'none';
}

// Listener para el formulario de productos
const pForm = document.getElementById('product_form');
if (pForm) {
    pForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const isEdit = document.getElementById('p_codigo').readOnly;
        const data = {
            codigo: document.getElementById('p_codigo').value,
            nombre: document.getElementById('p_nombre').value,
            categoria: document.getElementById('p_categoria').value,
            marca: document.getElementById('p_marca').value,
            proveedor_id: document.getElementById('p_proveedor_id').value ? parseInt(document.getElementById('p_proveedor_id').value) : null,
            unidad: document.getElementById('p_unidad').value,
            stock_actual: parseFloat(document.getElementById('p_stock').value),
            stock_minimo: parseFloat(document.getElementById('p_stock_min').value),
            precio_compra: parseFloat(document.getElementById('p_precio_compra').value || 0),
            precio_venta: parseFloat(document.getElementById('p_precio').value),
            descripcion: document.getElementById('p_descripcion').value
        };
        try {
            const res = await fetch(`${API_URL}/productos` + (isEdit ? `/${data.codigo}` : ''), {
                method: isEdit ? 'PUT' : 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            if (res.ok) { document.getElementById('product_modal').style.display = 'none'; fetchProducts(); notify.success("Guardado"); }
        } catch (e) { notify.error("Error al guardar"); }
    });
}

// --- PAPELERA Y EXPORTACIÓN ---

function openTrashModal() {
    const modal = document.getElementById('trash_modal');
    modal.style.display = "block";
    fetchDeletedProducts();
}

function closeTrashModal() {
    document.getElementById('trash_modal').style.display = "none";
}

async function fetchDeletedProducts() {
    const tbody = document.getElementById('trash_body');
    tbody.innerHTML = '<tr><td colspan="4" class="loading">Cargando...</td></tr>';
    try {
        const res = await fetch(`${API_URL}/productos-eliminados`);
        const products = await res.json();
        tbody.innerHTML = products.map(p => `
            <tr>
                <td><code>${p.codigo}</code></td>
                <td><strong>${p.nombre}</strong></td>
                <td><small>${p.deleted_at}</small></td>
                <td>
                    <button onclick="restoreProduct('${p.codigo}')" class="btn btn-primary" style="padding:5px 10px;" title="Restaurar"><i class="fas fa-trash-restore"></i> RESTAURAR</button>
                </td>
            </tr>
        `).join('') || '<tr><td colspan="4" style="text-align:center">La papelera está vacía.</td></tr>';
    } catch (e) { notify.error("Error al cargar la papelera"); }
}

async function restoreProduct(codigo) {
    try {
        const res = await fetch(`${API_URL}/productos/restaurar/${codigo}`, { method: 'POST' });
        if (res.ok) {
            notify.success("Producto restaurado");
            fetchDeletedProducts();
            fetchProducts();
        }
    } catch (e) { notify.error("Error al restaurar"); }
}

function exportToExcel() {
    notify.info("Generando archivo de exportación...");
    window.location.href = `${API_URL}/productos/exportar`;
}


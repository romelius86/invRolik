// proveedores_script.js - Lógica para Gestión de Proveedores en ROLIK ERP

let allSuppliers = [];

document.addEventListener('DOMContentLoaded', () => {
    fetchSuppliers();
    setupFormListener();
    
    const searchInput = document.getElementById('supplier_search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(() => filterSuppliers(), 300));
    }
});

async function fetchSuppliers() {
    const tbody = document.getElementById('suppliers_body');
    if (!tbody) return;
    
    try {
        const response = await fetch(`${API_URL}/proveedores-detalles`);
        allSuppliers = await response.json();
        renderSuppliers(allSuppliers);
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="6" class="error">Error de conexión con la API.</td></tr>`;
        notify.error("No se pudieron cargar los proveedores");
    }
}

function renderSuppliers(suppliers) {
    const columns = [
        { key: 'nombre', formatter: val => `<strong>${val}</strong>` },
        { key: 'ruc_dni', formatter: val => `<code>${val || '-'}</code>` },
        { key: 'telefono', formatter: val => val || '-' },
        { key: 'email', formatter: val => val || '-' },
        { key: 'direccion', formatter: val => `<small class="text-muted">${val || '-'}</small>` },
        { 
            key: 'id', 
            label: 'Acciones',
            formatter: (val, s) => `
                <div style="display: flex; gap: 5px;">
                    <button class="action-btn edit-btn" onclick="openSupplierModal(${val})" title="Editar"><i class="fas fa-edit"></i></button>
                    <button class="action-btn delete-btn" onclick="deleteSupplier(${val}, '${s.nombre.replace(/'/g, "\\'")}')" title="Eliminar"><i class="fas fa-trash-alt"></i></button>
                </div>
            `
        }
    ];

    renderTable(suppliers, columns, 'suppliers_body');
}

function filterSuppliers() {
    const query = document.getElementById('supplier_search').value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    if (!query) {
        renderSuppliers(allSuppliers);
        return;
    }
    const filtered = allSuppliers.filter(s => {
        const nombre = s.nombre.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        const ruc = (s.ruc_dni || "").toLowerCase();
        const email = (s.email || "").toLowerCase();
        return nombre.includes(query) || ruc.includes(query) || email.includes(query);
    });
    renderSuppliers(filtered);
}

function openSupplierModal(id = null) {
    const modal = document.getElementById('supplier_modal');
    const form = document.getElementById('supplier_form');
    const title = document.getElementById('modal_title');
    
    if (form) form.reset();
    document.getElementById('s_id').value = "";
    
    if (id) {
        if (title) title.innerText = "Editar Proveedor";
        loadSupplierData(id);
    } else {
        if (title) title.innerText = "Nuevo Proveedor";
    }
    
    if (modal) modal.style.display = "block";
}

function closeSupplierModal() {
    const modal = document.getElementById('supplier_modal');
    if (modal) modal.style.display = "none";
}

async function loadSupplierData(id) {
    const s = allSuppliers.find(sup => sup.id === id);
    if (s) {
        document.getElementById('s_id').value = s.id;
        document.getElementById('s_nombre').value = s.nombre;
        document.getElementById('s_ruc_dni').value = s.ruc_dni || "";
        document.getElementById('s_telefono').value = s.telefono || "";
        document.getElementById('s_email').value = s.email || "";
        
        // Seleccionar tipo de documento según longitud
        const doc = s.ruc_dni || "";
        const select = document.getElementById('s_tipo_doc');
        if (doc.length === 8) select.value = "DNI";
        else if (doc.length === 11) select.value = "RUC";
        else select.value = "OTROS";

        // Parsear dirección para extraer distrito si existe formato [Distrito] Dirección
        let dir = s.direccion || "";
        if (dir.startsWith("[") && dir.includes("]")) {
            const parts = dir.split("]");
            document.getElementById('s_distrito').value = parts[0].substring(1).trim();
            document.getElementById('s_direccion').value = parts[1].trim();
        } else {
            document.getElementById('s_distrito').value = "";
            document.getElementById('s_direccion').value = dir;
        }
    }
}

function setupFormListener() {
    const form = document.getElementById('supplier_form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const id = document.getElementById('s_id').value;
            const distrito = document.getElementById('s_distrito').value.trim();
            const direccionEx = document.getElementById('s_direccion').value.trim();
            
            // Combinar distrito y dirección para la DB
            const direccionCompleta = distrito ? `[${distrito}] ${direccionEx}` : direccionEx;

            const supplierData = {
                nombre: document.getElementById('s_nombre').value,
                ruc_dni: document.getElementById('s_ruc_dni').value.trim(),
                telefono: document.getElementById('s_telefono').value,
                email: document.getElementById('s_email').value,
                direccion: direccionCompleta
            };

            if (!supplierData.nombre) {
                notify.warn("El nombre es obligatorio");
                return;
            }

            // Validación por Tipo de Documento
            const tipoDoc = document.getElementById('s_tipo_doc').value;
            const docLen = supplierData.ruc_dni.length;

            if (tipoDoc === "DNI" && docLen !== 8) {
                notify.error(`El DNI debe tener exactamente 8 dígitos. Ingresado: ${docLen}`);
                return;
            }
            if (tipoDoc === "RUC" && docLen !== 11) {
                notify.error(`El RUC debe tener exactamente 11 dígitos. Ingresado: ${docLen}`);
                return;
            }
            if (isNaN(supplierData.ruc_dni) && (tipoDoc === "DNI" || tipoDoc === "RUC")) {
                notify.error("El número de documento debe contener solo dígitos");
                return;
            }

            try {
                const url = id ? `${API_URL}/proveedores/${id}` : `${API_URL}/proveedores`;
                const method = id ? 'PUT' : 'POST';

                const response = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(supplierData)
                });

                if (response.ok) {
                    closeSupplierModal();
                    fetchSuppliers();
                    notify.success(id ? "Proveedor actualizado" : "Proveedor registrado");
                } else {
                    const err = await response.json();
                    notify.error("Error: " + (err.detail || "No se pudo guardar"));
                }
            } catch (error) {
                notify.error("Error de conexión");
            }
        });
    }
}

async function deleteSupplier(id, nombre) {
    if (!confirm(`¿Estás seguro de enviar al proveedor "${nombre}" a la papelera?`)) return;

    try {
        const response = await fetch(`${API_URL}/proveedores/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            fetchSuppliers();
            notify.success("Proveedor movido a la papelera");
        } else {
            const err = await response.json();
            notify.error("Error: " + (err.detail || "No se pudo eliminar"));
        }
    } catch (error) {
        notify.error("Error de conexión");
    }
}

async function openTrashModal() {
    const modal = document.getElementById('trash_modal');
    try {
        const res = await fetch(`${API_URL}/proveedores-eliminados`);
        const suppliers = await res.json();
        const tbody = document.getElementById('trash_tbody');
        tbody.innerHTML = "";
        
        if (suppliers.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; padding: 20px;">La papelera está vacía</td></tr>';
        } else {
            suppliers.forEach(s => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${s.nombre}</strong></td>
                    <td><code>${s.ruc_dni || 'N/A'}</code></td>
                    <td><small>${s.deleted_at}</small></td>
                    <td>
                        <button onclick="restoreSupplier(${s.id})" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px; background: #22c55e;">
                            <i class="fas fa-undo"></i> RESTAURAR
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }
        modal.style.display = 'block';
    } catch (e) { notify.error("Error al cargar la papelera"); }
}

async function restoreSupplier(id) {
    try {
        const res = await fetch(`${API_URL}/proveedores/restaurar/${id}`, { method: 'POST' });
        if (res.ok) {
            notify.success("Proveedor restaurado con éxito");
            document.getElementById('trash_modal').style.display = 'none';
            fetchSuppliers();
        } else { notify.error("No se pudo restaurar el proveedor"); }
    } catch (e) { notify.error("Error de conexión"); }
}

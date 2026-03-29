// clientes_script.js - Lógica para Clientes con Papelera de Reciclaje

document.addEventListener('DOMContentLoaded', () => {
    fetchClientes();
    
    const form = document.getElementById('cliente_form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            guardarCliente();
        });
    }

    const searchInput = document.getElementById('cliente_search');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(() => fetchClientes(), 300));
    }

    window.onclick = function(event) {
        const clienteModal = document.getElementById('cliente_modal');
        const trashModal = document.getElementById('trash_modal');
        if (event.target == clienteModal) closeClienteModal();
        if (event.target == trashModal) closeTrashModal();
    }
});

let currentClienteId = null;

async function fetchClientes() {
    const search = document.getElementById('cliente_search').value;
    const tbody = document.getElementById('clientes_body');
    
    try {
        const response = await fetch(`${API_URL}/clientes-lista?search=${encodeURIComponent(search)}`);
        const clientes = await response.json();
        renderClientes(clientes);
    } catch (error) {
        if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="error">Error al conectar con el servidor</td></tr>`;
        notify.error("Error al cargar clientes");
    }
}

function renderClientes(clientes) {
    const columns = [
        { key: 'documento', formatter: val => `<code>${val}</code>` },
        { key: 'nombre', formatter: val => `<strong>${val}</strong>` },
        { key: 'telefono', formatter: val => val || '-' },
        { key: 'email', formatter: val => val || '-' },
        { key: 'direccion', formatter: val => `<small class="text-muted">${val || '-'}</small>` },
        { 
            key: 'documento', 
            label: 'Acciones',
            formatter: (val, c) => `
                <div style="display: flex; gap: 5px;">
                    ${hasPermission('user.edit') ? `<button class="action-btn edit-btn" onclick="openClienteModal('${val}')" title="Editar"><i class="fas fa-user-edit"></i></button>` : ''}
                    ${hasPermission('user.delete') ? `<button class="action-btn delete-btn" onclick="confirmarEliminar('${val}', '${c.nombre}')" title="Mover a Papelera"><i class="fas fa-trash"></i></button>` : ''}
                </div>
            `
        }
    ];

    renderTable(clientes, columns, 'clientes_body');
}

function openClienteModal(documento = null) {
    const modal = document.getElementById('cliente_modal');
    const form = document.getElementById('cliente_form');
    const title = document.getElementById('modal_title');
    
    if (form) form.reset();
    currentClienteId = null;
    document.getElementById('c_documento').disabled = false;
    
    if (documento) {
        title.innerText = "Editar Cliente";
        loadClienteData(documento);
    } else {
        title.innerText = "Nuevo Cliente";
    }
    
    modal.style.display = "block";
}

function closeClienteModal() {
    const modal = document.getElementById('cliente_modal');
    if (modal) modal.style.display = "none";
}

async function loadClienteData(documento) {
    try {
        const response = await fetch(`${API_URL}/clientes/${documento}`);
        const c = await response.json();
        
        currentClienteId = c.id;
        document.getElementById('c_documento').value = c.documento;
        document.getElementById('c_nombre').value = c.nombre;
        document.getElementById('c_direccion').value = c.direccion || "";
        document.getElementById('c_telefono').value = c.telefono || "";
        document.getElementById('c_email').value = c.email || "";

        // Seleccionar tipo de documento según longitud
        const doc = c.documento || "";
        const select = document.getElementById('c_tipo_doc');
        if (doc.length === 8) select.value = "DNI";
        else if (doc.length === 11) select.value = "RUC";
        else select.value = "OTROS";

    } catch (error) {
        notify.error("Error al cargar datos del cliente");
    }
}

async function guardarCliente() {
    const clienteData = {
        id: currentClienteId,
        documento: document.getElementById('c_documento').value.trim(),
        nombre: document.getElementById('c_nombre').value,
        direccion: document.getElementById('c_direccion').value,
        telefono: document.getElementById('c_telefono').value,
        email: document.getElementById('c_email').value
    };

    if (!clienteData.documento || !clienteData.nombre) {
        notify.warn("Documento y Nombre son obligatorios");
        return;
    }

    // Validación por Tipo de Documento
    const tipoDoc = document.getElementById('c_tipo_doc').value;
    const docLen = clienteData.documento.length;

    if (tipoDoc === "DNI" && docLen !== 8) {
        notify.error(`El DNI debe tener exactamente 8 dígitos. Ingresado: ${docLen}`);
        return;
    }
    if (tipoDoc === "RUC" && docLen !== 11) {
        notify.error(`El RUC debe tener exactamente 11 dígitos. Ingresado: ${docLen}`);
        return;
    }
    if (isNaN(clienteData.documento) && (tipoDoc === "DNI" || tipoDoc === "RUC")) {
        notify.error("El número de documento debe contener solo dígitos");
        return;
    }

    try {
        const response = await fetch(`${API_URL}/clientes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(clienteData)
        });

        if (response.ok) {
            closeClienteModal();
            fetchClientes();
            notify.success(currentClienteId ? "Cliente actualizado" : "Cliente registrado");
        } else {
            const err = await response.json();
            notify.error("Error: " + (err.detail || "No se pudo guardar"));
        }
    } catch (error) {
        notify.error("Error de conexión");
    }
}

function confirmarEliminar(documento, nombre) {
    if (confirm(`¿Estás seguro de mover a ${nombre} a la papelera?`)) {
        eliminarCliente(documento);
    }
}

async function eliminarCliente(documento) {
    try {
        const response = await fetch(`${API_URL}/clientes/${documento}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            fetchClientes();
            notify.success("Cliente movido a la papelera");
        } else {
            notify.error("Error al eliminar cliente");
        }
    } catch (error) {
        notify.error("Error de conexión");
    }
}

function openTrashModal() {
    const modal = document.getElementById('trash_modal');
    modal.style.display = "block";
    fetchClientesEliminados();
}

function closeTrashModal() {
    const modal = document.getElementById('trash_modal');
    modal.style.display = "none";
}

async function fetchClientesEliminados() {
    const tbody = document.getElementById('trash_body');
    tbody.innerHTML = `<tr><td colspan="4" class="loading">Buscando en papelera...</td></tr>`;
    
    try {
        const response = await fetch(`${API_URL}/clientes-eliminados`);
        const clientes = await response.json();
        
        tbody.innerHTML = "";
        if (clientes.length === 0) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding: 20px;">La papelera está vacía.</td></tr>`;
            return;
        }

        clientes.forEach(c => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><code>${c.documento}</code></td>
                <td>${c.nombre}</td>
                <td><small>${c.deleted_at}</small></td>
                <td>
                    <button class="btn btn-primary" style="padding: 5px 10px; font-size: 12px; background: #22c55e;" onclick="restaurarCliente('${c.documento}')">
                        <i class="fas fa-undo"></i> RESTAURAR
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });
    } catch (error) {
        tbody.innerHTML = `<tr><td colspan="4" class="error">Error al cargar papelera</td></tr>`;
    }
}

async function restaurarCliente(documento) {
    try {
        const response = await fetch(`${API_URL}/clientes/restaurar/${documento}`, {
            method: 'POST'
        });

        if (response.ok) {
            fetchClientesEliminados();
            fetchClientes();
            notify.success("Cliente restaurado correctamente");
        } else {
            notify.error("No se pudo restaurar el cliente");
        }
    } catch (error) {
        notify.error("Error de conexión");
    }
}

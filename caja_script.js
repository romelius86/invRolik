// caja_script.js - Lógica Avanzada para Gestión de Caja

let currentSession = null;

document.addEventListener('DOMContentLoaded', () => {
    updateSessionStatus();
    setupMovementForm();
});

async function updateSessionStatus() {
    try {
        const response = await fetch(`${API_URL}/caja/sesion-activa`);
        const data = await response.json();
        const statusBar = document.getElementById('cash_status_bar');
        const closeBtn = document.getElementById('btn_close_caja');

        if (data.active) {
            currentSession = data.session;
            const startDate = new Date(currentSession.open_date).toLocaleString();
            statusBar.innerHTML = `<span class="badge badge-green" style="font-size: 14px;"><i class="fas fa-check-circle"></i> CAJA ABIERTA</span> <span style="margin-left: 10px; color: var(--text-muted);">Inicio: ${startDate}</span>`;
            if (closeBtn) {
                closeBtn.innerHTML = '<i class="fas fa-file-invoice-dollar"></i> CERRAR CAJA (CORTE Z)';
                closeBtn.onclick = handleCloseCaja;
                closeBtn.className = "btn btn-danger";
            }
        } else {
            currentSession = null;
            statusBar.innerHTML = `<span class="badge badge-red" style="font-size: 14px;"><i class="fas fa-times-circle"></i> CAJA CERRADA</span>`;
            if (closeBtn) {
                closeBtn.innerHTML = '<i class="fas fa-cash-register"></i> ABRIR NUEVA CAJA';
                closeBtn.onclick = openOpenModal;
                closeBtn.className = "btn btn-primary";
            }
        }
    } catch (error) { 
        notify.error("Error al verificar estado de caja");
    }
}

async function fetchResumen() {
    if (!currentSession) return notify.warn("No hay una sesión de caja activa.");
    
    try {
        const response = await fetch(`${API_URL}/caja/resumen`);
        const data = await response.json();
        
        document.getElementById('empty_state').style.display = 'none';
        document.getElementById('history_content').style.display = 'none';
        document.getElementById('summary_content').style.display = 'block';

        document.getElementById('txt_inicial').textContent = `S/ ${data.inicial.toFixed(2)}`;
        
        let vEfectivo = 0, vYape = 0, vTransf = 0;
        const totalVentas = Object.values(data.ventas).reduce((a, b) => a + b, 0);
        document.getElementById('txt_ventas').textContent = `S/ ${totalVentas.toFixed(2)}`;

        const listVentas = document.getElementById('list_ventas');
        listVentas.innerHTML = "";
        
        for (const [metodo, monto] of Object.entries(data.ventas)) {
            const metUpper = metodo.toUpperCase();
            if (metUpper.includes('EFECTIVO')) vEfectivo += monto;
            else if (metUpper.includes('YAPE') || metUpper.includes('PLIN')) vYape += monto;
            else if (metUpper.includes('TARJETA') || metUpper.includes('TRANSF')) vTransf += monto;
            else {
                const div = document.createElement('div');
                div.className = "summary-item";
                div.style = "display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid var(--border-color);";
                div.innerHTML = `<span>${metodo}</span> <strong>S/ ${monto.toFixed(2)}</strong>`;
                listVentas.appendChild(div);
            }
        }

        document.getElementById('txt_v_efectivo').textContent = `S/ ${vEfectivo.toFixed(2)}`;
        document.getElementById('txt_v_yape').textContent = `S/ ${vYape.toFixed(2)}`;
        document.getElementById('txt_v_transf').textContent = `S/ ${vTransf.toFixed(2)}`;
        
        const movNeto = (data.movimientos['INGRESO'] || 0) - (data.movimientos['RETIRO'] || 0);
        const efectivoCaja = data.inicial + vEfectivo + movNeto;
        document.getElementById('txt_efectivo_caja').textContent = `S/ ${efectivoCaja.toFixed(2)}`;

        const listMov = document.getElementById('list_movimientos');
        listMov.innerHTML = "";
        for (const [tipo, monto] of Object.entries(data.movimientos)) {
            const div = document.createElement('div');
            div.className = "summary-item";
            div.style = "display: flex; justify-content: space-between; padding: 10px; border-bottom: 1px solid var(--border-color);";
            div.innerHTML = `<span style="color: ${tipo === 'INGRESO' ? 'var(--success)' : 'var(--danger)'}; font-weight: 600;">${tipo}</span> <strong>S/ ${monto.toFixed(2)}</strong>`;
            listMov.appendChild(div);
        }
        
        notify.info("Resumen de caja actualizado");
    } catch (error) { 
        notify.error("Error al cargar el resumen");
    }
}

async function handleCloseCaja() {
    if (!confirm("¿Estás seguro de que deseas cerrar la caja? Se generará el respaldo automático.")) return;

    try {
        const user = getLoggedInUser();
        const response = await fetch(`${API_URL}/caja/cerrar`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: user.id })
        });

        if (response.ok) {
            notify.success("Caja cerrada correctamente");
            setTimeout(() => location.reload(), 1500);
        } else {
            const err = await response.json();
            notify.error("Error: " + (err.detail || "No se pudo cerrar la caja"));
        }
    } catch (error) { notify.error("Error de conexión"); }
}

function openOpenModal() {
    document.getElementById('open_fondo').value = "0.00";
    document.getElementById('open_caja_modal').style.display = 'block';
}

function closeOpenModal() {
    document.getElementById('open_caja_modal').style.display = 'none';
}

async function confirmOpenCaja() {
    const fondo = parseFloat(document.getElementById('open_fondo').value) || 0;
    const user = getLoggedInUser();

    try {
        const response = await fetch(`${API_URL}/caja/abrir`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fondo_inicial: fondo, user_id: user.id })
        });

        if (response.ok) {
            notify.success("¡Caja abierta exitosamente!");
            closeOpenModal();
            setTimeout(() => location.reload(), 1000);
        } else {
            const err = await response.json();
            notify.error("Error: " + (err.detail || "No se pudo abrir la caja"));
        }
    } catch (error) { notify.error("Error de conexión"); }
}

async function loadHistory() {
    try {
        const response = await fetch(`${API_URL}/caja/historial`);
        const history = await response.json();
        
        document.getElementById('empty_state').style.display = 'none';
        document.getElementById('summary_content').style.display = 'none';
        document.getElementById('history_content').style.display = 'block';

        const columns = [
            { key: 'open_date', formatter: val => new Date(val).toLocaleString() },
            { key: 'close_date', formatter: val => val ? new Date(val).toLocaleString() : '<span class="badge badge-green">ACTIVA</span>' },
            { key: 'initial_fund', formatter: val => `S/ ${val.toFixed(2)}` },
            { key: 'total_sales', formatter: val => `S/ ${val.toFixed(2)}` },
            { 
                key: 'status', 
                formatter: val => `<span class="stock-badge ${val === 'OPEN' ? 'stock-ok' : 'stock-low'}">${val === 'OPEN' ? 'ABIERTA' : 'CERRADA'}</span>` 
            }
        ];

        renderTable(history.reverse(), columns, 'history_tbody');
        notify.info("Historial cargado");
    } catch (error) { notify.error("Error al cargar historial"); }
}

function openMovementModal(tipo) {
    if (!currentSession) return notify.warn("Debes abrir la caja primero");
    document.getElementById('mov_tipo').value = tipo;
    document.getElementById('mov_title').textContent = tipo === 'INGRESO' ? "Nuevo Ingreso Manual" : "Nuevo Retiro Manual";
    document.getElementById('movement_form').reset();
    document.getElementById('movement_modal').style.display = "block";
}

function closeMovementModal() {
    document.getElementById('movement_modal').style.display = "none";
}

function setupMovementForm() {
    const form = document.getElementById('movement_form');
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const user = getLoggedInUser();
            const movData = {
                user_id: user.id,
                tipo: document.getElementById('mov_tipo').value,
                monto: parseFloat(document.getElementById('mov_monto').value),
                descripcion: document.getElementById('mov_desc').value
            };

            if (isNaN(movData.monto) || movData.monto <= 0) {
                return notify.warn("Ingrese un monto válido");
            }

            try {
                const response = await fetch(`${API_URL}/caja/movimiento`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(movData)
                });

                if (response.ok) {
                    closeMovementModal();
                    fetchResumen();
                    notify.success("Movimiento registrado con éxito");
                } else {
                    const err = await response.json();
                    notify.error("Error: " + (err.detail || "No se pudo registrar"));
                }
            } catch (error) { notify.error("Error de conexión"); }
        });
    }
}

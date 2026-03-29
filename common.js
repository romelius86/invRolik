// common.js - Lógica compartida para seguridad y permisos
const API_URL = ""; // Ruta automática (relativa)

// --- UTILIDADES ---

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'error') icon = 'exclamation-circle';
    if (type === 'warning') icon = 'exclamation-triangle';

    toast.innerHTML = `
        <i class="fas fa-${icon}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 4000);
}

// Reemplazar alert con toast donde sea posible
const notify = {
    success: (msg) => showToast(msg, 'success'),
    error: (msg) => showToast(msg, 'error'),
    warn: (msg) => showToast(msg, 'warning'),
    info: (msg) => showToast(msg, 'info')
};

// --- UTILIDADES DE IMPRESIÓN Y PDF ---

async function descargarPDF(id, formato = '80mm') {
    if (!id) return alert("ID de venta no válido");
    
    const notify = typeof showToast === 'function' ? showToast : alert;
    notify(`Generando PDF ${formato}...`);

    try {
        // 1. Obtener el HTML completo del servidor
        const response = await fetch(`${API_URL}/ventas/${id}/ticket?format=${formato}&no_print=true`);
        const htmlText = await response.text();
        
        // 2. Crear un iframe invisible para renderizar el HTML de forma aislada y correcta
        const iframe = document.createElement('iframe');
        iframe.style.position = 'fixed';
        iframe.style.left = '-9999px';
        iframe.style.visibility = 'hidden';
        document.body.appendChild(iframe);
        
        // 3. Escribir el HTML en el iframe
        const doc = iframe.contentWindow.document;
        doc.open();
        doc.write(htmlText);
        doc.close();

        // 4. Esperar un momento a que el navegador procese los estilos y fuentes
        await new Promise(resolve => setTimeout(resolve, 800));

        // 5. Obtener el contenedor del ticket dentro del iframe
        const ticketElement = doc.querySelector('.ticket-container') || doc.body;
        
        const isA4 = formato.toUpperCase() === 'A4';
        const opt = {
            margin: isA4 ? 10 : 2,
            filename: `Recibo_ROLIK_${id}.pdf`,
            image: { type: 'jpeg', quality: 1 },
            html2canvas: { 
                scale: 3, 
                useCORS: true, 
                logging: false,
                backgroundColor: '#ffffff'
            },
            jsPDF: { 
                unit: 'mm', 
                format: isA4 ? 'a4' : [80, 250], 
                orientation: 'portrait' 
            }
        };

        // 6. Generar el PDF
        await html2pdf().set(opt).from(ticketElement).save();
        
        // 7. Limpiar
        document.body.removeChild(iframe);
        if (typeof showToast === 'function') notify("¡PDF Descargado!");
    } catch (e) {
        console.error("Error PDF:", e);
        alert("Error al generar PDF: " + e.message);
    }
}

function formatCurrency(amount) {
    return "S/ " + parseFloat(amount).toFixed(2);
}

function debounce(func, timeout = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => { func.apply(this, args); }, timeout);
    };
}

/**
 * Renderiza una tabla genérica
 * @param {Array} data - Lista de objetos a mostrar
 * @param {Array} columns - Configuración de columnas [{label: 'Nombre', key: 'nombre', formatter: val => val}]
 * @param {string} containerId - ID del <tbody> donde se insertarán las filas
 */
function renderTable(data, columns, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";
    
    if (data.length === 0) {
        container.innerHTML = `<tr><td colspan="${columns.length}" style="text-align:center; padding:20px; color:var(--text-muted);">No se encontraron registros.</td></tr>`;
        return;
    }

    data.forEach(item => {
        const tr = document.createElement('tr');
        columns.forEach(col => {
            const td = document.createElement('td');
            let value = item[col.key];
            if (col.formatter) value = col.formatter(value, item);
            td.innerHTML = value !== undefined ? value : "";
            if (col.style) td.style = col.style;
            tr.appendChild(td);
        });
        container.appendChild(tr);
    });
}

function getLoggedInUser() {
    const stored = sessionStorage.getItem('user');
    if (!stored) return null;
    return JSON.parse(stored);
}

function hasPermission(permission) {
    const user = getLoggedInUser();
    if (!user) return false;
    
    // Los admins suelen tener todos los permisos en sistemas ERP
    if (user.role === 'admin') return true;
    
    if (!user.permissions) return false;
    
    // Permisos que no existen en DB pero queremos controlar
    if (permission === 'dashboard.view') return true; // Todos ven el dashboard
    if (permission === 'customer.view') return true;  // Basado en main.py, todos ven clientes
    
    return user.permissions.includes(permission);
}

function checkAccess() {
    const user = getLoggedInUser();
    if (!user && !window.location.href.includes('login.html')) {
        window.location.href = 'login.html';
        return;
    }
    
    // Al cargar el DOM, aplicar visibilidad de menú
    document.addEventListener('DOMContentLoaded', () => {
        applyPermissions();
        updateUserDisplay();
    });
}

function updateUserDisplay() {
    const user = getLoggedInUser();
    if (!user) return;
    
    const nameEl = document.getElementById('user_name_display');
    const roleEl = document.getElementById('user_role_display');
    if (nameEl) nameEl.textContent = user.username;
    if (roleEl) roleEl.textContent = user.role.toUpperCase();
    
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.onclick = () => {
            sessionStorage.removeItem('user');
            window.location.href = 'login.html';
        };
    }
}

function applyPermissions() {
    // Lista de mapeo: ID de elemento -> Permiso requerido
    const permissionMap = {
        'nav_dashboard': 'dashboard.view', // Generalmente todos ven dashboard
        'nav_pos': 'pos.use',
        'nav_inventory': 'product.view',
        'nav_clients': 'customer.view',
        'nav_purchases': 'purchase_order.view',
        'nav_cash': 'cash.manage',
        'nav_reports': 'report.view.sales',
        'nav_users': 'user.view'
    };

    for (const [id, perm] of Object.entries(permissionMap)) {
        const el = document.getElementById(id);
        if (el && !hasPermission(perm)) {
            el.style.display = 'none';
        }
    }

    // Botones de acción específicos
    const actionButtons = {
        'btn_new_product': 'product.create',
        'btn_new_customer': 'customer.create', // Asumido
        'btn_new_order': 'purchase_order.create',
        'btn_new_user': 'user.create'
    };

    for (const [id, perm] of Object.entries(actionButtons)) {
        const btn = document.getElementById(id);
        if (btn && !hasPermission(perm)) {
            btn.style.display = 'none';
        }
    }
}

// Ejecutar chequeo de inmediato
if (!window.location.href.includes('login.html')) {
    const user = getLoggedInUser();
    if (!user) {
        window.location.href = 'login.html';
    }
}

// Lógica para Menú Hamburguesa (Responsive)
document.addEventListener('DOMContentLoaded', () => {
    const header = document.querySelector('header');
    if (header && !document.querySelector('.menu-toggle')) {
        const toggleBtn = document.createElement('button');
        toggleBtn.className = 'menu-toggle';
        toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
        toggleBtn.onclick = () => {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar) sidebar.classList.toggle('active');
        };
        header.prepend(toggleBtn);
    }

    // Cerrar sidebar al hacer clic en el contenido principal (en móviles)
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.addEventListener('click', () => {
            const sidebar = document.querySelector('.sidebar');
            if (sidebar && sidebar.classList.contains('active') && window.innerWidth <= 768) {
                sidebar.classList.remove('active');
            }
        });
    }
});

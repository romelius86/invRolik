// pos_script.js - Lógica para Punto de Venta con Buscador Avanzado y Precio Editable

let cart = [];
let cachedProducts = []; 
let selectedComprobante = 'BOLETA';
let selectedMetodo = 'EFECTIVO';
let last_sale_id = null;

function setComprobante(tipo) {
    selectedComprobante = tipo;
    const buttons = document.querySelectorAll('#group_comprobante .toggle-btn');
    buttons.forEach(btn => {
        if (btn.innerText.trim() === tipo) btn.classList.add('active');
        else btn.classList.remove('active');
    });
}

function setMetodo(metodo) {
    selectedMetodo = metodo;
    const buttons = document.querySelectorAll('#group_metodo .toggle-btn');
    buttons.forEach(btn => {
        const btnText = btn.innerText.trim();
        if ((btnText === 'EFECTIVO' && metodo === 'EFECTIVO') || 
            (btnText === 'TRANSF.' && metodo === 'TRANSFERENCIA') || 
            (btnText === 'YAPE' && metodo === 'YAPE/PLIN')) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

document.addEventListener('DOMContentLoaded', () => {
    cargarProductosEnCache();
    const searchInput = document.getElementById('pos_search');

    // SISTEMA HÍBRIDO - FOCO AUTOMÁTICO
    if (searchInput) {
        searchInput.focus();

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
            if (query.length < 2) {
                // Restaurar mensaje inicial
                document.getElementById('pos_results').innerHTML = `
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); opacity: 0.5; margin-top: 50px;">
                        <i class="fas fa-barcode" style="font-size: 48px; margin-bottom: 15px;"></i>
                        <p style="margin: 0; font-size: 16px;">Escribe para buscar o escanea un producto...</p>
                    </div>
                `;
                return;
            }
            ejecutarBusquedaInteligente(query);
        });

        // SOPORTE LECTORA: Detectar Enter
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const code = searchInput.value.trim();
                if (code.length > 0) {
                    const product = cachedProducts.find(p => p.codigo.toLowerCase() === code.toLowerCase());
                    if (product) {
                        addToCart(product);
                        limpiarBusqueda();
                        showToast(`Agregado: ${product.nombre}`);
                    } else {
                        ejecutarBusquedaInteligente(code);
                    }
                }
            }
        });
    }

    // Re-enfocar el buscador
    window.addEventListener('click', (e) => {
        const activeModal = document.querySelector('.modal[style*="display: block"]');
        if (!activeModal) {
            if (searchInput) searchInput.focus();
        }
    });

    // Autocompletado de clientes
    const chkNombre = document.getElementById('chk_nombre');
    const chkDoc = document.getElementById('chk_documento');
    
    if (chkNombre) {
        chkNombre.addEventListener('input', (e) => buscarClientesAutocomplete(e.target.value, 'nombre'));
        chkNombre.addEventListener('blur', () => setTimeout(() => ocultarSugerencias('nombre'), 200));
    }
    if (chkDoc) {
        chkDoc.addEventListener('input', (e) => buscarClientesAutocomplete(e.target.value, 'documento'));
        chkDoc.addEventListener('blur', () => setTimeout(() => ocultarSugerencias('documento'), 200));
    }
});

function limpiarBusqueda() {
    const input = document.getElementById('pos_search');
    if (input) {
        input.value = "";
        input.focus();
    }
    const results = document.getElementById('pos_results');
    if (results) {
        results.innerHTML = `
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-muted); opacity: 0.5; margin-top: 50px;">
                <i class="fas fa-barcode" style="font-size: 48px; margin-bottom: 15px;"></i>
                <p style="margin: 0; font-size: 16px;">Escribe para buscar o escanea un producto...</p>
            </div>
        `;
    }
}

function renderFavoritos() {
    const container = document.getElementById('quick_access_container');
    if (!container) return;
    
    const favoritos = cachedProducts
        .filter(p => p.stock_actual > 0)
        .slice(0, 10);

    container.innerHTML = favoritos.map(p => `
        <button class="btn btn-secondary" style="background: rgba(59, 130, 246, 0.1); border: 1px solid #334155; color: white; padding: 12px 15px; border-radius: 10px; font-size: 13px; font-weight: bold; transition: all 0.2s;" onclick='addToCart(${JSON.stringify(p)})'>
            <i class="fas fa-star" style="color: #f59e0b; margin-right: 5px; font-size: 10px;"></i> ${p.nombre.substring(0, 15)}
        </button>
    `).join('') || '<p style="color:var(--text-muted); font-size:12px;">Sin productos favoritos configurados.</p>';
}

function showToast(message) {
    let toast = document.getElementById('pos_toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'pos_toast';
        toast.style = "position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); background: #22c55e; color: white; padding: 12px 25px; border-radius: 50px; font-weight: bold; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3); z-index: 9999; display: none; border: 2px solid rgba(255,255,255,0.2);";
        document.body.appendChild(toast);
    }
    toast.innerText = message;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 2000);
}

async function buscarClientesAutocomplete(query, tipo) {
    const suggestionsId = `suggestions_${tipo}`;
    let suggestionsDiv = document.getElementById(suggestionsId);
    
    if (!suggestionsDiv) {
        suggestionsDiv = document.createElement('div');
        suggestionsDiv.id = suggestionsId;
        suggestionsDiv.style = "position: absolute; width: 100%; background: #1e293b; border: 1px solid #3b82f6; z-index: 1000; max-height: 200px; overflow-y: auto; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); border-radius: 4px; margin-top: 2px;";
        const input = tipo === 'nombre' ? document.getElementById('chk_nombre') : document.getElementById('chk_documento');
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
                document.getElementById('chk_nombre').value = c.nombre;
                document.getElementById('chk_documento').value = c.documento;
                suggestionsDiv.style.display = 'none';
            };
            suggestionsDiv.appendChild(item);
        });
        suggestionsDiv.style.display = 'block';
    } catch (e) {
        console.error("Error buscando clientes:", e);
    }
}

function ocultarSugerencias(tipo) {
    const div = document.getElementById(`suggestions_${tipo}`);
    if (div) div.style.display = 'none';
}

async function cargarProductosEnCache() {
    try {
        const response = await fetch(`${API_URL}/productos`);
        cachedProducts = await response.json();
    } catch (e) { console.warn("No se pudo cargar la caché"); }
}

function ejecutarBusquedaInteligente(query) {
    const words = query.split(/\s+/).filter(w => w.length > 0);
    
    // Filtrar y calificar por similitud
    const scored = cachedProducts.map(p => {
        const sku = (p.codigo || "").toLowerCase();
        const nombre = (p.nombre || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        const categoria = (p.categoria || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        const searchPool = sku + " " + nombre + " " + categoria;
        
        let score = 0;
        let matchesAll = true;

        words.forEach(word => {
            if (searchPool.includes(word)) {
                // RANKING DE RELEVANCIA
                if (nombre === word) score += 5000;
                if (nombre.startsWith(word)) score += 2000;
                if (sku.includes(word)) score += 1000;
                if (categoria.includes(word)) score += 500;
                const pos = nombre.indexOf(word);
                if (pos !== -1) score += (500 - pos);
            } else {
                matchesAll = false;
            }
        });
        return { p, score, matchesAll };
    });

    const visible = scored.filter(s => s.matchesAll).sort((a, b) => b.score - a.score);
    renderSearchResults(visible.map(v => v.p), query);
}

function renderSearchResults(products, query = "") {
    const resultsDiv = document.getElementById('pos_results');
    if (!resultsDiv) return;
    resultsDiv.innerHTML = "";
    
    if (products.length === 0) {
        resultsDiv.innerHTML = '<p style="text-align: center; color: var(--text-muted); margin-top: 50px;">No se encontraron productos.</p>';
        return;
    }

        products.forEach(p => {
            const div = document.createElement('div');
            div.className = "product-item";
            const isLowStock = p.stock_actual <= p.stock_minimo;
            
            // Calcular stock en unidades individuales para visualización
            let stockDisplay = p.stock_actual;
            let factor = 1;
            const unidadUpper = (p.unidad || "").toUpperCase();
            if (unidadUpper.includes("MILLAR")) factor = 1000;
            else if (unidadUpper.includes("CIENTO")) factor = 100;
            else if (unidadUpper.includes("DOCENA")) factor = 12;

            if (factor > 1) {
                const totalUnits = p.stock_actual * factor;
                stockDisplay = `${p.stock_actual} ${p.unidad} (${totalUnits} UND)`;
            } else {
                stockDisplay = `${p.stock_actual} ${p.unidad || 'UND'}`;
            }

            const unidadesDesc = p.unidad ? `<span class="badge badge-blue" style="font-size: 10px; margin-left: 5px;">${p.unidad}</span>` : "";

            div.innerHTML = `
                <div style="flex: 1; padding-right: 15px;">
                    <div style="color: white; font-weight: 700; font-size: 16px; margin-bottom: 4px;">
                        ${p.nombre} ${unidadesDesc}
                    </div>
                    <div style="display: flex; gap: 15px; align-items: center;">
                        <span style="color: var(--accent-color); font-family: monospace; font-size: 13px;">${p.codigo}</span>
                        <span style="color: var(--text-muted); font-size: 13px;">Stock: 
                            <span class="badge ${isLowStock ? 'badge-red' : 'badge-green'}" style="padding: 2px 8px; font-size: 11px;">${stockDisplay}</span>
                        </span>
                    </div>
                </div>
                <div style="text-align: right; display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
                    <div style="font-size: 22px; color: #22c55e; font-weight: 900;">S/ ${p.precio_venta.toFixed(2)}</div>
                    <button class="btn btn-primary" style="padding: 10px 20px; font-size: 13px; border-radius: 8px; font-weight: bold;" onclick='addToCart(${JSON.stringify(p)})'>
                        <i class="fas fa-plus-circle"></i> SELECCIONAR
                    </button>
                </div>
            `;
            resultsDiv.appendChild(div);
        });
}

async function addToCart(product) {
    try {
        // Consultar si el producto tiene unidades adicionales
        const res = await fetch(`${API_URL}/productos/${product.codigo}/unidades`);
        const units = await res.json();
        
        if (units.length > 0) {
            // Si hay unidades adicionales, mostramos el modal de selección
            openUnitSelectionModal(product, units);
        } else {
            // Si no hay unidades adicionales, añadir como unidad base
            confirmAddToCart(product, product.unidad || 'UND', 1, product.precio_venta);
        }
    } catch (e) {
        console.error("Error al obtener unidades:", e);
        confirmAddToCart(product, product.unidad || 'UND', 1, product.precio_venta);
    }
}

function openUnitSelectionModal(product, units) {
    let modal = document.getElementById('pos_unit_modal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'pos_unit_modal';
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 450px;">
                <h2 style="margin-top:0;">Seleccionar Presentación</h2>
                <p style="color: var(--text-muted); margin-bottom: 20px;">Elija la unidad de medida para <strong>${product.nombre}</strong></p>
                <div id="unit_options_list" style="display: flex; flex-direction: column; gap: 10px;"></div>
                <div style="margin-top: 20px; text-align: right;">
                    <button onclick="document.getElementById('pos_unit_modal').style.display='none'" class="btn-secondary" style="padding: 10px 20px; border-radius: 8px;">CANCELAR</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }

    const list = document.getElementById('unit_options_list');
    list.innerHTML = "";

    // Opción 1: Unidad Base
    const baseBtn = document.createElement('button');
    baseBtn.className = 'btn';
    baseBtn.style = "justify-content: space-between; padding: 15px; background: rgba(59, 130, 246, 0.1); border: 1px solid #3b82f6; color: white;";
    baseBtn.innerHTML = `<span>${product.unidad || 'Unidad (Base)'}</span> <strong>S/ ${product.precio_venta.toFixed(2)}</strong>`;
    baseBtn.onclick = () => {
        confirmAddToCart(product, product.unidad || 'UND', 1, product.precio_venta);
        modal.style.display = 'none';
    };
    list.appendChild(baseBtn);

    // Opciones adicionales
    units.forEach(u => {
        const btn = document.createElement('button');
        btn.className = 'btn';
        btn.style = "justify-content: space-between; padding: 15px; background: rgba(34, 197, 94, 0.1); border: 1px solid #22c55e; color: white;";
        btn.innerHTML = `<span>${u.nombre_unidad} (x${u.factor_conversion})</span> <strong>S/ ${u.precio_venta.toFixed(2)}</strong>`;
        btn.onclick = () => {
            confirmAddToCart(product, u.nombre_unidad, u.factor_conversion, u.precio_venta);
            modal.style.display = 'none';
        };
        list.appendChild(btn);
    });

    modal.style.display = 'block';
}

function confirmAddToCart(product, unidadNombre, factor, precio) {
    const itemKey = `${product.codigo}_${unidadNombre}`;
    const existing = cart.find(item => item.itemKey === itemKey);
    
    if (existing) {
        existing.cantidad += 1;
    } else {
        cart.push({
            itemKey: itemKey,
            codigo: product.codigo,
            nombre: product.nombre,
            unidad: unidadNombre,
            factor: factor,
            precio_venta: precio,
            cantidad: 1
        });
    }
    renderCart();
}

function renderCart() {
    const cartList = document.getElementById('cart_list');
    const totalSpan = document.getElementById('total_amount');
    if (!cartList) return;
    cartList.innerHTML = "";
    let total = 0;
    cart.forEach((item, index) => {
        const subtotal = item.precio_venta * item.cantidad;
        total += subtotal;
        const div = document.createElement('div');
        div.className = "cart-item";
        div.innerHTML = `
            <div style="flex-grow: 1; cursor:pointer;">
                <strong style="color: white; font-size:14px;" onclick="promptEditQuantity(${index})">${item.nombre}</strong><br>
                <span onclick="promptEditQuantity(${index})" style="background:#1e293b; border:1px solid #334155; color:white; border-radius:4px; padding:2px 8px; font-weight:bold; display:inline-block; margin-top:4px;">${item.cantidad}</span>
                <span style="color:var(--text-muted); margin: 0 5px;">x</span>
                <span onclick="promptEditPrice(${index})" style="background:#1e293b; border:1px solid #334155; color:var(--success); border-radius:4px; padding:2px 8px; font-weight:bold; display:inline-block;">S/ ${item.precio_venta.toFixed(2)}</span>
            </div>
            <div style="text-align: right;">
                <button onclick="removeFromCart('${item.codigo}')" style="background:none; border:none; color:#ef4444; cursor:pointer; padding:5px;"><i class="fas fa-trash"></i></button><br>
                <strong style="color: var(--success); font-size: 15px;">S/ ${subtotal.toFixed(2)}</strong>
            </div>
        `;
        cartList.appendChild(div);
    });
    if (totalSpan) totalSpan.textContent = total.toFixed(2);
}

function promptEditQuantity(index) {
    const item = cart[index];
    const newQty = prompt(`Editar cantidad para ${item.nombre}:`, item.cantidad);
    if (newQty !== null && newQty !== "") {
        updateCartItem(index, 'cantidad', newQty);
    }
}

function promptEditPrice(index) {
    const item = cart[index];
    const newPrice = prompt(`Editar precio para ${item.nombre}:`, item.precio_venta.toFixed(2));
    if (newPrice !== null && newPrice !== "") {
        updateCartItem(index, 'precio', newPrice);
    }
}

function updateCartItem(index, field, value) {
    const numValue = parseFloat(value);
    if (isNaN(numValue) || numValue < 0) return;
    if (field === 'cantidad') cart[index].cantidad = Math.max(0.01, numValue);
    if (field === 'precio') cart[index].precio_venta = numValue;
    renderCart();
    if (document.getElementById('checkout_modal').style.display === 'block') actualizarModalCartList();
}

function removeFromCart(codigo) {
    cart = cart.filter(item => item.codigo !== codigo);
    renderCart();
}

function openCheckoutModal() {
    if (cart.length === 0) return alert("El carrito está vacío");
    document.getElementById('checkout_modal').style.display = 'block';
    actualizarModalCartList();
    updateToggleButtons();
}

function closeCheckoutModal() {
    document.getElementById('checkout_modal').style.display = 'none';
}

function actualizarModalCartList() {
    const list = document.getElementById('modal_cart_list');
    if (!list) return;
    list.innerHTML = "";
    let total = 0;
    cart.forEach((item, index) => {
        const subtotal = item.precio_venta * item.cantidad;
        total += subtotal;
        const div = document.createElement('div');
        div.style = "display: flex; justify-content: space-between; align-items: center; padding: 10px; border-bottom: 1px solid #334155; color: white;";
        div.innerHTML = `
            <div style="flex: 1;">
                <div style="font-weight: bold;">${item.nombre} <span class="badge badge-blue" style="font-size: 10px; margin-left: 5px;">${item.unidad}</span></div>
                <div style="font-size: 11px; color: var(--accent-color); font-family: monospace;">${item.codigo}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 10px;">
                <span>${item.cantidad} x </span>
                <input type="number" value="${item.precio_venta.toFixed(2)}" step="0.01" onchange="updateCartItem(${index}, 'precio', this.value)" style="width: 75px; background:#0f172a; border: 1px solid #3b82f6; color:var(--success); font-weight:bold; text-align:right; border-radius: 4px; padding: 2px;">
                <div style="width: 80px; text-align: right; font-weight:bold;">S/ ${subtotal.toFixed(2)}</div>
            </div>
        `;
        list.appendChild(div);
    });
    document.getElementById('chk_total').innerText = total.toFixed(2);
    document.getElementById('chk_recibido').value = total.toFixed(2);
    calcularVuelto();
}


function setComprobante(val) { selectedComprobante = val; updateToggleButtons(); }
function setMetodo(val) { selectedMetodo = val; updateToggleButtons(); }

function updateToggleButtons() {
    const map = { 
        'BOLETA': 'BOLETA', 
        'FACTURA': 'FACTURA', 
        'TICKET': 'TICKET', 
        'EFECTIVO': 'EFECTIVO', 
        'TRANSF.': 'TRANSFERENCIA', 
        'YAPE': 'YAPE/PLIN' 
    };
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        const text = btn.innerText.trim().toUpperCase();
        const val = map[text] || text;
        btn.classList.toggle('active', val === selectedComprobante || val === selectedMetodo);
    });
}

function calcularVuelto() {
    const total = parseFloat(document.getElementById('chk_total').innerText);
    const recibido = parseFloat(document.getElementById('chk_recibido').value || 0);
    document.getElementById('chk_vuelto').innerText = Math.max(0, recibido - total).toFixed(2);
}

function toggleNuevoClienteRapido() {
    const div = document.getElementById('nuevo_cliente_rapido');
    if (div.style.display === 'none') {
        div.style.display = 'block';
        // Si ya hay un documento escrito, lo pasamos al mini-form
        const doc = document.getElementById('chk_documento').value;
        if (doc && !document.getElementById('nc_nombre').value) {
            // Podríamos inicializar algo aquí si fuera necesario
        }
        document.getElementById('nc_nombre').focus();
    } else {
        div.style.display = 'none';
    }
}

async function guardarClienteRapido() {
    const documento = document.getElementById('chk_documento').value;
    const nombre = document.getElementById('nc_nombre').value;
    const telefono = document.getElementById('nc_telefono').value;
    const direccion = document.getElementById('nc_direccion').value;

    if (!documento || !nombre) {
        alert("DNI/RUC y Nombre son obligatorios");
        return;
    }

    const clienteData = {
        documento: documento,
        nombre: nombre,
        telefono: telefono,
        direccion: direccion,
        email: ""
    };

    try {
        const response = await fetch(`${API_URL}/clientes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(clienteData)
        });

        if (response.ok) {
            // Llenar los campos de la venta
            document.getElementById('chk_nombre').value = nombre.toUpperCase();
            
            // Limpiar y ocultar mini-form
            document.getElementById('nc_nombre').value = "";
            document.getElementById('nc_telefono').value = "";
            document.getElementById('nc_direccion').value = "";
            document.getElementById('nuevo_cliente_rapido').style.display = 'none';
            
            alert("Cliente registrado y seleccionado");
        } else {
            const err = await response.json();
            alert("Error: " + (err.detail || "No se pudo guardar el cliente"));
        }
    } catch (error) {
        alert("Error de conexión al guardar cliente");
    }
}

async function procesarVentaFinal() {
    const total = parseFloat(document.getElementById('chk_total').innerText);
    const recibido = parseFloat(document.getElementById('chk_recibido').value || 0);
    const saleData = {
        user_id: getLoggedInUser().id,
        total: total,
        metodo_pago: selectedMetodo,
        tipo_comprobante: selectedComprobante,
        cliente_nombre: document.getElementById('chk_nombre').value || "PÚBLICO EN GENERAL",
        cliente_documento: document.getElementById('chk_documento').value || "00000000",
        monto_pagado: recibido,
        vuelto: Math.max(0, recibido - total),
        items: cart.map(item => ({ 
            producto_codigo: item.codigo, 
            cantidad: item.cantidad, 
            precio_unitario: item.precio_venta,
            factor: item.factor || 1.0,
            unidad_nombre: item.unidad // Enviamos el nombre: "DOCENA", "MILLAR", etc.
        }))
    };
    try {
        const response = await fetch(`${API_URL}/ventas`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(saleData)
        });
        if (response.ok) {
            const res = await response.json();
            last_sale_id = res.transaction_id;
            closeCheckoutModal();
            document.getElementById('success_modal').style.display = 'block';
        } else {
            const err = await response.json();
            let msg = "No se pudo procesar la venta.";
            if (err.detail) {
                if (Array.isArray(err.detail)) {
                    msg = err.detail.map(e => `${e.loc.join('.')}: ${e.msg}`).join('\n');
                } else {
                    msg = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
                }
            }
            alert("Error: " + msg);
        }
    } catch (e) { alert("Error de conexión"); }
}

function closeSuccessModal() {
    document.getElementById('success_modal').style.display = 'none';
    cart = [];
    renderCart();
    document.getElementById('pos_search').value = "";
    document.getElementById('pos_results').innerHTML = "";
}

function imprimirTicket(id, format) { window.open(`${API_URL}/ventas/${id}/ticket?format=${format}`, '_blank'); }

function abrirWhatsAppSolo() {
    const clienteNombre = document.getElementById('chk_nombre').value || "Cliente";
    const telefono = prompt(`Ingrese el número de WhatsApp para ${clienteNombre}:`, "");
    if (telefono) {
        const mensaje = encodeURIComponent(`Hola ${clienteNombre}, le envío su recibo de ROLIK. Por favor, adjunte el archivo PDF que se acaba de descargar.`);
        window.open(`https://wa.me/51${telefono}?text=${mensaje}`, '_blank');
    }
}

async function buscarClienteCheckout() {
    const doc = document.getElementById('chk_documento').value;
    if (!doc) return;
    try {
        const response = await fetch(`${API_URL}/clientes/${doc}`);
        if (response.ok) {
            const c = await response.json();
            document.getElementById('chk_nombre').value = c.nombre;
        }
    } catch (e) {}
}

async function buscarProductosModal(query) {
    const resultsDiv = document.getElementById('modal_search_results');
    if (query.length < 2) { resultsDiv.style.display = 'none'; return; }
    try {
        const response = await fetch(`${API_URL}/productos?search=${encodeURIComponent(query)}`);
        const products = await response.json();
        resultsDiv.innerHTML = "";
        products.slice(0, 5).forEach(p => {
            const div = document.createElement('div');
            div.style = "padding:10px; border-bottom:1px solid #334155; cursor:pointer; color:white;";
            div.innerHTML = `<strong>${p.nombre}</strong> - S/ ${p.precio_venta.toFixed(2)}`;
            div.onclick = () => { addToCart(p); resultsDiv.style.display = 'none'; actualizarModalCartList(); };
            resultsDiv.appendChild(div);
        });
        resultsDiv.style.display = 'block';
    } catch (e) {}
}

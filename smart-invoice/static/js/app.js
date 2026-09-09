/* ==========================================================================
   Smart Freelance Invoice & Payment Risk System - JavaScript App
   Multi-Tenant Auth, Client Roster & 1-Click PDF Generation
   ========================================================================== */

let currentUser = null;
let currentInvoiceList = [];
let registeredClientsList = [];
let userServicesList = [];
let selectedInvoiceForDetail = null;

// Pagination configuration for invoices
let invoiceCurrentPage = 1;
const invoicePageSize = 10;

document.addEventListener("DOMContentLoaded", () => {
    checkAuthStatus();
});

// -------------------------------------------------------------
// 1. AUTHENTICATION HANDLERS
// -------------------------------------------------------------
async function checkAuthStatus() {
    try {
        const res = await fetch("/api/auth/me");
        const data = await res.json();
        
        if (data.authenticated && data.user) {
            currentUser = data.user;
            showAppWorkspace();
        } else {
            showAuthScreen();
        }
    } catch (err) {
        console.error("Error checking auth status:", err);
        showAuthScreen();
    }
}

function showAuthScreen() {
    const authElem = document.getElementById("auth-container");
    const appElem = document.getElementById("app-workspace");
    if (authElem) authElem.classList.remove("hidden");
    if (appElem) appElem.classList.add("hidden");
}

function showAppWorkspace() {
    const authElem = document.getElementById("auth-container");
    const appElem = document.getElementById("app-workspace");
    if (authElem) authElem.classList.add("hidden");
    if (appElem) appElem.classList.remove("hidden");
    
    const userDisplay = document.getElementById("user-display-name");
    if (userDisplay && currentUser) userDisplay.textContent = currentUser.name;
    
    // Default to dashboard tab on load
    switchAppTab('dashboard');
    
    loadDashboardStats();
    loadInvoices();
    loadRegisteredClients();
    loadUserServices();
}

function switchAppTab(tabName) {
    const dashboardBtn = document.getElementById("btn-tab-dashboard");
    const workBtn = document.getElementById("btn-tab-work");
    const dashboardContent = document.getElementById("dashboard-tab-content");
    const workContent = document.getElementById("work-tab-content");

    if (tabName === "dashboard") {
        if (dashboardBtn) dashboardBtn.classList.add("active");
        if (workBtn) workBtn.classList.remove("active");
        if (dashboardContent) dashboardContent.classList.remove("hidden");
        if (workContent) workContent.classList.add("hidden");
    } else {
        if (dashboardBtn) dashboardBtn.classList.remove("active");
        if (workBtn) workBtn.classList.add("active");
        if (dashboardContent) dashboardContent.classList.add("hidden");
        if (workContent) workContent.classList.remove("hidden");
    }
}

function toggleAuthMode(mode) {
    if (document.getElementById("login-error")) document.getElementById("login-error").textContent = "";
    if (document.getElementById("register-error")) document.getElementById("register-error").textContent = "";
    
    const loginForm = document.getElementById("login-form");
    const registerForm = document.getElementById("register-form");

    if (mode === "register") {
        if (loginForm) loginForm.classList.add("hidden");
        if (registerForm) registerForm.classList.remove("hidden");
    } else {
        if (registerForm) registerForm.classList.add("hidden");
        if (loginForm) loginForm.classList.remove("hidden");
    }
}

function togglePasswordVisibility(inputId, iconElement) {
    const input = document.getElementById(inputId);
    if (input.type === "password") {
        input.type = "text";
        iconElement.classList.remove("fa-eye");
        iconElement.classList.add("fa-eye-slash");
    } else {
        input.type = "password";
        iconElement.classList.remove("fa-eye-slash");
        iconElement.classList.add("fa-eye");
    }
}

async function handleLogin(event) {
    event.preventDefault();
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value.trim();
    const errorDiv = document.getElementById("login-error");
    errorDiv.textContent = "";

    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        
        if (res.ok && data.user) {
            currentUser = data.user;
            showAppWorkspace();
        } else {
            errorDiv.textContent = data.error || "Login failed.";
        }
    } catch (err) {
        console.error("Login error:", err);
        errorDiv.textContent = "Server connection error.";
    }
}

async function handleRegister(event) {
    event.preventDefault();
    const name = document.getElementById("reg-name").value.trim();
    const email = document.getElementById("reg-email").value.trim();
    const password = document.getElementById("reg-password").value.trim();
    const errorDiv = document.getElementById("register-error");
    errorDiv.textContent = "";

    if (password.length < 6) {
        errorDiv.textContent = "Password must be at least 6 characters long.";
        return;
    }
    if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
        errorDiv.textContent = "Password must contain both letters and numbers.";
        return;
    }

    try {
        const res = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, email, password })
        });
        const data = await res.json();
        
        if (res.ok && data.user) {
            currentUser = data.user;
            showAppWorkspace();
        } else {
            errorDiv.textContent = data.error || "Registration failed.";
        }
    } catch (err) {
        console.error("Registration error:", err);
        errorDiv.textContent = "Server connection error.";
    }
}

async function handleLogout() {
    try {
        await fetch("/api/auth/logout", { method: "POST" });
        currentUser = null;
        showAuthScreen();
    } catch (err) {
        console.error("Logout error:", err);
    }
}

// -------------------------------------------------------------
// 2. REGISTERED CLIENTS ROSTER MANAGEMENT
// -------------------------------------------------------------
async function loadRegisteredClients() {
    try {
        const res = await fetch("/api/registered-clients");
        if (res.ok) {
            registeredClientsList = await res.json();
            populateClientDropdown();
            renderDashboardClientsTable();
        }
    } catch (err) {
        console.error("Error loading registered clients:", err);
    }
}

function renderDashboardClientsTable() {
    const tbody = document.getElementById("dashboard-clients-body");
    if (!tbody) return;
    if (!registeredClientsList || registeredClientsList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
                    No clients registered yet. Click "Add Client" to get started!
                </td>
            </tr>
        `;
        return;
    }
    tbody.innerHTML = registeredClientsList.map(c => `
        <tr>
            <td>
                <strong>${c.client_name}</strong>
                ${c.client_whatsapp ? `<br><small style="color:var(--primary-blue);"><i class="fa-brands fa-whatsapp"></i> ${c.client_whatsapp}</small>` : ''}
            </td>
            <td><span class="badge badge-amber">${c.payment_terms_days} days</span></td>
            <td>${c.client_email || '<span style="color: var(--text-dim);">No email</span>'}</td>
            <td style="text-align: right;">
                <button class="btn btn-sm btn-outline-danger" onclick="deleteClient(${c.id}, '${c.client_name}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join("");
}

function openRegisterClientModal() {
    document.getElementById("register-client-form").reset();
    document.getElementById("register-client-modal").classList.add("active");
}

function closeRegisterClientModal() {
    document.getElementById("register-client-modal").classList.remove("active");
}

async function handleRegisterClientSubmit(event) {
    event.preventDefault();
    const name = document.getElementById("new-client-name").value.trim();
    const email = document.getElementById("new-client-email").value.trim();
    const whatsapp = document.getElementById("new-client-whatsapp") ? document.getElementById("new-client-whatsapp").value.trim() : "";
    const terms = parseInt(document.getElementById("new-client-terms").value) || 14;
    const notes = document.getElementById("new-client-notes").value.trim();

    try {
        const res = await fetch("/api/registered-clients", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ client_name: name, client_email: email, client_whatsapp: whatsapp, payment_terms_days: terms, notes })
        });
        
        if (res.ok) {
            closeRegisterClientModal();
            await loadRegisteredClients();
            const clientSelect = document.getElementById("client-select");
            if (clientSelect) {
                clientSelect.value = name;
                onClientSelectChange();
            }
        } else {
            const data = await res.json();
            alert(data.error || "Failed to register client");
        }
    } catch (err) {
        console.error("Error registering client:", err);
    }
}

async function deleteClient(id, name) {
    if (!confirm(`Are you sure you want to permanently delete client '${name}' from your roster?`)) return;
    
    try {
        const res = await fetch(`/api/registered-clients/${id}`, { method: "DELETE" });
        if (res.ok) {
            await loadRegisteredClients();
        } else {
            const data = await res.json();
            alert(data.error || "Failed to delete client");
        }
    } catch (err) {
        console.error("Error deleting client:", err);
    }
}

function populateClientDropdown() {
    const select = document.getElementById("client-select");
    if (!select) return;
    select.innerHTML = '<option value="">-- Choose Registered Client --</option>';
    
    registeredClientsList.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.client_name;
        opt.textContent = `${c.client_name} (${c.payment_terms_days} days terms)`;
        opt.dataset.email = c.client_email || "";
        opt.dataset.terms = c.payment_terms_days || 14;
        select.appendChild(opt);
    });
}

function onClientSelectChange() {
    const select = document.getElementById("client-select");
    if (!select) return;
    const selectedOpt = select.options[select.selectedIndex];
    const clientNameInput = document.getElementById("client-name");
    const clientEmailInput = document.getElementById("client-email");
    const dueDateInput = document.getElementById("due-date");
    
    if (selectedOpt && selectedOpt.value) {
        if (clientNameInput) clientNameInput.value = selectedOpt.value;
        if (clientEmailInput) clientEmailInput.value = selectedOpt.dataset.email || "";
        
        const terms = parseInt(selectedOpt.dataset.terms) || 14;
        const invDateVal = document.getElementById("invoice-date")?.value || new Date().toISOString().split("T")[0];
        
        const invDateObj = new Date(invDateVal);
        invDateObj.setDate(invDateObj.getDate() + terms);
        if (dueDateInput) dueDateInput.value = invDateObj.toISOString().split("T")[0];

        if (clientNameInput) {
            clientNameInput.style.borderColor = "var(--primary-blue)";
            clientNameInput.style.boxShadow = "0 0 10px var(--primary-glow)";
            setTimeout(() => {
                clientNameInput.style.borderColor = "";
                clientNameInput.style.boxShadow = "";
            }, 1000);
        }
    }
}

function onInvoiceDateChange() {
    onClientSelectChange();
}

// -------------------------------------------------------------
// 3. DASHBOARD STATISTICS & OVERVIEW
// -------------------------------------------------------------
async function loadDashboardStats() {
    try {
        const res = await fetch("/api/dashboard");
        if (res.status === 401) { showAuthScreen(); return; }
        const data = await res.json();
        
        const totalBilledElem = document.getElementById("stat-total-billed");
        if (totalBilledElem) totalBilledElem.textContent = formatCurrency(data.total_billed);
        const totalCountElem = document.getElementById("stat-total-count");
        if (totalCountElem) totalCountElem.textContent = `${data.total_invoices} total invoices`;

        const pendingAmtElem = document.getElementById("stat-pending-amount");
        if (pendingAmtElem) pendingAmtElem.textContent = formatCurrency(data.total_pending);
        const pendingCountElem = document.getElementById("stat-pending-count");
        if (pendingCountElem) pendingCountElem.textContent = `${data.pending_count} pending settlement`;

        const overdueAmtElem = document.getElementById("stat-overdue-amount");
        if (overdueAmtElem) overdueAmtElem.textContent = formatCurrency(data.total_overdue);
        const overdueCountElem = document.getElementById("stat-overdue-count");
        if (overdueCountElem) overdueCountElem.textContent = `${data.overdue_count} overdue invoices`;

        const highRiskCountElem = document.getElementById("stat-high-risk-count");
        if (highRiskCountElem) highRiskCountElem.textContent = data.high_risk_count;
        
        renderDashboardGraph(data.total_billed, data.total_pending, data.total_overdue);
    } catch (err) {
        console.error("Error loading dashboard stats:", err);
    }
}

// -------------------------------------------------------------
// 4. FETCH & RENDER INVOICE HISTORY MATRIX
// -------------------------------------------------------------
async function loadInvoices() {
    try {
        const statusFilter = document.getElementById("filter-status")?.value || "";
        const riskFilter = document.getElementById("filter-risk")?.value || "";
        const searchQuery = document.getElementById("search-input")?.value.trim() || "";

        let url = `/api/invoices?status=${encodeURIComponent(statusFilter)}&risk=${encodeURIComponent(riskFilter)}&search=${encodeURIComponent(searchQuery)}`;
        const res = await fetch(url);
        if (res.status === 401) { showAuthScreen(); return; }
        
        const invoices = await res.json();
        currentInvoiceList = invoices;
        
        renderInvoicesTable(invoices);
    } catch (err) {
        console.error("Error loading invoices:", err);
    }
}

function filterInvoices() {
    invoiceCurrentPage = 1;
    loadInvoices();
}

async function refreshAllData() {
    const icon = document.getElementById("refresh-icon");
    if (icon) icon.classList.add("fa-spin");
    
    invoiceCurrentPage = 1;
    await Promise.all([
        loadDashboardStats(),
        loadInvoices(),
        loadRegisteredClients()
    ]);

    setTimeout(() => {
        if (icon) icon.classList.remove("fa-spin");
    }, 500);
}

function changeInvoicePage(delta) {
    invoiceCurrentPage += delta;
    renderInvoicesTable(currentInvoiceList);
}

function renderInvoicesTable(invoices) {
    const tbody = document.getElementById("invoices-table-body");
    if (!tbody) return;
    tbody.innerHTML = "";

    const totalInvoices = invoices.length;
    const totalPages = Math.ceil(totalInvoices / invoicePageSize) || 1;

    // Validate bounds
    if (invoiceCurrentPage > totalPages) {
        invoiceCurrentPage = totalPages;
    }
    if (invoiceCurrentPage < 1) {
        invoiceCurrentPage = 1;
    }

    // Update pagination controls
    const prevBtn = document.getElementById("prev-page-btn");
    const nextBtn = document.getElementById("next-page-btn");
    const indicator = document.getElementById("page-indicator");

    if (prevBtn) prevBtn.disabled = invoiceCurrentPage === 1;
    if (nextBtn) nextBtn.disabled = invoiceCurrentPage === totalPages;

    const startIdx = (invoiceCurrentPage - 1) * invoicePageSize;
    const endIdx = startIdx + invoicePageSize;
    const pageInvoices = invoices.slice(startIdx, endIdx);

    if (indicator) {
        if (totalInvoices === 0) {
            indicator.textContent = "No invoices";
        } else {
            indicator.textContent = `Page ${invoiceCurrentPage} of ${totalPages} (showing ${startIdx + 1}-${Math.min(endIdx, totalInvoices)} of ${totalInvoices})`;
        }
    }

    if (totalInvoices === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; color: var(--text-muted); padding: 2rem;">
                    No invoices match your search/filter criteria.
                </td>
            </tr>
        `;
        return;
    }

    pageInvoices.forEach(inv => {
        const tr = document.createElement("tr");
        
        if (inv.risk && inv.risk.is_overdue) {
            tr.classList.add("tr-overdue");
        }

        let badgeClass = "badge-blue";
        if (inv.status === "PAID") badgeClass = "badge-green";
        else if (inv.risk.is_overdue) badgeClass = "badge-red";
        else if (inv.risk.days_diff === 0 || Math.abs(inv.risk.days_diff) <= 2) badgeClass = "badge-amber";

        let riskTagClass = "risk-low";
        if (inv.risk.risk_level === "High") riskTagClass = "risk-high";
        else if (inv.risk.risk_level === "Medium") riskTagClass = "risk-medium";

        tr.innerHTML = `
            <td><strong>${inv.invoice_number}</strong></td>
            <td>${inv.client_name}</td>
            <td>${inv.invoice_date}</td>
            <td>${inv.due_date}</td>
            <td><strong>${formatCurrency(inv.grand_total)}</strong></td>
            <td>
                <span class="badge ${badgeClass}">
                    <i class="fa-solid ${inv.status === 'PAID' ? 'fa-check' : 'fa-clock'}"></i>
                    ${inv.risk.status_label}
                </span>
            </td>
            <td>
                <div class="risk-badge-box">
                    <span class="risk-score-num">${inv.status === 'PAID' ? '-' : inv.risk.risk_score}</span>
                    <span class="risk-tag ${inv.status === 'PAID' ? 'risk-low' : riskTagClass}">${inv.status === 'PAID' ? 'Settled' : inv.risk.risk_level}</span>
                </div>
            </td>
            <td>
                <div style="display: flex; gap: 0.4rem;">
                    <button class="btn btn-sm btn-secondary" onclick="openDetailModal(${inv.id})" title="Inspect Risk & Details">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                    <button class="btn btn-sm ${inv.pdf_url ? 'btn-primary' : 'btn-outline-primary'}" onclick="${inv.pdf_url ? `window.open('/api/invoices/${inv.id}/download-pdf', '_blank')` : `downloadInvoicePDFDirect(${inv.id})`}" title="${inv.pdf_url ? 'View Cloud PDF' : 'Download 1-Click PDF'}">
                        <i class="fa-solid fa-file-pdf"></i>
                    </button>
                    <button class="btn btn-sm btn-secondary" onclick="printInvoice(${inv.id})" title="Print Invoice">
                        <i class="fa-solid fa-print"></i>
                    </button>
                    ${inv.status === 'PENDING' ? `
                        <button class="btn btn-sm btn-success" onclick="markAsPaidDirect(${inv.id})" title="Mark as Paid">
                            <i class="fa-solid fa-check"></i>
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-outline-primary" style="color: #25D366; border-color: #25D366;" onclick="shareCurrentInvoiceWhatsApp(${inv.id})" title="Share via WhatsApp">
                        <i class="fa-brands fa-whatsapp"></i>
                    </button>
                </div>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// -------------------------------------------------------------
// 5. DYNAMIC LINE ITEMS & REAL-TIME CALCULATION
// -------------------------------------------------------------
function openCreateInvoiceModal() {
    fetch("/api/invoices/next-number")
        .then(res => res.json())
        .then(data => {
            const preview = document.getElementById("inv-number-preview");
            if (preview) preview.value = data.next_invoice_number;
        });

    populateClientDropdown();

    const tbody = document.getElementById("line-items-body");
    if (tbody) tbody.innerHTML = "";
    
    addLineItemRow("", 1, 0);

    const today = new Date().toISOString().split("T")[0];
    const defaultDue = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];
    
    const invDateElem = document.getElementById("invoice-date");
    if (invDateElem) invDateElem.value = today;
    const dueDateElem = document.getElementById("due-date");
    if (dueDateElem) dueDateElem.value = defaultDue;

    const modal = document.getElementById("create-modal");
    if (modal) modal.classList.add("active");
    calculateLiveTotals();
}

function closeCreateInvoiceModal() {
    const modal = document.getElementById("create-modal");
    if (modal) modal.classList.remove("active");
}

function addLineItemRow(description = "", hours = 1, hourlyRate = 50) {
    const tbody = document.getElementById("line-items-body");
    if (!tbody) return;
    const tr = document.createElement("tr");

    tr.innerHTML = `
        <td>
            <input type="text" class="item-desc" list="services-datalist" placeholder="Type or search saved work..." value="${description}" oninput="onServiceInputSearch(this)" required autocomplete="off">
        </td>
        <td>
            <input type="number" class="item-hours" min="0.01" step="0.5" value="${hours}" oninput="calculateLiveTotals()" required>
        </td>
        <td>
            <input type="number" class="item-rate" min="0" step="0.01" value="${hourlyRate}" oninput="calculateLiveTotals()" required>
        </td>
        <td>
            <strong class="item-line-total">₹0.00</strong>
        </td>
        <td style="text-align: center;">
            <button type="button" class="remove-row-btn" onclick="removeLineItemRow(this)">&times;</button>
        </td>
    `;
    tbody.appendChild(tr);
    calculateLiveTotals();
}

function onServiceInputSearch(inputElem) {
    const val = inputElem.value.trim().toLowerCase();
    if (!val) return;
    
    // Exact or partial match with saved services
    const matchedService = userServicesList.find(s => s.title.toLowerCase() === val || (s.title + " (₹" + parseFloat(s.hourly_rate).toFixed(2) + "/hr)").toLowerCase() === val);
    if (matchedService) {
        const row = inputElem.closest("tr");
        const rateInput = row.querySelector(".item-rate");
        if (inputElem.value !== matchedService.title) {
            inputElem.value = matchedService.title;
        }
        if (rateInput) {
            rateInput.value = parseFloat(matchedService.hourly_rate).toFixed(2);
            calculateLiveTotals();
        }
    }
}


function removeLineItemRow(btn) {
    const tbody = document.getElementById("line-items-body");
    if (tbody.children.length > 1) {
        btn.closest("tr").remove();
        calculateLiveTotals();
    } else {
        alert("At least one line item is required!");
    }
}

function calculateLiveTotals() {
    const rows = document.querySelectorAll("#line-items-body tr");
    let subtotal = 0.0;

    rows.forEach(row => {
        let hours = parseFloat(row.querySelector(".item-hours")?.value) || 0;
        let rate = parseFloat(row.querySelector(".item-rate")?.value) || 0;
        if (hours < 0) hours = 0;
        if (rate < 0) rate = 0;
        const lineTotal = hours * rate;

        const lineTotalElem = row.querySelector(".item-line-total");
        if (lineTotalElem) lineTotalElem.textContent = formatCurrency(lineTotal);
        subtotal += lineTotal;
    });

    let taxRate = parseFloat(document.getElementById("tax-rate")?.value) || 0;
    if (taxRate < 0) taxRate = 0;
    const taxAmount = subtotal * (taxRate / 100.0);
    const grandTotal = subtotal + taxAmount;

    const subElem = document.getElementById("calc-subtotal");
    if (subElem) subElem.textContent = formatCurrency(subtotal);
    const taxElem = document.getElementById("calc-tax");
    if (taxElem) taxElem.textContent = formatCurrency(taxAmount);
    const grandElem = document.getElementById("calc-grand-total");
    if (grandElem) grandElem.textContent = formatCurrency(grandTotal);
}

async function handleCreateInvoice(event) {
    event.preventDefault();
    
    const saveBtn = document.getElementById("btn-save-invoice");
    const originalBtnText = saveBtn ? saveBtn.innerHTML : `<i class="fa-solid fa-floppy-disk"></i> Save Invoice & Monitor`;
    
    const clientName = document.getElementById("client-name").value.trim();
    const clientEmail = document.getElementById("client-email").value.trim();
    const invoiceDate = document.getElementById("invoice-date").value;
    const dueDate = document.getElementById("due-date").value;
    const taxRateInput = document.getElementById("tax-rate");
    const taxRate = parseFloat(taxRateInput ? taxRateInput.value : 0) || 0;
    const notes = document.getElementById("invoice-notes").value.trim();

    if (taxRate < 0) {
        alert("Tax rate cannot be negative. Please enter a valid non-negative tax percentage.");
        if (taxRateInput) taxRateInput.focus();
        return;
    }
    if (!clientName) {
        alert("Please enter a Client Name.");
        document.getElementById("client-name").focus();
        return;
    }
    if (!invoiceDate || !dueDate) {
        alert("Please select both Invoice Date and Payment Due Date.");
        return;
    }

    const itemRows = document.querySelectorAll("#line-items-body tr");
    const items = [];
    let hasInvalidRow = false;

    itemRows.forEach(row => {
        const descInput = row.querySelector(".item-desc");
        const hoursInput = row.querySelector(".item-hours");
        const rateInput = row.querySelector(".item-rate");

        if (descInput && hoursInput && rateInput) {
            const desc = descInput.value.trim();
            const hours = parseFloat(hoursInput.value);
            const rate = parseFloat(rateInput.value);

            if (desc) {
                if (isNaN(hours) || hours <= 0) {
                    alert(`Invalid hours for service "${desc}". Hours must be a positive number greater than 0.`);
                    hoursInput.focus();
                    hasInvalidRow = true;
                    return;
                }
                if (isNaN(rate) || rate < 0) {
                    alert(`Invalid hourly rate for service "${desc}". Hourly rate cannot be negative.`);
                    rateInput.focus();
                    hasInvalidRow = true;
                    return;
                }
                items.push({ description: desc, hours: hours, hourly_rate: rate });
            }
        }
    });

    if (hasInvalidRow) return;

    if (items.length === 0) {
        alert("Please enter valid line item details (Service Description, Hours > 0, Hourly Rate >= 0).");
        return;
    }

    try {
        if (saveBtn) {
            saveBtn.disabled = true;
            saveBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Saving & Monitoring...`;
        }

        const res = await fetch("/api/invoices", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                client_name: clientName,
                client_email: clientEmail,
                invoice_date: invoiceDate,
                due_date: dueDate,
                tax_rate: taxRate,
                notes: notes,
                items: items
            })
        });

        const data = await res.json();
        if (res.ok) {
            closeCreateInvoiceModal();
            await loadDashboardStats();
            await loadInvoices();
            await loadRegisteredClients();
            
            if (data.invoice) {
                uploadInvoicePDFToCloud(data.invoice);
            }
        } else {
            alert(data.error || "Failed to create invoice");
        }
    } catch (err) {
        console.error("Error creating invoice:", err);
        alert("Server error while creating invoice. Please try again.");
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalBtnText;
        }
    }
}

function uploadInvoicePDFToCloud(invoice) {
    renderPrintableInvoice(invoice);
    const element = document.getElementById("printable-invoice");
    if (!element) return;
    
    const originalDisplay = element.style.display;
    element.style.display = "block";
    element.style.backgroundColor = "#ffffff";
    element.style.color = "#1e293b";
    
    const opt = {
        margin:       [0.4, 0.4, 0.4, 0.4],
        filename:     `${invoice.invoice_number}_Invoice.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, logging: false, backgroundColor: '#ffffff', useCORS: true },
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
    };

    if (window.html2pdf) {
        window.html2pdf().set(opt).from(element).outputPdf('blob').then(async (blob) => {
            element.style.display = originalDisplay;
            
            const formData = new FormData();
            formData.append("pdf", blob, `${invoice.invoice_number}.pdf`);
            
            try {
                const uploadRes = await fetch(`/api/invoices/${invoice.id}/upload-pdf`, {
                    method: "POST",
                    body: formData
                });
                if (uploadRes.ok) {
                    const result = await uploadRes.json();
                    console.log("PDF uploaded to cloud storage successfully:", result.pdf_url);
                    await loadInvoices();
                } else {
                    console.error("Failed to upload PDF:", uploadRes.statusText);
                }
            } catch (err) {
                console.error("Error uploading PDF:", err);
            }
        }).catch(err => {
            console.error("PDF generation error:", err);
            element.style.display = originalDisplay;
        });
    } else {
        element.style.display = originalDisplay;
    }
}

// -------------------------------------------------------------
// 6. OVERDUE RISK INSPECTOR & DETAIL MODAL
// -------------------------------------------------------------
async function openDetailModal(invoiceId) {
    try {
        const res = await fetch(`/api/invoices/${invoiceId}`);
        const inv = await res.json();
        selectedInvoiceForDetail = inv;

        const numElem = document.getElementById("detail-invoice-number");
        if (numElem) numElem.textContent = `Invoice ${inv.invoice_number} Inspector`;

        const risk = inv.risk;
        const history = inv.client_history;

        let riskBoxClass = "risk-explanation-box";
        if (risk.risk_level === "High") riskBoxClass += " high-risk";
        else if (risk.risk_level === "Medium") riskBoxClass += " medium-risk";

        let riskFillColor = "#10b981";
        if (risk.risk_level === "High") riskFillColor = "#ef4444";
        else if (risk.risk_level === "Medium") riskFillColor = "#f59e0b";

        const modalContent = document.getElementById("detail-modal-content");
        if (modalContent) {
            modalContent.innerHTML = `
                <div style="display: flex; justify-content: space-between; gap: 1rem; border-bottom: 1px solid var(--border-color); padding-bottom: 1rem;">
                    <div>
                        <h3 style="font-size: 1.2rem; color: var(--text-main);">${inv.client_name}</h3>
                        <p style="font-size: 0.85rem; color: var(--text-muted);">${inv.client_email || 'No email provided'}</p>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.4rem; font-weight: 700; color: var(--success-green);">${formatCurrency(inv.grand_total)}</div>
                        <span class="badge ${inv.status === 'PAID' ? 'badge-green' : (risk.is_overdue ? 'badge-red' : 'badge-amber')}">
                            ${risk.status_label}
                        </span>
                    </div>
                </div>

                ${inv.status === 'PENDING' ? `
                    <div class="${riskBoxClass}">
                        <div class="risk-header-row">
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <i class="fa-solid fa-shield-virus" style="font-size: 1.2rem; color: ${riskFillColor};"></i>
                                <strong>Overdue Risk Scoring Engine</strong>
                            </div>
                            <div style="font-family: var(--font-heading); font-size: 1.1rem; font-weight: 700;">
                                Score: <span style="color: ${riskFillColor};">${risk.risk_score} / 100</span> (${risk.risk_level} Risk)
                            </div>
                        </div>

                        <div class="score-meter-bar">
                            <div class="score-meter-fill" style="width: ${risk.risk_score}%; background: ${riskFillColor};"></div>
                        </div>

                        <div>
                            <strong style="font-size: 0.8rem; text-transform: uppercase; color: var(--text-muted);">Explainable Risk Drivers:</strong>
                            <ul class="risk-drivers-list">
                                ${risk.explanations.map(exp => `<li><i class="fa-solid fa-angle-right"></i> ${exp}</li>`).join("")}
                            </ul>
                        </div>

                        <div class="action-recommendation-card">
                            <strong>Recommended Action:</strong>
                            <p style="margin-top: 0.2rem; font-size: 0.85rem; color: var(--text-main);">${risk.recommended_action}</p>
                        </div>
                    </div>
                ` : `
                    <div class="risk-explanation-box" style="border-left-color: var(--success-green);">
                        <i class="fa-solid fa-circle-check" style="color: var(--success-green); font-size: 1.2rem;"></i>
                        <strong>Payment Settled</strong> - This invoice was fully paid on ${inv.payment_date}.
                    </div>
                `}

                <div>
                    <h4 style="font-size: 0.9rem; margin-bottom: 0.5rem; color: var(--text-muted);">Itemized Services</h4>
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Description</th>
                                <th>Hours</th>
                                <th>Rate (₹)</th>
                                <th>Total (₹)</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${inv.items.map(item => `
                                <tr>
                                    <td>${item.description}</td>
                                    <td>${item.hours} hrs</td>
                                    <td>₹${item.hourly_rate.toFixed(2)}</td>
                                    <td><strong>₹${item.amount.toFixed(2)}</strong></td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>

                <div style="background: rgba(15, 23, 42, 0.4); padding: 1rem; border-radius: var(--radius-sm); font-size: 0.85rem; display: flex; justify-content: space-between;">
                    <span><strong>Client History:</strong> ${history.paid_invoices_count} past paid invoices (${history.late_invoices_count} paid late)</span>
                    <span><strong>Avg Payment Delay:</strong> ${history.avg_delay_days} days</span>
                </div>
            `;
        }

        const markPaidBtn = document.getElementById("btn-mark-paid");
        if (markPaidBtn) markPaidBtn.style.display = inv.status === "PAID" ? "none" : "inline-flex";

        const detailModal = document.getElementById("detail-modal");
        if (detailModal) detailModal.classList.add("active");
    } catch (err) {
        console.error("Error opening detail modal:", err);
    }
}

function closeDetailModal() {
    const detailModal = document.getElementById("detail-modal");
    if (detailModal) detailModal.classList.remove("active");
}

async function markCurrentAsPaid() {
    if (!selectedInvoiceForDetail) return;
    await markAsPaidDirect(selectedInvoiceForDetail.id);
    closeDetailModal();
}

function shareCurrentInvoiceWhatsApp(invoiceId = null) {
    let invoice = null;
    if (invoiceId) {
        invoice = currentInvoiceList.find(i => i.id === invoiceId);
    } else {
        invoice = selectedInvoiceForDetail;
    }
    
    if (!invoice) return;
    
    let clientPhone = "";
    const client = registeredClientsList.find(c => c.client_name === invoice.client_name);
    if (client && client.client_whatsapp) {
        clientPhone = client.client_whatsapp.replace(/[^0-9]/g, '');
    }
    
    // Always use the public proxy route to bypass GCS IAM restrictions
    let link = window.location.origin + "/public/invoices/" + invoice.id + "/download-pdf";
    let message = `Hi ${invoice.client_name}, here is the invoice ${invoice.invoice_number} for the recent work: ${link} . Thank you!`;
    
    let waUrl = `https://wa.me/${clientPhone}?text=${encodeURIComponent(message)}`;
    window.open(waUrl, '_blank');
}

async function markAsPaidDirect(invoiceId) {
    try {
        const res = await fetch(`/api/invoices/${invoiceId}/mark-paid`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({})
        });
        if (res.ok) {
            await loadDashboardStats();
            await loadInvoices();
        } else {
            const data = await res.json();
            alert(data.error || "Failed to mark invoice as paid");
        }
    } catch (err) {
        console.error("Error marking as paid:", err);
    }
}

// -------------------------------------------------------------
// 7. CLIENT RISK PROFILES MODAL
// -------------------------------------------------------------
async function openClientHistoryModal() {
    try {
        const res = await fetch("/api/clients");
        const clients = await res.json();
        
        const tbody = document.getElementById("clients-table-body");
        if (!tbody) return;
        tbody.innerHTML = "";

        clients.forEach(c => {
            const tr = document.createElement("tr");
            const latePct = Math.round(c.late_payment_ratio * 100);
            
            tr.innerHTML = `
                <td><strong>${c.client_name}</strong></td>
                <td>${c.total_invoices}</td>
                <td>${c.paid_invoices_count}</td>
                <td>${c.late_invoices_count}</td>
                <td>
                    <span class="badge ${latePct > 50 ? 'badge-red' : (latePct > 0 ? 'badge-amber' : 'badge-green')}">
                        ${latePct}% late
                    </span>
                </td>
                <td>${c.avg_delay_days} days</td>
                <td><strong>${formatCurrency(c.outstanding_amount)}</strong></td>
            `;
            tbody.appendChild(tr);
        });

        const clientsModal = document.getElementById("clients-modal");
        if (clientsModal) clientsModal.classList.add("active");
    } catch (err) {
        console.error("Error loading client profiles:", err);
    }
}

function closeClientsModal() {
    const clientsModal = document.getElementById("clients-modal");
    if (clientsModal) clientsModal.classList.remove("active");
}

// -------------------------------------------------------------
// 8. PRINT & 1-CLICK PDF DOWNLOAD ENGINE
// -------------------------------------------------------------
async function printInvoice(invoiceId) {
    try {
        const res = await fetch(`/api/invoices/${invoiceId}`);
        const inv = await res.json();
        renderPrintableInvoice(inv);
        window.print();
    } catch (err) {
        console.error("Error fetching invoice for print:", err);
    }
}

function printCurrentInvoice() {
    if (selectedInvoiceForDetail) {
        renderPrintableInvoice(selectedInvoiceForDetail);
        window.print();
    }
}

async function downloadInvoicePDFDirect(invoiceId) {
    try {
        const res = await fetch(`/api/invoices/${invoiceId}`);
        const inv = await res.json();
        renderPrintableInvoice(inv);
        triggerPDFDownload(inv.invoice_number);
    } catch (err) {
        console.error("Error generating PDF:", err);
    }
}

function downloadCurrentInvoicePDF() {
    if (selectedInvoiceForDetail) {
        if (selectedInvoiceForDetail.pdf_url) {
            window.open(`/api/invoices/${selectedInvoiceForDetail.id}/download-pdf`, '_blank');
        } else {
            renderPrintableInvoice(selectedInvoiceForDetail);
            triggerPDFDownload(selectedInvoiceForDetail.invoice_number);
        }
    }
}

function triggerPDFDownload(invoiceNum) {
    const element = document.getElementById("printable-invoice");
    if (!element) return;
    element.style.display = "block";
    element.style.backgroundColor = "#ffffff";
    element.style.color = "#1e293b";
    
    const opt = {
        margin:       [0.4, 0.4, 0.4, 0.4],
        filename:     `${invoiceNum}_Invoice.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, logging: false, backgroundColor: '#ffffff', useCORS: true },
        jsPDF:        { unit: 'in', format: 'letter', orientation: 'portrait' }
    };

    if (window.html2pdf) {
        window.html2pdf().set(opt).from(element).save().then(() => {
            element.style.display = "none";
        }).catch(err => {
            console.error("PDF generation error:", err);
            element.style.display = "none";
        });
    } else {
        window.print();
        element.style.display = "none";
    }
}

function renderPrintableInvoice(inv) {
    const container = document.getElementById("printable-invoice");
    if (!container) return;
    container.innerHTML = `
        <div class="print-invoice-header">
            <div class="print-company">
                <h1>FREELANCE INVOICE</h1>
                <p>Professional Creative & Technical Services</p>
                <p style="font-size: 0.85rem; color: #555;">Issued By: ${currentUser ? currentUser.name : 'Freelancer'}</p>
            </div>
            <div class="print-inv-details">
                <h2>${inv.invoice_number}</h2>
                <p>Status: ${inv.status}</p>
            </div>
        </div>

        <div class="print-meta-grid">
            <div class="print-meta-box">
                <h4>Billed To:</h4>
                <p>${inv.client_name}</p>
                <p style="font-weight: normal; font-size: 0.9rem;">${inv.client_email || ''}</p>
            </div>
            <div class="print-meta-box">
                <h4>Invoice Date:</h4>
                <p>${inv.invoice_date}</p>
            </div>
            <div class="print-meta-box">
                <h4>Payment Due Date:</h4>
                <p>${inv.due_date}</p>
            </div>
        </div>

        <table class="print-table">
            <thead>
                <tr>
                    <th>Service Description</th>
                    <th style="text-align: center;">Hours</th>
                    <th style="text-align: right;">Hourly Rate</th>
                    <th style="text-align: right;">Amount</th>
                </tr>
            </thead>
            <tbody>
                ${inv.items.map(item => `
                    <tr>
                        <td>${item.description}</td>
                        <td style="text-align: center;">${item.hours}</td>
                        <td style="text-align: right;">₹${item.hourly_rate.toFixed(2)}</td>
                        <td style="text-align: right;"><strong>₹${item.amount.toFixed(2)}</strong></td>
                    </tr>
                `).join("")}
            </tbody>
        </table>

        <div class="print-totals">
            <div class="print-total-row">
                <span>Subtotal:</span>
                <span>₹${inv.subtotal.toFixed(2)}</span>
            </div>
            <div class="print-total-row">
                <span>Tax (${inv.tax_rate}%):</span>
                <span>₹${(inv.grand_total - inv.subtotal).toFixed(2)}</span>
            </div>
            <div class="print-total-row print-grand-total">
                <span>Grand Total:</span>
                <span>₹${inv.grand_total.toFixed(2)}</span>
            </div>
        </div>

        ${inv.notes ? `
            <div class="print-footer-notes">
                <strong>Payment Notes & Terms:</strong>
                <p>${inv.notes}</p>
            </div>
        ` : ''}
    `;
}

function formatCurrency(amount) {
    const val = parseFloat(amount || 0);
    return "₹" + val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// -------------------------------------------------------------
// FREELANCER WORK & SERVICES CATALOG MANAGERS
// -------------------------------------------------------------
async function loadUserServices() {
    try {
        const res = await fetch("/api/services");
        if (res.ok) {
            userServicesList = await res.json();
            renderServicesTable();
            renderDashboardServicesTable();
            updateServicesDatalist();
        }
    } catch (err) {
        console.error("Error loading services catalog:", err);
    }
}

function renderDashboardServicesTable() {
    const tbody = document.getElementById("dashboard-services-body");
    if (!tbody) return;
    if (!userServicesList || userServicesList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="3" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
                    No work items cataloged yet. Click "Manage Catalog" to add predefined work!
                </td>
            </tr>
        `;
        return;
    }
    tbody.innerHTML = userServicesList.map(srv => `
        <tr>
            <td><strong>${srv.title}</strong></td>
            <td><span class="badge badge-green">₹${parseFloat(srv.hourly_rate).toFixed(2)}/hr</span></td>
            <td>${srv.description || '<span style="color: var(--text-dim);">No description</span>'}</td>
        </tr>
    `).join("");
}

function updateServicesDatalist() {
    const datalist = document.getElementById("services-datalist");
    if (!datalist) return;
    datalist.innerHTML = userServicesList.map(srv => 
        `<option value="${srv.title}">₹${parseFloat(srv.hourly_rate).toFixed(2)}/hr ${srv.description ? '- ' + srv.description : ''}</option>`
    ).join("");
}


function openServicesModal() {
    resetServiceForm();
    renderServicesTable();
    const modal = document.getElementById("services-modal");
    if (modal) modal.classList.add("active");
}

function closeServicesModal() {
    const modal = document.getElementById("services-modal");
    if (modal) modal.classList.remove("active");
}

function resetServiceForm() {
    document.getElementById("service-edit-id").value = "";
    document.getElementById("service-title").value = "";
    document.getElementById("service-rate").value = "";
    document.getElementById("service-desc").value = "";
    document.getElementById("service-form-title").innerHTML = `<i class="fa-solid fa-plus"></i> Add Predefined Work Item / Service`;
    document.getElementById("btn-save-service").innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Save Work Item`;
    document.getElementById("btn-cancel-service-edit").style.display = "none";
}

function renderServicesTable() {
    const tbody = document.getElementById("services-table-body");
    if (!tbody) return;

    if (!userServicesList || userServicesList.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" style="text-align: center; color: var(--text-muted); padding: 1.5rem;">
                    No work items in your catalog yet. Add your standard services and hourly rates above!
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = userServicesList.map(srv => `
        <tr>
            <td><strong>${srv.title}</strong></td>
            <td><span class="badge badge-green">₹${parseFloat(srv.hourly_rate).toFixed(2)} / hr</span></td>
            <td>${srv.description || '<span style="color: var(--text-dim);">No description</span>'}</td>
            <td style="text-align: right;">
                <button class="btn btn-sm btn-secondary" onclick="editService(${srv.id})">
                    <i class="fa-solid fa-pen-to-square"></i> Edit
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteService(${srv.id})">
                    <i class="fa-solid fa-trash"></i> Delete
                </button>
            </td>
        </tr>
    `).join("");
}

async function handleSaveService(event) {
    event.preventDefault();
    const editId = document.getElementById("service-edit-id").value;
    const title = document.getElementById("service-title").value.trim();
    const hourly_rate = parseFloat(document.getElementById("service-rate").value) || 0;
    const description = document.getElementById("service-desc").value.trim();

    if (!title || hourly_rate <= 0) {
        alert("Please enter a valid Work Title and Hourly Rate.");
        return;
    }

    const payload = { title, hourly_rate, description };
    const url = editId ? `/api/services/${editId}` : "/api/services";
    const method = editId ? "PUT" : "POST";

    try {
        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            resetServiceForm();
            await loadUserServices();
        } else {
            const errData = await res.json();
            alert(errData.error || "Failed to save work item.");
        }
    } catch (err) {
        console.error("Save service error:", err);
        alert("Network error saving work item.");
    }
}

function editService(id) {
    const srv = userServicesList.find(s => s.id === id);
    if (!srv) return;
    document.getElementById("service-edit-id").value = srv.id;
    document.getElementById("service-title").value = srv.title;
    document.getElementById("service-rate").value = srv.hourly_rate;
    document.getElementById("service-desc").value = srv.description || "";
    document.getElementById("service-form-title").innerHTML = `<i class="fa-solid fa-pen-to-square"></i> Edit Work Item / Hourly Rate`;
    document.getElementById("btn-save-service").innerHTML = `<i class="fa-solid fa-floppy-disk"></i> Update Work Item`;
    document.getElementById("btn-cancel-service-edit").style.display = "inline-flex";
}

async function deleteService(id) {
    if (!confirm("Are you sure you want to remove this work item from your catalog?")) return;
    try {
        const res = await fetch(`/api/services/${id}`, { method: "DELETE" });
        if (res.ok) {
            await loadUserServices();
        } else {
            alert("Failed to delete work item.");
        }
    } catch (err) {
        console.error("Delete service error:", err);
    }
}

// -------------------------------------------------------------
// 10. NEW FEATURES: NLP DICTATION & CHART.JS
// -------------------------------------------------------------

function startDictation(targetId, btnElement) {
    if (window.hasOwnProperty('webkitSpeechRecognition')) {
        const recognition = new webkitSpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = "en-US";
        
        const originalHtml = btnElement.innerHTML;
        btnElement.innerHTML = `<i class="fa-solid fa-microphone-lines fa-fade" style="color: red;"></i> Listening...`;
        
        recognition.start();

        recognition.onresult = function(e) {
            const transcript = e.results[0][0].transcript;
            const targetElem = document.getElementById(targetId);
            if (targetElem) {
                targetElem.value = targetElem.value ? targetElem.value + " " + transcript : transcript;
            }
            recognition.stop();
            btnElement.innerHTML = originalHtml;
        };

        recognition.onerror = function(e) {
            console.error("Speech recognition error:", e.error);
            recognition.stop();
            btnElement.innerHTML = originalHtml;
        }
        
        recognition.onend = function() {
            btnElement.innerHTML = originalHtml;
        }
    } else {
        alert("Speech Recognition is not supported in your browser. Please try Chrome or Edge.");
    }
}

let dashboardChartInstance = null;

function renderDashboardGraph(billed, pending, overdue) {
    const ctx = document.getElementById('revenueChart');
    if (!ctx) return;
    
    if (dashboardChartInstance) {
        dashboardChartInstance.destroy();
    }
    
    const isDark = document.body.classList.contains("dark-theme");
    const textColor = isDark ? '#e2e8f0' : '#1e293b';
    const gridColor = isDark ? '#334155' : '#e2e8f0';
    
    dashboardChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Total Billed', 'Pending', 'Overdue'],
            datasets: [{
                label: 'Revenue Overview (₹)',
                data: [billed, pending, overdue],
                backgroundColor: [
                    'rgba(59, 130, 246, 0.7)',
                    'rgba(245, 158, 11, 0.7)',
                    'rgba(239, 68, 68, 0.7)'
                ],
                borderColor: [
                    'rgb(59, 130, 246)',
                    'rgb(245, 158, 11)',
                    'rgb(239, 68, 68)'
                ],
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: gridColor },
                    ticks: { color: textColor }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: textColor }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

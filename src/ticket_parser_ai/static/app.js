let parsedTicket = null;

const CATEGORIES = ["Comestibles", "Libreria", "Bebidas", "Utensilios", "Panaderia"];

// Preview image when selected
document.getElementById('image-file').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        const preview = document.getElementById('preview');
        preview.src = URL.createObjectURL(file);
        preview.style.display = 'block';
    }
});

// Function to delete a specific item row
function deleteRow(index) {
    if (!parsedTicket || !parsedTicket.items) return;
    
    // Remove item from array
    parsedTicket.items.splice(index, 1);
    
    // Re-render table with updated items
    renderItemsTable();
}

// Render items table and update totals
function renderItemsTable() {
    const tbody = document.querySelector('#items-table tbody');
    tbody.innerHTML = '';

    // Recalculate and update total amount
    const newTotal = parsedTicket.items.reduce((sum, item) => {
        return sum + (item.total_price || (item.quantity * item.unit_price));
    }, 0);
    document.getElementById('res-total').innerText = newTotal.toFixed(2);

    parsedTicket.items.forEach((item, index) => {
        const categoryOptions = CATEGORIES.map(cat => 
            `<option value="${cat}" ${cat === (item.category || "Comestibles") ? "selected" : ""}>${cat}</option>`
        ).join('');

        tbody.innerHTML += `
            <tr>
                <td>
                    <input type="text" class="product-name-input" data-index="${index}" value="${item.product_name || ''}">
                </td>
                <td>${item.quantity}</td>
                <td>$${item.unit_price}</td>
                <td>
                    <input type="number" class="margin-input" data-index="${index}" value="${item.profit_margin ? item.profit_margin * 100 : 40}" min="0" max="100" step="5">%
                </td>
                <td>
                    <select class="category-select" data-index="${index}">
                        ${categoryOptions}
                    </select>
                </td>
                <td style="text-align: center;">
                    <button type="button" class="delete-btn" onclick="deleteRow(${index})" title="Eliminar fila">🗑️</button>
                </td>
            </tr>`;
    });
}

// Process image analysis with API
document.getElementById('upload-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const status = document.getElementById('status');
    const btn = document.getElementById('parse-btn');

    status.innerText = 'Analyzing image with Vision LLM...';
    btn.disabled = true;

    const formData = new FormData();
    formData.append('file', document.getElementById('image-file').files[0]);
    formData.append('provider', document.getElementById('provider').value);

    try {
        const res = await fetch('/api/parse', { method: 'POST', body: formData });
        if (!res.ok) throw new Error(await res.text());

        parsedTicket = await res.json();
        document.getElementById('res-store').innerText = parsedTicket.store_name || 'N/A';

        renderItemsTable();

        document.getElementById('results').style.display = 'block';
        status.innerText = 'Analysis completed successfully!';
    } catch (err) {
        status.innerText = 'Error: ' + err.message;
    } finally {
        btn.disabled = false;
    }
});

// Save updated ticket data to Google Sheets
document.getElementById('save-btn').addEventListener('click', async () => {
    if (!parsedTicket) return;
    const status = document.getElementById('status');
    const btn = document.getElementById('save-btn');

    status.innerText = 'Saving to Google Sheets...';
    btn.disabled = true;

    const productNameInputs = document.querySelectorAll('.product-name-input');
    const marginInputs = document.querySelectorAll('.margin-input');
    const categorySelects = document.querySelectorAll('.category-select');

    const updatedItems = parsedTicket.items.map((item, idx) => {
        return {
            ...item,
            product_name: productNameInputs[idx].value.trim(),
            profit_margin: parseFloat(marginInputs[idx].value) / 100.0,
            category: categorySelects[idx].value
        };
    });

    const payload = {
        ticket: {
            ...parsedTicket,
            items: updatedItems
        }
    };

    try {
        const res = await fetch('/api/save-sheets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) throw new Error(await res.text());

        const data = await res.json();
        status.innerText = `Successfully added ${data.rows_added} items to Google Sheets!`;
    } catch (err) {
        status.innerText = 'Error saving to Google Sheets: ' + err.message;
    } finally {
        btn.disabled = false;
    }
});
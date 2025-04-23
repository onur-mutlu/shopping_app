from flask import request, jsonify, render_template_string
from app import app
from app.db import cursor, db
from app.logic import get_active_items, get_latest_carts

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Alışveriş Listesi</title>
    <meta charset="UTF-8">
</head>
<body>
    <h1>🛒 Aktif Alışveriş Listesi</h1>
<form id="deactivateForm">
    {% if active_items %}
        <ul>
        {% for item in active_items %}
            <li>
                <input type="checkbox" name="item" value="{{ item.id }}" />
                {{ item.name }}, {{ item.created_at.strftime('%H:%M %d.%m.%Y') }}
            </li>
        {% endfor %}
        </ul>
        <input type="number" id="amountInput" placeholder="Toplam Tutar (₺)" required />
        <button type="button" onclick="deactivateSelected()">Save Changes</button>
    {% else %}
        <p>Aktif ürün yok.</p>
    {% endif %}
</form>
    <h2>🛒 Son 3 Sepet</h2>
    {% if carts %}
        {% for cart_id, cart in carts.items() %}
            <div>
                <button onclick="toggleCart('cart{{ cart_id }}')">
                    Sepet #{{ cart_id }} – {{ cart.created_at.strftime('%H:%M %d.%m.%Y %H:%M') }} - {{ cart.total_amount }}₺
                </button>
                <ul id="cart{{ cart_id }}" style="display: none; margin-top: 5px;">
                    {% for item in cart.items_list %}
                        <li>{{ item.name }} ({{ item.created_at.strftime('%H:%M %d.%m.%Y') }})</li>
                    {% endfor %}
                </ul>
            </div>
        {% endfor %}
    {% else %}
        <p>Hiç sepet bulunamadı.</p>
    {% endif %}
</body>
<h2>➕ Yeni Ürün Ekle</h2>
<input type="text" id="itemInput" placeholder="Yeni ürün adı" />
<button onclick="addItem()">Ekle</button>

<script>
function addItem() {
    const itemName = document.getElementById("itemInput").value;
    if (!itemName) {
        alert("Ürün adı boş olamaz!");
        return;
    }

    fetch('/items', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ name: itemName })
    })
    .then(response => {
        if (response.ok) {
            location.reload();
        } else {
            alert("Ekleme başarısız!");
        }
    });
}
function deactivateSelected() {
     const checkboxes = document.querySelectorAll('input[name="item"]:checked');
    const ids = Array.from(checkboxes).map(cb => parseInt(cb.value));
    const amount = parseInt(document.getElementById("amountInput").value);

    if (ids.length === 0) {
        alert("Lütfen en az bir ürün seçin.");
        return;
    }

    if (!amount || isNaN(amount)) {
        alert("Lütfen geçerli bir toplam tutar girin.");
        return;
    }

    fetch('/items/deactivate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: ids, amount: amount })
    })
    .then(response => {
        if (response.ok) {
            location.reload();
        } else {
            alert("Güncelleme başarısız!");
        }
    });
}
function toggleCart(id) {
    const el = document.getElementById(id);
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
}
</script>
</html>"""

@app.route('/')
def show_list():
    active_items = get_active_items()
    carts = get_latest_carts()
    return render_template_string(HTML_TEMPLATE, active_items=active_items, carts=carts)

@app.route('/items', methods=['GET'])
def get_items():
    cursor.execute("SELECT * FROM items")
    return jsonify(cursor.fetchall())

@app.route('/items', methods=['POST'])
def add_item():
    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    cursor.execute("INSERT INTO items (name) VALUES (%s)", (name,))
    db.commit()
    return jsonify({'message': 'Item added'}), 201

@app.route('/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
    db.commit()
    return jsonify({'message': 'Item deleted'})

@app.route('/items', methods=['DELETE'])
def clear_items():
    cursor.execute("DELETE FROM items")
    db.commit()
    return jsonify({'message': 'All items cleared'})

@app.route('/items/deactivate', methods=['POST'])
def deactivate_items():

    

    data = request.get_json()
    ids = data.get('ids', [])
    if not ids or not all(isinstance(i, int) for i in ids):
        return jsonify({'error': 'Invalid item list'}), 400

    amount = data.get('amount')

    if amount is None or not isinstance(amount, int):
        return jsonify({'error': 'Amount is required and must be an integer'}), 400
        
    cursor.execute("INSERT INTO carts (total_amount) VALUES (%s)", (amount,))
    db.commit()
    cart_id = cursor.lastrowid

    for item_id in ids:
        cursor.execute("INSERT INTO cart_items (cart_id, item_id) VALUES (%s, %s)", (cart_id, item_id))

    format_strings = ','.join(['%s'] * len(ids))
    query = f"UPDATE items SET is_active = 0 WHERE id IN ({format_strings})"
    cursor.execute(query, tuple(ids))
    db.commit()

    return jsonify({'message': 'Items deactivated and added to cart', 'cart_id': cart_id})

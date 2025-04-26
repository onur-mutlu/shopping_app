from flask import request, jsonify, render_template_string, session, redirect
from app import app
from app.db import cursor, db
from app.logic import get_active_items, get_latest_carts
from flask_bcrypt import Bcrypt
from functools import wraps

bcrypt = Bcrypt(app)

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
<h2>🚪 Logout</h2>
<a href="/logout">Logout</a>

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

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
def show_list():
    user_id = session['user_id']

    cursor.execute("SELECT * FROM items WHERE is_active = 1 AND user_id = %s ORDER BY created_at DESC", (user_id,))
    active_items = cursor.fetchall()

    carts = get_latest_carts(user_id)

    return render_template_string(HTML_TEMPLATE, active_items=active_items, carts=carts)


@app.route('/items', methods=['GET'])
@login_required
def get_items():
    cursor.execute("SELECT * FROM items")
    return jsonify(cursor.fetchall())

@app.route('/items', methods=['POST'])
@login_required
def add_item():
    data = request.get_json()
    name = data.get('name')
    user_id = session['user_id']

    if not name:
        return jsonify({'error': 'Name is required'}), 400

    cursor.execute("INSERT INTO items (name, user_id, is_active) VALUES (%s, %s, 1)", (name, user_id))
    db.commit()
    return jsonify({'message': 'Item added'}), 201

@app.route('/items/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
    db.commit()
    return jsonify({'message': 'Item deleted'})

@app.route('/items', methods=['DELETE'])
@login_required
def clear_items():
    cursor.execute("DELETE FROM items")
    db.commit()
    return jsonify({'message': 'All items cleared'})

@app.route('/items/deactivate', methods=['POST'])
@login_required
def deactivate_items():
    user_id = session['user_id']
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids or not all(isinstance(i, int) for i in ids):
        return jsonify({'error': 'Invalid item list'}), 400

    amount = data.get('amount')

    if amount is None or not isinstance(amount, int):
        return jsonify({'error': 'Amount is required and must be an integer'}), 400
        
    cursor.execute("INSERT INTO carts (total_amount,user_id) VALUES (%s,%s)", (amount,user_id,))
    db.commit()
    cart_id = cursor.lastrowid

    for item_id in ids:
        cursor.execute("INSERT INTO cart_items (cart_id, item_id) VALUES (%s, %s)", (cart_id, item_id))

    format_strings = ','.join(['%s'] * len(ids))
    query = f"UPDATE items SET is_active = 0 WHERE id IN ({format_strings})"
    cursor.execute(query, tuple(ids))
    db.commit()

    return jsonify({'message': 'Items deactivated and added to cart', 'cart_id': cart_id})


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, hashed_password))
        db.commit()

        return redirect('/login')
    return render_template_string("""
        <h2>Sign Up</h2>
        <form method="POST">
            Kullanıcı Adı: <input type="text" name="username" required><br>
            Şifre        : <input type="password" name="password" required><br>
            <button type="submit">Sign Up</button>
        </form>
        <a href="/login">Hesabın varsa buradan giriş yap</a>
    """)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT id, password_hash FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            return redirect('/dashboard')
        else:
            return "Invalid credentials!"

    return render_template_string("""
        <h2>Login</h2>
        <form method="POST">
            Kullanıcı Adı: <input type="text" name="username" required><br>
            Şifre : <input type="password" name="password" required><br>
            <button type="submit">Giriş Yap</button>
        </form>
        <a href="/signup">Hesabın yok mu? Buradan Kaydol</a>
    """)





@app.route('/items')
@login_required
def items():
    user_id = session['user_id']
    cursor.execute("SELECT * FROM items WHERE user_id = %s", (user_id,))
    items = cursor.fetchall()
    return render_template('items.html', items=items)


@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect('/login')


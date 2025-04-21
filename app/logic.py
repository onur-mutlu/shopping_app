from datetime import datetime
from collections import defaultdict
from .db import cursor, db

def get_active_items():
    cursor.execute("SELECT * FROM items WHERE is_active = 1 ORDER BY created_at DESC")
    items = cursor.fetchall()
    for item in items:
        item['created_at'] = datetime.strptime(str(item['created_at']), "%Y-%m-%d %H:%M:%S")
    return items

def get_latest_carts(limit=3):
    cursor.execute("""
         SELECT c.id AS cart_id,
           c.created_at AS cart_created,
           i.name,
           i.id AS item_id,
           i.created_at AS item_created_at
        FROM carts c
        JOIN cart_items ci ON ci.cart_id = c.id
        JOIN items i ON i.id = ci.item_id
        ORDER BY c.created_at DESC, i.created_at DESC
    """)
    rows = cursor.fetchall()

    carts = defaultdict(lambda: {'created_at': None, 'items_list': []})
    for row in rows:
        cart_id = row['cart_id']
        if carts[cart_id]['created_at'] is None:
            carts[cart_id]['created_at'] = datetime.strptime(str(row['cart_created']), "%Y-%m-%d %H:%M:%S")
        carts[cart_id]['items_list'].append({
            'name': row['name'],
            'created_at': datetime.strptime(str(row['item_created_at']), "%Y-%m-%d %H:%M:%S")
        })

    return dict(list(carts.items())[:limit])

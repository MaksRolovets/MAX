from collections import defaultdict

# In-memory cart for dev: user_id -> item_id -> {name, price, qty}
CART = defaultdict(dict)

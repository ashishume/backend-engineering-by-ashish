from re import U


users = [
    {"user_id": 1, "name": "Ashish"},
    {"user_id": 2, "name": "Rahul"},
    {"user_id": 3, "name": "Priya"},
]

products = [
    {"product_id": 101, "product_name": "Laptop", "price": 50000},
    {"product_id": 102, "product_name": "Mouse", "price": 1000},
    {"product_id": 103, "product_name": "Keyboard", "price": 2000},
]
orders = [
    {"order_id": 1, "user_id": 1, "product_id": 101, "quantity": 1},
    {"order_id": 2, "user_id": 1, "product_id": 102, "quantity": 2},
    {"order_id": 3, "user_id": 2, "product_id": 103, "quantity": 1},
    {"order_id": 4, "user_id": 3, "product_id": 101, "quantity": 1},
]


def merge_data():
    users_mp = {}
    products_mp = {}
    for ch in users:
        users_mp[ch["user_id"]] = ch["name"]
    for ch in products:
        products_mp[ch["product_id"]] = ch

    res = {}
    for order in orders:
        user_id = order["user_id"]
        product_id = order["product_id"]

        amount = products_mp[product_id]["price"] * order["quantity"]

        if user_id in res:
            res[user_id]["total_spent"] += amount

        else:
            res[user_id] = {
                "user": users_mp[user_id],
                "total_spent": amount,
            }

    return list(res.values())


print(merge_data())

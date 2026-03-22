def trailing_take_profit(position, price):

    entry = position["entry_price"]
    highest = position.get("highest_price", entry)

    if price > highest:
        highest = price

    profit = (price - entry) / entry

    drop = (highest - price) / highest

    if profit > 0.02 and drop > 0.01:

        return True, highest

    return False, highest
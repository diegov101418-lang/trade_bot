balance = 1000

def get_balance():
    return balance

def update_balance(pnl):
    global balance
    balance += pnl
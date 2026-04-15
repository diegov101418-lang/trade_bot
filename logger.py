from datetime import datetime

LOG_FILE = "bot_log.txt"
ORDERS_LOG_FILE = "orders_log.txt"


def log(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line)

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"Error guardando log: {e}")


def log_order(msg):
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | {msg}"
    print(line)

    try:
        with open(ORDERS_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        print(f"Error guardando order log: {e}")
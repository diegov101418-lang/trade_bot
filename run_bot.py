import subprocess
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BOT_FILE = os.path.join(BASE_DIR, "bot.py")
DASHBOARD_FILE = os.path.join(BASE_DIR, "dashboard.py")

bot_process = None


def start_bot():

    global bot_process

    if bot_process and bot_process.poll() is None:
        return

    print("🤖 Iniciando bot...")

    bot_process = subprocess.Popen(
        [sys.executable, BOT_FILE],
        cwd=BASE_DIR
    )


def start_dashboard():

    print("🌐 Iniciando dashboard...")

    subprocess.Popen(
        [sys.executable, DASHBOARD_FILE],
        cwd=BASE_DIR
    )


def monitor():

    global bot_process

    while True:

        if not bot_process or bot_process.poll() is not None:
            print("⚠ Bot caído. Reiniciando...")
            start_bot()

        time.sleep(10)


def main():

    print("🚀 Trading System PRO (sin controller)")

    start_bot()
    start_dashboard()

    print("\n📊 Panel:")
    print("http://127.0.0.1:5000\n")

    monitor()


if __name__ == "__main__":
    main()
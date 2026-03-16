import subprocess
import time
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BOT_FILE = os.path.join(BASE_DIR, "bot.py")
DASHBOARD_FILE = os.path.join(BASE_DIR, "dashboard.py")

bot_process = None
dashboard_process = None


def start_bot():

    global bot_process

    print("🤖 Iniciando bot...")

    bot_process = subprocess.Popen(
        [sys.executable, BOT_FILE],
        cwd=BASE_DIR
    )


def start_dashboard():

    global dashboard_process

    print("🌐 Iniciando dashboard...")

    dashboard_process = subprocess.Popen(
        [sys.executable, DASHBOARD_FILE],
        cwd=BASE_DIR
    )


def monitor():

    global bot_process

    while True:

        if bot_process.poll() is not None:

            print("⚠ Bot detenido inesperadamente. Reiniciando...")

            start_bot()

        time.sleep(10)


def stop_all():

    print("⛔ Deteniendo sistema...")

    if bot_process:
        bot_process.terminate()

    if dashboard_process:
        dashboard_process.terminate()


def main():

    print("🚀 Iniciando Trading System")

    if not os.path.exists(BOT_FILE):
        print("❌ No se encontró bot.py")
        return

    if not os.path.exists(DASHBOARD_FILE):
        print("❌ No se encontró dashboard.py")
        return

    start_bot()
    start_dashboard()

    print("\n📊 Panel disponible en:")
    print("http://127.0.0.1:5000\n")

    try:

        monitor()

    except KeyboardInterrupt:

        stop_all()


if __name__ == "__main__":

    main()
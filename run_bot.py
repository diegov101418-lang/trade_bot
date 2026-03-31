import subprocess
import time
import os
import sys
import signal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

BOT_FILE = os.path.join(BASE_DIR, "bot.py")
DASHBOARD_FILE = os.path.join(BASE_DIR, "app.py")

bot_process = None
dashboard_process = None


# =========================
# BOT
# =========================
def start_bot():
    global bot_process

    if bot_process and bot_process.poll() is None:
        return

    print("🤖 Iniciando bot...")

    bot_process = subprocess.Popen(
        [sys.executable, BOT_FILE],
        cwd=BASE_DIR
    )


# =========================
# DASHBOARD
# =========================
def start_dashboard():
    global dashboard_process

    if dashboard_process and dashboard_process.poll() is None:
        return

    print("🌐 Iniciando dashboard...")

    dashboard_process = subprocess.Popen(
        [sys.executable, DASHBOARD_FILE],
        cwd=BASE_DIR
    )


# =========================
# MONITOR
# =========================
def monitor():
    global bot_process, dashboard_process

    bot_restart_count = 0
    dashboard_restart_count = 0

    while True:

        if not bot_process or bot_process.poll() is not None:
            print("⚠ Bot caído. Reiniciando...")
            start_bot()
            bot_restart_count += 1

        if not dashboard_process or dashboard_process.poll() is not None:
            print("⚠ Dashboard caído. Reiniciando...")
            start_dashboard()
            dashboard_restart_count += 1

        if bot_restart_count > 10:
            print("❌ Demasiados reinicios del bot. Revisar bot.")
            break

        if dashboard_restart_count > 10:
            print("❌ Demasiados reinicios del dashboard. Revisar app.py")
            break

        time.sleep(10)


# =========================
# STOP LIMPIO
# =========================
def stop_all():
    global bot_process, dashboard_process

    print("\n⛔ Cerrando sistema...")

    if bot_process and bot_process.poll() is None:
        bot_process.terminate()

    if dashboard_process and dashboard_process.poll() is None:
        dashboard_process.terminate()

    sys.exit(0)


# =========================
# MAIN
# =========================
def main():
    signal.signal(signal.SIGINT, lambda sig, frame: stop_all())

    print("🚀 Trading System PRO")

    start_bot()
    start_dashboard()

    print("\n📊 Panel:")
    print("http://127.0.0.1:5000\n")

    monitor()


if __name__ == "__main__":
    main()
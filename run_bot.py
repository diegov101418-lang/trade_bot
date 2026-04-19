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
is_shutting_down = False


# =========================
# BOT
# =========================
def start_bot():
    global bot_process

    if bot_process and bot_process.poll() is None:
        print("🤖 Bot ya está corriendo")
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
        print("🌐 Dashboard ya está corriendo")
        return

    print("🌐 Iniciando dashboard...")

    dashboard_process = subprocess.Popen(
        [sys.executable, DASHBOARD_FILE],
        cwd=BASE_DIR
    )


# =========================
# STOP PROCESO
# =========================
def stop_process(proc, name, timeout=10):
    if not proc or proc.poll() is not None:
        return

    print(f"⛔ Cerrando {name}...")

    try:
        proc.terminate()
        proc.wait(timeout=timeout)
        print(f"✅ {name} cerrado correctamente")
    except subprocess.TimeoutExpired:
        print(f"⚠ {name} no cerró a tiempo, forzando...")
        proc.kill()
        proc.wait()
        print(f"🔥 {name} cerrado por kill")
    except Exception as e:
        print(f"❌ Error cerrando {name}: {e}")


# =========================
# MONITOR
# =========================
def monitor():
    global bot_process, dashboard_process, is_shutting_down

    bot_restart_count = 0
    dashboard_restart_count = 0

    while not is_shutting_down:
        try:
            if not bot_process or bot_process.poll() is not None:
                if is_shutting_down:
                    break
                print("⚠ Bot caído. Reiniciando...")
                start_bot()
                bot_restart_count += 1

            if not dashboard_process or dashboard_process.poll() is not None:
                if is_shutting_down:
                    break
                print("⚠ Dashboard caído. Reiniciando...")
                start_dashboard()
                dashboard_restart_count += 1

            if bot_restart_count > 10:
                print("❌ Demasiados reinicios del bot. Revisar bot.py")
                break

            if dashboard_restart_count > 10:
                print("❌ Demasiados reinicios del dashboard. Revisar app.py")
                break

            time.sleep(10)

        except Exception as e:
            print(f"🔥 Error en monitor: {e}")
            time.sleep(5)


# =========================
# STOP LIMPIO
# =========================
def stop_all():
    global is_shutting_down, bot_process, dashboard_process

    if is_shutting_down:
        return

    is_shutting_down = True
    print("\n⛔ Cerrando sistema...")

    stop_process(bot_process, "bot")
    stop_process(dashboard_process, "dashboard")

    print("✅ Sistema detenido")
    sys.exit(0)


# =========================
# SIGNAL HANDLER
# =========================
def handle_signal(sig, frame):
    stop_all()


# =========================
# MAIN
# =========================
def main():
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    print("🚀 Trading System PRO")

    start_bot()
    start_dashboard()

    print("\n📊 Panel:")
    print("http://127.0.0.1:5000\n")

    monitor()


if __name__ == "__main__":
    main()
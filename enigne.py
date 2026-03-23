import time

from strategy.signals import generate_signal
from risk.risk_engine import validate_trade
from execution.broker import execute_trade
from portfolio.portfolio import Portfolio


portfolio = Portfolio()


def run():

    print("🚀 HEDGE FUND ENGINE STARTED")

    while True:

        signals = generate_signal()

        for signal in signals:

            # validar riesgo
            if not validate_trade(portfolio, signal):
                continue

            # ejecutar trade
            trade = execute_trade(signal)

            # actualizar portfolio
            portfolio.open_position(trade)

        time.sleep(10)
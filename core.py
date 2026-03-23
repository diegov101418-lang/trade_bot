# core.py

from strategies import run_strategies
from portfolio import allocate_capital
from risk_manager import global_risk_check

def run_system():

    strategies_signals = run_strategies()

    allocations = allocate_capital(strategies_signals)

    for signal in allocations:

        if global_risk_check(signal):
            execute_trade(signal)
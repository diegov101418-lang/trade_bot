let chartInstance = null;
let hourChartInstance = null;
let dayChartInstance = null;

function formatNumber(value, decimals = 2) {
    const num = Number(value || 0);
    return Number.isFinite(num) ? num.toFixed(decimals) : (0).toFixed(decimals);
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.innerText = value;
}

function setClass(id, className) {
    const el = document.getElementById(id);
    if (el) el.className = className;
}

function updateHeader(data) {
    setText("mode", data.mode || "-");
    setText("strategy", data.strategy || "-");

    const runningEl = document.getElementById("running");
    if (runningEl) {
        if (data.running) {
            runningEl.innerText = "ON";
            runningEl.className = "status-on";
        } else {
            runningEl.innerText = "OFF";
            runningEl.className = "status-off";
        }
    }

    if (data.time) {
        const date = new Date(data.time * 1000);
        setText("api_time", date.toLocaleTimeString());
    }
}

function updateSystemStatus(data) {
    const running = !!data.running;
    const mode = data.mode || "-";
    const strategy = data.strategy || "-";
    const nowText = data.time ? new Date(data.time * 1000).toLocaleTimeString() : "-";

    setText("system_bot_status", running ? "ACTIVO" : "PAUSADO");
    setClass("system_bot_status", running ? "value-green" : "value-red");

    setText("system_mode", mode.toUpperCase());
    setText("system_strategy", strategy);

    const maxTradesGuess = data.max_trades_per_day ?? 30;
    const tradesTodayGuess = data.daily_trades ?? Math.min(Number(data.performance?.trades || 0), maxTradesGuess);

    setText("system_daily_trades", `${tradesTodayGuess}/${maxTradesGuess}`);
    setText("system_last_update", nowText);
}

function updateCards(data) {
    const balance = Number(data.balance || 0);
    const free = Number(data.free_balance || 0);
    const used = Number(data.used_balance || 0);
    const equity = Number(data.equity || 0);
    const floatingPnl = Number(data.floating_pnl || 0);
    const exposurePct = Number(data.risk_pct || 0);
    const openPositionsCount = Number(data.open_positions_count || 0);

    const performance = data.performance || {};
    const stats = data.stats || {};
    const riskMetrics = data.risk_metrics || {};

    const totalRisk = Number(riskMetrics.total_open_risk || 0);
    const avgRisk = Number(riskMetrics.avg_risk_per_trade || 0);
    const realRiskPct = Number(riskMetrics.risk_pct_real || 0);

    const profit = Number(performance.profit || 0);
    const loss = Number(performance.loss || 0);
    const netResult = profit + loss;
    const netProfit = Number(performance.net_profit ?? netResult);

    const totalTrades = Number(performance.trades || stats.total || 0);
    const avgProfitTrade = Number(
        performance.avg_profit_per_trade ??
        (totalTrades > 0 ? netResult / totalTrades : 0)
    );

    const maxDrawdown = Number(performance.max_drawdown || 0);

    setText("balance", formatNumber(balance));
    setText("free_balance", formatNumber(free));
    setText("used_balance", formatNumber(used));
    setText("equity", formatNumber(equity));
    setText("floating_pnl", formatNumber(floatingPnl));
    setText("risk_pct", `${formatNumber(exposurePct)}%`);
    setText("open_positions_count", openPositionsCount);

    setText("total_risk", formatNumber(totalRisk));
    setText("avg_risk", formatNumber(avgRisk));
    setText("risk_real_pct", `${formatNumber(realRiskPct)}%`);

    setText("profit", formatNumber(profit));
    setText("loss", formatNumber(loss));
    setText("net_result", formatNumber(netResult));
    setText("net_profit", formatNumber(netProfit));
    setText("avg_profit_per_trade", formatNumber(avgProfitTrade));
    setText("max_drawdown", `${formatNumber(maxDrawdown, 2)}%`);

    [
        "balance", "free_balance", "used_balance", "equity", "floating_pnl",
        "risk_pct", "open_positions_count", "total_risk", "avg_risk",
        "risk_real_pct", "profit", "loss", "net_result", "net_profit",
        "avg_profit_per_trade", "max_drawdown"
    ].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.className = "";
    });

    const equityEl = document.getElementById("equity");
    const floatingPnlEl = document.getElementById("floating_pnl");
    const riskPctEl = document.getElementById("risk_pct");
    const realRiskPctEl = document.getElementById("risk_real_pct");
    const profitEl = document.getElementById("profit");
    const lossEl = document.getElementById("loss");
    const netEl = document.getElementById("net_result");
    const netProfitEl = document.getElementById("net_profit");
    const avgProfitTradeEl = document.getElementById("avg_profit_per_trade");
    const maxDrawdownEl = document.getElementById("max_drawdown");

    if (equityEl) {
        if (equity > balance) equityEl.classList.add("value-green");
        else if (equity < balance) equityEl.classList.add("value-red");
    }

    if (floatingPnlEl) {
        if (floatingPnl > 0) floatingPnlEl.classList.add("value-green");
        else if (floatingPnl < 0) floatingPnlEl.classList.add("value-red");
    }

    if (riskPctEl) {
        if (exposurePct < 20) riskPctEl.classList.add("value-green");
        else if (exposurePct < 50) riskPctEl.classList.add("value-yellow");
        else riskPctEl.classList.add("value-red");
    }

    if (realRiskPctEl) {
        if (realRiskPct < 3) realRiskPctEl.classList.add("value-green");
        else if (realRiskPct < 8) realRiskPctEl.classList.add("value-yellow");
        else realRiskPctEl.classList.add("value-red");
    }

    if (profitEl && profit > 0) profitEl.classList.add("value-green");
    if (lossEl && loss < 0) lossEl.classList.add("value-red");

    if (netEl) {
        if (netResult > 0) netEl.classList.add("value-green");
        else if (netResult < 0) netEl.classList.add("value-red");
    }

    if (netProfitEl) {
        if (netProfit > 0) netProfitEl.classList.add("value-green");
        else if (netProfit < 0) netProfitEl.classList.add("value-red");
    }

    if (avgProfitTradeEl) {
        if (avgProfitTrade > 0) avgProfitTradeEl.classList.add("value-green");
        else if (avgProfitTrade < 0) avgProfitTradeEl.classList.add("value-red");
    }

    if (maxDrawdownEl && maxDrawdown < 0) {
        maxDrawdownEl.classList.add("value-red");
    }

    setText("winrate", `${stats.winrate ?? 0}%`);
    setText("trades", performance.trades ?? stats.total ?? 0);
    setText("equity_info", `Historial de performance | Max DD: ${formatNumber(maxDrawdown, 2)}%`);
}

function pnlClass(value) {
    const v = Number(value || 0);
    if (v > 0) return "pnl-box pnl-pos";
    if (v < 0) return "pnl-box pnl-neg";
    return "pnl-box pnl-flat";
}

function updatePositions(positions) {
    const tbody = document.getElementById("positionsTable");
    const count = document.getElementById("positions_count");

    if (!tbody || !count) return;

    count.innerText = `${positions.length} posición${positions.length === 1 ? "" : "es"}`;

    if (!positions.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="muted">Sin posiciones</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = positions.map(pos => {
        const entry = Number(pos.entry_price || 0);
        const current = pos.current_price !== null && pos.current_price !== undefined
            ? Number(pos.current_price)
            : 0;
        const qty = Number(pos.quantity || 0);
        const capital = Number(pos.capital || 0);
        const pnl = Number(pos.pnl || 0);
        const pnlPct = Number(pos.pnl_pct || 0);

        return `
            <tr>
                <td>${pos.symbol ?? "-"}</td>
                <td>${formatNumber(entry, 6)}</td>
                <td>${current ? formatNumber(current, 6) : "-"}</td>
                <td>${formatNumber(qty, 6)}</td>
                <td>${formatNumber(capital, 2)}</td>
                <td><span class="${pnlClass(pnl)}">${formatNumber(pnl, 4)}</span></td>
                <td><span class="${pnlClass(pnlPct)}">${formatNumber(pnlPct, 2)}%</span></td>
            </tr>
        `;
    }).join("");
}

function updateTrades(trades) {
    const tbody = document.getElementById("tradesTable");
    if (!tbody) return;

    if (!trades.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="muted">Sin trades</td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = trades.slice().reverse().map(trade => {
        const resultRaw = trade.result ?? "";
        const pnl = Number(trade.pnl || 0);

        let resultText = "-";
        let resultClass = "muted";

        if (resultRaw === "1" || resultRaw === 1) {
            resultText = "WIN";
            resultClass = "green";
        } else if (resultRaw === "0" || resultRaw === 0) {
            resultText = "LOSS";
            resultClass = "red";
        }

        return `
            <tr>
                <td>${trade.symbol ?? "-"}</td>
                <td>${trade.rsi ?? "-"}</td>
                <td>${trade.volume ?? "-"}</td>
                <td>${trade.trend ?? "-"}</td>
                <td>${trade.momentum ?? "-"}</td>
                <td class="${resultClass}">${resultText}</td>
                <td>
                    <span class="${pnlClass(pnl)}">
                        ${trade.pnl !== undefined && trade.pnl !== "" ? formatNumber(trade.pnl, 4) : "-"}
                    </span>
                </td>
            </tr>
        `;
    }).join("");
}

function updateAlerts(data) {
    const container = document.getElementById("alertsList");
    if (!container) return;

    const alerts = [];

    const exposurePct = Number(data.risk_pct || 0);
    const floatingPnl = Number(data.floating_pnl || 0);
    const openPositions = Number(data.open_positions_count || 0);
    const winrate = Number(data.stats?.winrate || 0);
    const netProfit = Number(data.performance?.net_profit || (Number(data.performance?.profit || 0) + Number(data.performance?.loss || 0)));
    const realRiskPct = Number(data.risk_metrics?.risk_pct_real || 0);

    if (exposurePct >= 50) {
        alerts.push("⛔ Exposición alta: capital comprometido superior al 50%");
    } else if (exposurePct >= 20) {
        alerts.push("⚠ Exposición moderada: capital comprometido entre 20% y 50%");
    }

    if (realRiskPct >= 8) {
        alerts.push(`⛔ Riesgo real alto: ${formatNumber(realRiskPct, 2)}%`);
    } else if (realRiskPct >= 3) {
        alerts.push(`⚠ Riesgo real moderado: ${formatNumber(realRiskPct, 2)}%`);
    }

    if (openPositions >= 3) {
        alerts.push(`📂 Varias posiciones abiertas: ${openPositions}`);
    }

    if (floatingPnl < 0) {
        alerts.push(`📉 PnL flotante negativo: ${formatNumber(floatingPnl, 4)}`);
    } else if (floatingPnl > 0) {
        alerts.push(`📈 PnL flotante positivo: ${formatNumber(floatingPnl, 4)}`);
    }

    if (winrate < 40 && Number(data.performance?.trades || 0) > 30) {
        alerts.push(`⚠ Winrate bajo: ${formatNumber(winrate, 2)}%`);
    }

    if (netProfit > 0) {
        alerts.push(`✅ Sistema en ganancia neta: ${formatNumber(netProfit, 4)}`);
    } else if (netProfit < 0) {
        alerts.push(`⚠ Sistema en pérdida neta: ${formatNumber(netProfit, 4)}`);
    }

    if (!data.running) {
        alerts.push("⏸ Bot en pausa");
    }

    if (!alerts.length) {
        container.innerHTML = `<div class="alert-empty">Sin alertas por ahora</div>`;
        return;
    }

    container.innerHTML = alerts.map(alert => `
        <div class="alert-item">${alert}</div>
    `).join("");
}

function updateChart(history) {
    const canvas = document.getElementById("equityChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (chartInstance) {
        chartInstance.destroy();
    }

    chartInstance = new Chart(ctx, {
        type: "line",
        data: {
            labels: history.map((_, i) => i + 1),
            datasets: [{
                label: "Equity",
                data: history,
                borderColor: "#38bdf8",
                backgroundColor: "rgba(56, 189, 248, 0.12)",
                tension: 0.25,
                fill: true,
                pointRadius: 1.5
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: "#e5e7eb"
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: "#94a3b8" },
                    grid: { color: "#1f2937" }
                },
                y: {
                    ticks: { color: "#94a3b8" },
                    grid: { color: "#1f2937" }
                }
            }
        }
    });
}

function updateHourChart(hourAnalysis) {
    const canvas = document.getElementById("hourChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    const labels = hourAnalysis.map(item =>
        `${String(item.hour).padStart(2, "0")}:00`
    );

    const tradesData = hourAnalysis.map(item => Number(item.trades || 0));
    const winrateData = hourAnalysis.map(item => Number(item.winrate || 0));

    if (hourChartInstance) {
        hourChartInstance.destroy();
    }

    hourChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Trades",
                    data: tradesData,
                    backgroundColor: "rgba(56, 189, 248, 0.35)",
                    borderColor: "#38bdf8",
                    borderWidth: 1
                },
                {
                    label: "Winrate %",
                    data: winrateData,
                    type: "line",
                    borderColor: "#22c55e",
                    backgroundColor: "rgba(34, 197, 94, 0.15)",
                    tension: 0.25,
                    fill: false,
                    pointRadius: 2,
                    yAxisID: "y1"
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: {
                        color: "#e5e7eb"
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: "#94a3b8" },
                    grid: { color: "#1f2937" }
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: "#94a3b8" },
                    grid: { color: "#1f2937" },
                    title: {
                        display: true,
                        text: "Trades",
                        color: "#94a3b8"
                    }
                },
                y1: {
                    beginAtZero: true,
                    position: "right",
                    min: 0,
                    max: 100,
                    ticks: { color: "#94a3b8" },
                    grid: { drawOnChartArea: false },
                    title: {
                        display: true,
                        text: "Winrate %",
                        color: "#94a3b8"
                    }
                }
            }
        }
    });
}

async function loadData() {
    try {
        const res = await fetch("/api/data");
        const data = await res.json();

        console.log("DATA API:", data);

        updateHeader(data);
        updateSystemStatus(data);
        updateCards(data);
        updatePositions(data.positions || []);
        updateTrades(data.trades || []);
        updateAlerts(data);
        updateChart(data.history || []);
        updateHourChart(data.hour_analysis || []);
        updateDayChart(data.day_analysis || []);
        updateSessionChart(data.data.session_analysis || []);

    } catch (err) {
        console.error("Error cargando dashboard:", err);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadData();
    setInterval(loadData, 3000);
});
function updateDayChart(dayAnalysis) {
    const canvas = document.getElementById("dayChart");
    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    const labels = dayAnalysis.map(item => item.day);
    const tradesData = dayAnalysis.map(item => Number(item.trades || 0));
    const winrateData = dayAnalysis.map(item => Number(item.winrate || 0));

    if (dayChartInstance) {
        dayChartInstance.destroy();
    }

    dayChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Trades",
                    data: tradesData,
                    backgroundColor: "rgba(59, 130, 246, 0.3)",
                    borderColor: "#3b82f6",
                    borderWidth: 1
                },
                {
                    label: "Winrate %",
                    data: winrateData,
                    type: "line",
                    borderColor: "#22c55e",
                    tension: 0.25,
                    yAxisID: "y1"
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    ticks: { color: "#94a3b8" },
                    grid: { color: "#1f2937" }
                },
                y1: {
                    position: "right",
                    min: 0,
                    max: 100,
                    grid: { drawOnChartArea: false }
                }
            },
            plugins: {
                legend: {
                    labels: { color: "#e5e7eb" }
                }
            }
        }
    });
}
let sessionChartInstance = null;

function updateSessionChart(sessionAnalysis) {
    const canvas = document.getElementById("sessionChart");
    if (!canvas || !sessionAnalysis || sessionAnalysis.length === 0) return;

    const ctx = canvas.getContext("2d");

    const labels = sessionAnalysis.map(s => s.session.toUpperCase());
    const trades = sessionAnalysis.map(s => Number(s.trades || 0));
    const winrate = sessionAnalysis.map(s => Number(s.winrate || 0));
    const pnl = sessionAnalysis.map(s => Number(s.net_pnl || 0));

    if (sessionChartInstance) {
        sessionChartInstance.destroy();
    }

    sessionChartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [
                {
                    label: "Trades",
                    data: trades,
                    backgroundColor: "rgba(56, 189, 248, 0.4)",
                    borderColor: "#38bdf8",
                    borderWidth: 1
                },
                {
                    label: "Winrate %",
                    data: winrate,
                    type: "line",
                    borderColor: "#22c55e",
                    tension: 0.25,
                    yAxisID: "y1"
                },
                {
                    label: "PnL",
                    data: pnl,
                    type: "line",
                    borderColor: "#f59e0b",
                    tension: 0.25,
                    yAxisID: "y2"
                }
            ]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    labels: { color: "#e5e7eb" }
                }
            },
            scales: {
                x: {
                    ticks: { color: "#94a3b8" },
                    grid: { color: "#1f2937" }
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: "#94a3b8" },
                    title: {
                        display: true,
                        text: "Trades",
                        color: "#94a3b8"
                    }
                },
                y1: {
                    position: "right",
                    min: 0,
                    max: 100,
                    ticks: { color: "#22c55e" },
                    grid: { drawOnChartArea: false },
                    title: {
                        display: true,
                        text: "Winrate %",
                        color: "#22c55e"
                    }
                },
                y2: {
                    position: "right",
                    ticks: { color: "#f59e0b" },
                    grid: { drawOnChartArea: false },
                    title: {
                        display: true,
                        text: "PnL",
                        color: "#f59e0b"
                    }
                }
            }
        }
    });
}
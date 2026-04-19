document.addEventListener("DOMContentLoaded", () => {
    let currentSymbol = "BTCUSDT";
    let selectedPositionSymbol = null;
    let selectedTrade = null;

    let entryLine = null;
    let stopLine = null;
    let tpLine = null;
    let partialLine = null;

    const chartElement = document.getElementById("chart");

    const chart = LightweightCharts.createChart(chartElement, {
        width: chartElement.clientWidth,
        height: 560,
        layout: {
            background: { color: "#0f172a" },
            textColor: "#d1d5db",
        },
        grid: {
            vertLines: { color: "#1f2937" },
            horzLines: { color: "#1f2937" },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: "#374151",
            scaleMargins: {
                top: 0.08,
                bottom: 0.08,
            },
        },
        timeScale: {
            borderColor: "#374151",
            timeVisible: true,
            secondsVisible: false,
            rightOffset: 12,
            barSpacing: 10,
        },
    });

    const candleSeries = chart.addCandlestickSeries({
        upColor: "#22c55e",
        downColor: "#ef4444",
        borderUpColor: "#22c55e",
        borderDownColor: "#ef4444",
        wickUpColor: "#22c55e",
        wickDownColor: "#ef4444",
    });

    const ma50Series = chart.addLineSeries({
        color: "#facc15",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
    });

    const ma200Series = chart.addLineSeries({
        color: "#38bdf8",
        lineWidth: 2,
        priceLineVisible: false,
        lastValueVisible: false,
    });

    const scaleHelperSeries = chart.addLineSeries({
        color: "rgba(0,0,0,0)",
        lineWidth: 1,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
    });

    const toggleBot = document.getElementById("toggle-bot");
    const toggleMode = document.getElementById("toggle-mode");
    const aiLevelSelect = document.getElementById("ai-level");
    const aiLevelBadge = document.getElementById("ai-level-badge");

    toggleBot?.addEventListener("change", async () => {
        const endpoint = toggleBot.checked ? "/start" : "/stop";
        await fetch(endpoint);
    });

    toggleMode?.addEventListener("change", async () => {
        const endpoint = toggleMode.checked ? "/mode/real" : "/mode/demo";
        await fetch(endpoint);
    });

    aiLevelSelect?.addEventListener("change", () => {
        updateAiLevelBadge(aiLevelSelect.value);
    });

    function formatReason(reason) {
        const map = {
            ok: "Entrada válida",
            no_signal: "Sin señal",
            low_liquidity: "Baja liquidez",
            cooldown: "Cooldown activo",
            low_winrate: "Winrate bajo",
            risk_limits: "Límite de riesgo",
            no_entry: "No cumple condiciones",
        };
        return map[reason] || reason;
    }

    function updateAiLevelBadge(level) {
        if (!aiLevelBadge) return;

        const normalized = String(level || "medium").toLowerCase();
        const labels = {
            off: "NADA",
            low: "POCO",
            medium: "MEDIO",
            high: "MUCHO",
        };

        aiLevelBadge.innerText = labels[normalized] || "MEDIO";

        if (normalized === "off") aiLevelBadge.style.color = "#94a3b8";
        else if (normalized === "low") aiLevelBadge.style.color = "#22c55e";
        else if (normalized === "medium") aiLevelBadge.style.color = "#facc15";
        else aiLevelBadge.style.color = "#ef4444";
    }

    function animateNumber(el, from, to, options = {}) {
        if (!el) return;

        const {
            duration = 450,
            decimals = 2,
            suffix = "",
        } = options;

        const start = performance.now();
        const change = to - from;

        function easeOutCubic(t) {
            return 1 - Math.pow(1 - t, 3);
        }

        function frame(now) {
            const elapsed = now - start;
            const progress = Math.min(elapsed / duration, 1);
            const eased = easeOutCubic(progress);

            const current = from + change * eased;
            el.innerText = current.toFixed(decimals) + suffix;

            if (progress < 1) {
                requestAnimationFrame(frame);
            } else {
                el.innerText = to.toFixed(decimals) + suffix;
            }
        }

        requestAnimationFrame(frame);
    }

    function setAnimatedText(elementId, value, color = null, suffix = "") {
        const el = document.getElementById(elementId);
        if (!el) return;

        const num = Number(value) || 0;
        const previousRaw = el.dataset.prevValue;
        const previous = previousRaw !== undefined ? Number(previousRaw) : null;

        el.dataset.prevValue = num;

        if (color) {
            el.style.color = color;
        }

        el.classList.remove("flash-up", "flash-down", "flash-neutral");
        void el.offsetWidth;

        if (previous === null || Number.isNaN(previous)) {
            el.innerText = `${num}${suffix}`;
            el.classList.add("flash-neutral");
            return;
        }

        animateNumber(el, previous, num, {
            duration: 400,
            decimals: 0,
            suffix,
        });

        if (num > previous) el.classList.add("flash-up");
        else if (num < previous) el.classList.add("flash-down");
    }

    function setColoredValue(elementId, value, isPercent = false) {
        const el = document.getElementById(elementId);
        if (!el) return;

        const num = Number(value) || 0;
        const previousRaw = el.dataset.prevValue;
        const previous = previousRaw !== undefined ? Number(previousRaw) : null;

        el.dataset.prevValue = num;

        if (num > 0) el.style.color = "#22c55e";
        else if (num < 0) el.style.color = "#ef4444";
        else el.style.color = "#e5e7eb";

        el.classList.remove("flash-up", "flash-down", "flash-neutral");
        void el.offsetWidth;

        if (previous === null || Number.isNaN(previous)) {
            el.innerText = isPercent ? `${num.toFixed(2)}%` : num.toFixed(2);
            el.classList.add("flash-neutral");
            return;
        }

        animateNumber(el, previous, num, {
            duration: 500,
            decimals: 2,
            suffix: isPercent ? "%" : "",
        });

        if (num > previous) el.classList.add("flash-up");
        else if (num < previous) el.classList.add("flash-down");
    }

    function setAnimatedBalance(value) {
        const el = document.getElementById("balance");
        if (!el) return;

        const num = Number(value) || 0;
        const previousRaw = el.dataset.prevValue;
        const previous = previousRaw !== undefined ? Number(previousRaw) : null;

        el.dataset.prevValue = num;

        el.classList.remove("balance-up", "balance-down", "balance-idle");
        void el.offsetWidth;

        if (previous === null || Number.isNaN(previous)) {
            el.innerText = num.toFixed(2);
            el.classList.add("balance-idle");
            return;
        }

        animateNumber(el, previous, num, {
            duration: 700,
            decimals: 2,
        });

        if (num > previous) el.classList.add("balance-up");
        else if (num < previous) el.classList.add("balance-down");
        else {
            el.classList.add("balance-idle");
            return;
        }

        setTimeout(() => {
            el.classList.remove("balance-up", "balance-down");
            el.classList.add("balance-idle");
        }, 1200);
    }

    function clearTradeLines() {
        if (entryLine) {
            candleSeries.removePriceLine(entryLine);
            entryLine = null;
        }
        if (stopLine) {
            candleSeries.removePriceLine(stopLine);
            stopLine = null;
        }
        if (tpLine) {
            candleSeries.removePriceLine(tpLine);
            tpLine = null;
        }
        if (partialLine) {
            candleSeries.removePriceLine(partialLine);
            partialLine = null;
        }
    }

    function resetTradeSelection() {
        selectedTrade = null;
        scaleHelperSeries.setData([]);
        candleSeries.setMarkers([]);
        clearTradeLines();
    }

    function renderPositionLines(positions) {
        clearTradeLines();

        if (!positions || positions.length === 0) return;

        const selectedPos = positions.find((p) => p.symbol === currentSymbol) || positions[0];
        if (!selectedPos) return;

        const entry = parseFloat(selectedPos.entry_price || 0);
        const stop = parseFloat(selectedPos.stop_loss || 0);
        const tp = parseFloat(selectedPos.take_profit || 0);

        if (entry > 0) {
            entryLine = candleSeries.createPriceLine({
                price: entry,
                color: "#3b82f6",
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Solid,
                axisLabelVisible: true,
                title: "ENTRY",
            });
        }

        if (stop > 0) {
            stopLine = candleSeries.createPriceLine({
                price: stop,
                color: "#ef4444",
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                axisLabelVisible: true,
                title: "SL",
            });
        }

        if (tp > 0) {
            tpLine = candleSeries.createPriceLine({
                price: tp,
                color: "#22c55e",
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                axisLabelVisible: true,
                title: "TP",
            });
        }
    }

    function renderSelectedTradeMarker(trade) {
        if (!trade || !trade.timestamp) {
            candleSeries.setMarkers([]);
            return;
        }

        const markers = [];
        const entryTime = parseInt(trade.timestamp);

        if (Number.isFinite(entryTime)) {
            markers.push({
                time: entryTime,
                position: "belowBar",
                color: "#3b82f6",
                shape: "circle",
                text: "ENTRY",
            });
        }

        if (trade.partial_timestamp) {
            const partialTime = parseInt(trade.partial_timestamp);
            if (Number.isFinite(partialTime)) {
                markers.push({
                    time: partialTime,
                    position: "aboveBar",
                    color: "#facc15",
                    shape: "circle",
                    text: "PARTIAL",
                });
            }
        }

        if (trade.exit_timestamp) {
            const exitTime = parseInt(trade.exit_timestamp);
            if (Number.isFinite(exitTime)) {
                const pnl = parseFloat(trade.pnl_net ?? trade.pnl ?? 0);
                const isWin = pnl > 0;

                markers.push({
                    time: exitTime,
                    position: "aboveBar",
                    color: isWin ? "#22c55e" : "#ef4444",
                    shape: "arrowDown",
                    text: isWin ? "TP" : "SL",
                });
            }
        }

        candleSeries.setMarkers(markers);
    }

    function renderSelectedTradeLines(trade) {
        clearTradeLines();
        scaleHelperSeries.setData([]);

        if (!trade) return;

        const entry = parseFloat(trade.entry_price || 0);
        const stop = parseFloat(trade.stop_loss || 0);
        const tp = parseFloat(trade.take_profit || 0);
        const partial = parseFloat(trade.partial_price || 0);

        const prices = [entry, stop, tp, partial].filter(
            (v) => Number.isFinite(v) && v > 0
        );

        if (entry > 0) {
            entryLine = candleSeries.createPriceLine({
                price: entry,
                color: "#3b82f6",
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Solid,
                axisLabelVisible: true,
                title: "ENTRY",
            });
        }

        if (stop > 0) {
            stopLine = candleSeries.createPriceLine({
                price: stop,
                color: "#ef4444",
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                axisLabelVisible: true,
                title: "SL",
            });
        }

        if (tp > 0) {
            tpLine = candleSeries.createPriceLine({
                price: tp,
                color: "#22c55e",
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                axisLabelVisible: true,
                title: "TP",
            });
        }

        if (partial > 0) {
            partialLine = candleSeries.createPriceLine({
                price: partial,
                color: "#facc15",
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dotted,
                axisLabelVisible: true,
                title: "PARTIAL",
            });
        }

        if (prices.length > 0 && trade.timestamp) {
            const entryTime = parseInt(trade.timestamp);

            if (Number.isFinite(entryTime)) {
                const helperData = prices.map((price) => ({
                    time: entryTime,
                    value: price,
                }));
                scaleHelperSeries.setData(helperData);
            }
        }
    }

    function renderEquity(history) {
        const canvas = document.getElementById("equityChart");
        if (!canvas) return;

        const ctx = canvas.getContext("2d");
        const parentWidth = canvas.parentElement.clientWidth - 20;

        canvas.width = parentWidth;
        canvas.height = 165;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (!history || history.length < 2) {
            ctx.fillStyle = "#94a3b8";
            ctx.font = "14px Arial";
            ctx.fillText("Sin datos suficientes", 20, 30);
            return;
        }

        const padding = 20;
        const w = canvas.width - padding * 2;
        const h = canvas.height - padding * 2;

        const minVal = Math.min(...history);
        const maxVal = Math.max(...history);
        const range = maxVal - minVal || 1;

        const first = history[0];
        const last = history[history.length - 1];

        ctx.strokeStyle = last >= first ? "#22c55e" : "#ef4444";
        ctx.lineWidth = 2;
        ctx.beginPath();

        history.forEach((value, i) => {
            const x = padding + (i / (history.length - 1)) * w;
            const y = padding + h - ((value - minVal) / range) * h;

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });

        ctx.stroke();
    }

    function renderPositions(positions) {
        const container = document.getElementById("positions");
        if (!container) return;

        container.innerHTML = "";

        if (!positions || positions.length === 0) {
            container.innerHTML = "<div class='position'>Sin posiciones abiertas</div>";
            return;
        }

        positions.forEach((p) => {
            const pnlGross = Number(p.pnl_gross ?? p.pnl ?? 0);
            const pnlNet = Number(p.pnl_net ?? pnlGross);
            const feeTotal = Number(p.fee_total_est ?? 0);
            const colorNet = pnlNet > 0 ? "#22c55e" : pnlNet < 0 ? "#ef4444" : "#e5e7eb";

            const stopText =
                p.stop_loss != null && p.stop_loss !== ""
                    ? Number(p.stop_loss).toFixed(4)
                    : "-";

            const tpText =
                p.take_profit != null && p.take_profit !== ""
                    ? Number(p.take_profit).toFixed(4)
                    : "-";

            const entryText =
                p.entry_price != null && p.entry_price !== ""
                    ? Number(p.entry_price).toFixed(4)
                    : "-";

            const div = document.createElement("div");
            div.className = "position";
            div.style.cursor = "pointer";
            div.style.marginBottom = "8px";

            if (p.symbol === currentSymbol && !selectedTrade) {
                div.style.background = "rgba(59,130,246,0.12)";
                div.style.border = "1px solid #3b82f6";
            } else {
                div.style.background = "rgba(15,23,42,0.5)";
            }

            div.innerHTML = `
                <strong>${p.symbol}</strong><br>
                Entry: ${entryText}<br>
                SL: ${stopText}<br>
                TP: ${tpText}<br>
                Gross: ${pnlGross.toFixed(4)}<br>
                Fees est: ${feeTotal.toFixed(4)}<br>
                <span style="color:${colorNet}">Net: ${pnlNet.toFixed(4)}</span>
            `;

            div.addEventListener("click", async () => {
                selectedPositionSymbol = p.symbol;
                currentSymbol = p.symbol;
                resetTradeSelection();

                await loadChart(currentSymbol);
                renderPositions(positions);
                renderPositionLines(positions);
            });

            container.appendChild(div);
        });
    }

    function getTradeStatus(t) {
        const rawResult = String(t.result ?? "").trim();
        const pnlNum = Number(t.pnl_net ?? t.pnl ?? 0);

        if (rawResult === "" || rawResult.toLowerCase() === "open") return "open";
        if (rawResult === "1") return "win";
        if (rawResult === "0") return "loss";
        if (pnlNum > 0) return "win";
        if (pnlNum < 0) return "loss";
        return "open";
    }

    function buildTradeRow(t, statusText) {
        const symbol = t.symbol ?? "-";
        const pnlValueRaw = String(t.pnl_net ?? t.pnl ?? "").trim();
        const pnlNum = pnlValueRaw === "" ? 0 : Number(pnlValueRaw);
        const pnlText = pnlValueRaw === "" ? "-" : pnlNum.toFixed(4);
        const strategy = t.strategy_name ?? "-";
        const fee = Number(t.fee_total || 0).toFixed(4);

        const tr = document.createElement("tr");
        tr.style.cursor = "pointer";

        tr.innerHTML = `
            <td>${symbol}</td>
            <td>${statusText}</td>
            <td>${pnlText}</td>
            <td>${strategy}</td>
            <td>${fee}</td>
        `;

        if (statusText === "WIN") tr.style.color = "#22c55e";
        else if (statusText === "LOSS") tr.style.color = "#ef4444";
        else tr.style.color = "#facc15";

        tr.addEventListener("click", async () => {
            selectedPositionSymbol = null;
            selectedTrade = t;
            currentSymbol = symbol;

            await loadChart(currentSymbol);
            renderSelectedTradeMarker(selectedTrade);
            renderSelectedTradeLines(selectedTrade);
        });

        return tr;
    }

    function renderTrades(trades) {
        const summaryContainer = document.getElementById("trade-summary-list");
        const winsTbody = document.querySelector("#wins-table tbody");
        const lossesTbody = document.querySelector("#losses-table tbody");

        if (!summaryContainer || !winsTbody || !lossesTbody) return;

        summaryContainer.innerHTML = "";
        winsTbody.innerHTML = "";
        lossesTbody.innerHTML = "";

        if (!trades || trades.length === 0) {
            summaryContainer.innerHTML = "<div class='position'>Sin trades recientes</div>";

            const emptyWin = document.createElement("tr");
            emptyWin.innerHTML = `<td colspan="5">Sin wins</td>`;
            winsTbody.appendChild(emptyWin);

            const emptyLoss = document.createElement("tr");
            emptyLoss.innerHTML = `<td colspan="5">Sin losses</td>`;
            lossesTbody.appendChild(emptyLoss);
            return;
        }

        const recentTrades = trades.slice(-18).reverse();

        let winCount = 0;
        let lossCount = 0;

        recentTrades.forEach((t) => {
            const symbol = t.symbol ?? "-";
            const status = getTradeStatus(t);

            const summaryItem = document.createElement("div");
            summaryItem.className = "trade-summary-item";
            summaryItem.style.cursor = "pointer";

            let badgeText = "OPEN";
            if (status === "win") badgeText = "WIN";
            else if (status === "loss") badgeText = "LOSS";

            summaryItem.innerHTML = `
                <span class="trade-summary-symbol">${symbol}</span>
                <span class="trade-summary-badge ${status}">${badgeText}</span>
            `;

            summaryItem.addEventListener("click", async () => {
                selectedPositionSymbol = null;
                selectedTrade = t;
                currentSymbol = symbol;

                await loadChart(currentSymbol);
                renderSelectedTradeMarker(selectedTrade);
                renderSelectedTradeLines(selectedTrade);
            });

            summaryContainer.appendChild(summaryItem);

            if (status === "win") {
                winsTbody.appendChild(buildTradeRow(t, "WIN"));
                winCount++;
            }

            if (status === "loss") {
                lossesTbody.appendChild(buildTradeRow(t, "LOSS"));
                lossCount++;
            }
        });

        if (winCount === 0) {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td colspan="5">Sin wins recientes</td>`;
            winsTbody.appendChild(tr);
        }

        if (lossCount === 0) {
            const tr = document.createElement("tr");
            tr.innerHTML = `<td colspan="5">Sin losses recientes</td>`;
            lossesTbody.appendChild(tr);
        }
    }

    function renderAlerts(alerts) {
        const container = document.getElementById("alerts");
        if (!container) return;

        container.innerHTML = "";

        if (!alerts || alerts.length === 0) {
            container.innerHTML = "Sin alertas";
            return;
        }

        alerts.forEach((a) => {
            const div = document.createElement("div");
            div.className = "position";

            let color = "#e5e7eb";
            const text = String(a).toLowerCase();

            if (text.includes("positivo") || text.includes("ganancia") || text.includes("profit")) {
                color = "#22c55e";
            } else if (
                text.includes("riesgo") ||
                text.includes("pérdida") ||
                text.includes("perdida") ||
                text.includes("bajo")
            ) {
                color = "#ef4444";
            } else if (text.includes("varias") || text.includes("moderado")) {
                color = "#facc15";
            }

            div.style.color = color;
            div.textContent = a;
            container.appendChild(div);
        });
    }

    function renderDecisions(decisions) {
        const container = document.getElementById("decisions");
        if (!container) return;

        container.innerHTML = "";

        if (!decisions || decisions.length === 0) {
            container.innerHTML = "<div class='position'>Sin decisiones recientes</div>";
            return;
        }

        decisions.forEach((d) => {
            const div = document.createElement("div");
            div.className = "position";

            const decision = String(d.decision || "SKIP").toUpperCase();
            const symbol = d.symbol || "-";
            const confidence = Number(d.confidence || 0).toFixed(2);
            const liquidity = d.liquidity || "-";
            const reason = formatReason(d.reason || "-");

            const time = d.time
                ? new Date(d.time * 1000).toLocaleTimeString()
                : "--:--";

            let color = "#facc15";
            if (decision === "BUY") color = "#22c55e";
            else if (decision === "SELL") color = "#38bdf8";

            div.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <strong style="font-size:14px;">${symbol}</strong>
                    <span style="
                        background:${color}22;
                        color:${color};
                        padding:2px 8px;
                        border-radius:999px;
                        font-size:11px;
                        font-weight:700;
                    ">
                        ${decision}
                    </span>
                </div>

                <div style="font-size:12px; color:#94a3b8; display:flex; justify-content:space-between;">
                    <span>Conf: ${confidence}</span>
                    <span>${time}</span>
                </div>

                <div style="font-size:12px; margin-top:4px;">
                    <span style="color:#94a3b8;">Liq:</span> ${liquidity}
                </div>

                <div style="
                    font-size:12px;
                    margin-top:4px;
                    color:${d.reason === "ok" ? "#22c55e" : "#facc15"};
                ">
                    ${reason}
                </div>
            `;

            container.appendChild(div);
        });
    }

    async function loadChart(symbol = currentSymbol) {
        try {
            const res = await fetch(`/api/chart/${symbol}`);
            if (!res.ok) {
                console.error("API chart error:", res.status);
                return;
            }

            const data = await res.json();

            // limpiar siempre antes de cargar nuevo símbolo
            candleSeries.setData([]);
            ma50Series.setData([]);
            ma200Series.setData([]);
            scaleHelperSeries.setData([]);
            candleSeries.setMarkers([]);
            clearTradeLines();

            if (!data.candles || data.candles.length === 0) {
                const symbolEl = document.getElementById("symbol");
                const priceEl = document.getElementById("price");

                if (symbolEl) symbolEl.innerText = symbol;
                if (priceEl) priceEl.innerText = "Sin data";
                return;
            }

            candleSeries.setData(data.candles);
            ma50Series.setData(data.ma50 || []);
            ma200Series.setData(data.ma200 || []);

            const lastCandle = data.candles[data.candles.length - 1];
            const symbolEl = document.getElementById("symbol");
            const priceEl = document.getElementById("price");

            if (lastCandle && symbolEl) symbolEl.innerText = symbol;
            if (lastCandle && priceEl) priceEl.innerText = Number(lastCandle.close).toFixed(2);

            chart.timeScale().fitContent();
        } catch (err) {
            console.error("Error chart:", err);
        }
    }

    async function loadTodayStats() {
        try {
            const res = await fetch("/api/stats/today");
            if (!res.ok) {
                console.error("API today stats error:", res.status);
                return;
            }

            const data = await res.json();

            setAnimatedText("wins", data.wins ?? 0, "#22c55e");
            setAnimatedText("losses", data.losses ?? 0, "#ef4444");
            setColoredValue("daily-net", data.pnl_net ?? 0);
            setAnimatedText("daily-trades", data.trades ?? 0, "#e5e7eb");
        } catch (err) {
            console.error("Error today stats:", err);
        }
    }

    async function loadDashboard() {
        try {
            const res = await fetch("/api/data");
            if (!res.ok) {
                console.error("API data error:", res.status);
                return;
            }

            const data = await res.json();

            if (data.performance) {
                setAnimatedBalance(data.performance.balance);
                setColoredValue("profit", data.performance.profit);
                setColoredValue("loss", data.performance.loss);
                setColoredValue("net-profit", data.performance.net_profit);
                setColoredValue("avg-profit", data.performance.avg_profit_per_trade);
                setColoredValue("drawdown", data.performance.max_drawdown, true);
                setAnimatedText("trades", data.performance.trades ?? 0, "#e5e7eb");

                const winrate = Number(data.performance.winrate ?? 0);
                const winElColor =
                    winrate >= 50 ? "#22c55e" :
                    winrate >= 40 ? "#facc15" :
                    "#ef4444";

                setColoredValue("winrate", winrate, true);

                const winEl = document.getElementById("winrate");
                if (winEl) winEl.style.color = winElColor;

                renderEquity(data.performance.history || []);

                const totalWins = data.performance.wins ?? 0;
                const totalLosses = data.performance.losses ?? 0;
                const winsTitle = document.getElementById("wins-title");
                const lossesTitle = document.getElementById("losses-title");

                if (winsTitle) {
                    winsTitle.innerHTML = `WINS <span style="opacity:0.6;">(${totalWins})</span>`;
                }

                if (lossesTitle) {
                    lossesTitle.innerHTML = `LOSSES <span style="opacity:0.6;">(${totalLosses})</span>`;
                }
            }

            const botStatusEl = document.getElementById("bot-status");
            if (botStatusEl) {
                botStatusEl.innerText = data.running ? "RUNNING" : "STOPPED";
                botStatusEl.style.color = data.running ? "#22c55e" : "#ef4444";
            }

            const modeEl = document.getElementById("mode");
            if (modeEl) {
                modeEl.innerText = data.mode ?? "-";
                modeEl.style.color = data.mode === "real" ? "#ef4444" : "#22c55e";
            }

            const strategyEl = document.getElementById("strategy");
            if (strategyEl) strategyEl.innerText = data.strategy ?? "-";

            if (toggleBot) toggleBot.checked = !!data.running;
            if (toggleMode) toggleMode.checked = data.mode === "real";

            const botStatusText = document.getElementById("bot-status-text");
            if (botStatusText) botStatusText.innerText = data.running ? "RUNNING" : "STOPPED";

            const modeText = document.getElementById("mode-text");
            if (modeText) modeText.innerText = data.mode === "real" ? "REAL" : "DEMO";

            updateAiLevelBadge(aiLevelSelect?.value || "medium");

            if (data.ai) {
                const aiStrategy = document.getElementById("ai-strategy");
                const aiRisk = document.getElementById("ai-risk");

                if (aiStrategy) {
                    aiStrategy.innerText = data.ai.strategy_suggestion || "-";
                    aiStrategy.style.color = "#38bdf8";
                }

                if (aiRisk) {
                    aiRisk.innerText = data.ai.risk_suggestion || "-";
                    const riskValue = String(data.ai.risk_suggestion || "").toLowerCase();

                    if (riskValue === "aggressive") aiRisk.style.color = "#ef4444";
                    else if (riskValue === "conservative") aiRisk.style.color = "#22c55e";
                    else aiRisk.style.color = "#facc15";
                }
            }

            if (!selectedTrade) {
                if (data.positions && data.positions.length > 0) {
                    const exists = data.positions.some((p) => p.symbol === selectedPositionSymbol);

                    if (exists) {
                        currentSymbol = selectedPositionSymbol;
                    } else {
                        currentSymbol = data.positions[0].symbol;
                        selectedPositionSymbol = currentSymbol;
                    }
                } else {
                    currentSymbol = "BTCUSDT";
                    selectedPositionSymbol = null;
                }
            }

            await loadChart(currentSymbol);

            renderPositions(data.positions || []);
            renderTrades(data.trades || []);

            if (selectedTrade) {
                renderSelectedTradeMarker(selectedTrade);
                renderSelectedTradeLines(selectedTrade);
            } else {
                scaleHelperSeries.setData([]);
                candleSeries.setMarkers([]);
                renderPositionLines(data.positions || []);
            }

            renderAlerts(data.alerts || []);
            renderDecisions(data.last_decisions || []);
            await loadTodayStats();
        } catch (err) {
            console.error("Error dashboard:", err);
        }
    }

    function resizeChart() {
        if (!chartElement) return;

        const width = chartElement.clientWidth;
        const dynamicHeight = window.innerWidth <= 700 ? 340 : window.innerWidth <= 1100 ? 440 : 560;

        chart.applyOptions({
            width,
            height: dynamicHeight,
        });
    }

    function startAutoRefresh() {
        setInterval(() => {
            loadDashboard();
        }, 5000);
    }

    loadDashboard();
    startAutoRefresh();

    const resizeObserver = new ResizeObserver(() => {
        resizeChart();
    });

    resizeObserver.observe(chartElement);

    window.addEventListener("resize", () => {
        resizeChart();
    });
});
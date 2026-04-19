import pandas as pd


DATA_FILE = "trades_dataset.csv"


def safe_numeric(series, default=None):
    return pd.to_numeric(series, errors="coerce") if series is not None else default


def print_section(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def summarize_column_coverage(df: pd.DataFrame):
    print_section("COBERTURA DEL DATASET")

    print(f"Filas totales: {len(df)}")

    cols_to_check = [
        "result_net",
        "ai_trade_decision",
        "shadow_prediction",
        "pnl_net",
        "prob_live",
        "prob_historical",
        "prob_final",
        "decision_source",
        "models_agree",
        "dataset_version",
    ]

    for col in cols_to_check:
        if col in df.columns:
            valid = pd.to_numeric(df[col], errors="coerce").notna().sum() if col not in [
                "decision_source",
                "dataset_version",
            ] else df[col].astype(str).str.strip().replace("nan", "").ne("").sum()
            print(f"{col:<20} -> presente | valores útiles: {valid}")
        else:
            print(f"{col:<20} -> NO EXISTE")


def evaluate_subset(name: str, subset_df: pd.DataFrame):
    print_section(f"ANÁLISIS: {name}")

    if subset_df.empty:
        print("⚠ No hay filas para analizar")
        return

    total_closed = len(subset_df)

    compare_df = subset_df[
        subset_df["ai_trade_decision"].isin([0, 1]) &
        subset_df["shadow_prediction"].isin([0, 1])
    ].copy()

    print(f"Trades cerrados válidos: {total_closed}")
    print(f"Trades comparables:      {len(compare_df)}")

    if compare_df.empty:
        print("⚠ No hay trades con IA vieja y nueva disponibles para comparar")
        return

    compare_df["old_correct"] = (
        compare_df["ai_trade_decision"] == compare_df["result_net"]
    ).astype(int)
    compare_df["new_correct"] = (
        compare_df["shadow_prediction"] == compare_df["result_net"]
    ).astype(int)
    compare_df["agree"] = (
        compare_df["ai_trade_decision"] == compare_df["shadow_prediction"]
    ).astype(int)

    disagree_df = compare_df[compare_df["agree"] == 0].copy()

    old_acc = compare_df["old_correct"].mean()
    new_acc = compare_df["new_correct"].mean()
    agree_rate = compare_df["agree"].mean()

    old_buy_rate = (compare_df["ai_trade_decision"] == 1).mean()
    new_buy_rate = (compare_df["shadow_prediction"] == 1).mean()

    old_avg_pnl = compare_df.loc[
        compare_df["ai_trade_decision"] == 1, "pnl_net"
    ].mean()
    new_avg_pnl = compare_df.loc[
        compare_df["shadow_prediction"] == 1, "pnl_net"
    ].mean()

    print(f"Acierto IA vieja:        {old_acc:.2%}")
    print(f"Acierto IA nueva:        {new_acc:.2%}")
    print(f"Tasa de coincidencia:    {agree_rate:.2%}")
    print(f"Vieja dijo BUY:          {old_buy_rate:.2%}")
    print(f"Nueva dijo BUY:          {new_buy_rate:.2%}")
    print(
        f"PNL neto prom. BUY vieja:{old_avg_pnl:.4f}"
        if pd.notna(old_avg_pnl) else
        "PNL neto prom. BUY vieja: N/A"
    )
    print(
        f"PNL neto prom. BUY nueva:{new_avg_pnl:.4f}"
        if pd.notna(new_avg_pnl) else
        "PNL neto prom. BUY nueva: N/A"
    )

    print_section(f"DESACUERDOS: {name}")
    print(f"Trades en desacuerdo:    {len(disagree_df)}")

    if len(disagree_df) > 0:
        old_wins = (disagree_df["old_correct"] > disagree_df["new_correct"]).sum()
        new_wins = (disagree_df["new_correct"] > disagree_df["old_correct"]).sum()
        ties = (disagree_df["new_correct"] == disagree_df["old_correct"]).sum()

        print(f"Vieja acertó más:        {old_wins}")
        print(f"Nueva acertó más:        {new_wins}")
        print(f"Empates:                 {ties}")

        old_pnl_when_old_right = disagree_df.loc[
            disagree_df["old_correct"] > disagree_df["new_correct"], "pnl_net"
        ].mean()

        new_pnl_when_new_right = disagree_df.loc[
            disagree_df["new_correct"] > disagree_df["old_correct"], "pnl_net"
        ].mean()

        print(
            f"PNL neto prom. cuando vieja tuvo razón: {old_pnl_when_old_right:.4f}"
            if pd.notna(old_pnl_when_old_right) else
            "PNL vieja: N/A"
        )
        print(
            f"PNL neto prom. cuando nueva tuvo razón: {new_pnl_when_new_right:.4f}"
            if pd.notna(new_pnl_when_new_right) else
            "PNL nueva: N/A"
        )

    print_section(f"COMBINACIONES MÁS FRECUENTES: {name}")
    combo = (
        compare_df
        .groupby(["ai_trade_decision", "shadow_prediction", "result_net"])
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    print(combo.head(12).to_string(index=False))

    if len(disagree_df) > 0:
        cols = [
            c for c in [
                "timestamp",
                "symbol",
                "dataset_version",
                "ai_trade_decision",
                "shadow_prediction",
                "result_net",
                "pnl_net",
                "prob_live",
                "prob_historical",
                "prob_final",
                "decision_source",
                "models_agree",
                "strategy_name",
                "risk_mode",
                "market_regime",
                "liquidity_mode",
                "signal_confidence",
            ] if c in disagree_df.columns
        ]

        print_section(f"EJEMPLOS DE DESACUERDO: {name}")
        print(disagree_df[cols].head(20).to_string(index=False))

    print_section(f"SEÑAL DE MIGRACIÓN: {name}")

    acc_gap = new_acc - old_acc
    enough_samples = len(compare_df) >= 50
    enough_disagreements = len(disagree_df) >= 15
    pnl_signal = (
        pd.notna(new_avg_pnl) and pd.notna(old_avg_pnl) and new_avg_pnl >= old_avg_pnl
    )

    print(f"Diferencia de accuracy (nueva - vieja): {acc_gap:.2%}")
    print(f"Muestras suficientes:                   {enough_samples}")
    print(f"Desacuerdos suficientes:                {enough_disagreements}")
    print(f"PNL nueva >= vieja:                     {pnl_signal}")

    if enough_samples and enough_disagreements and acc_gap >= 0.03 and pnl_signal:
        print("✅ La IA nueva ya parece candidata para pasar a modo 'poca' o 'media'")
    elif enough_samples and acc_gap >= 0.00:
        print("🟡 La IA nueva está cerca, pero todavía conviene mantener modo sombra")
    else:
        print("🔴 Todavía falta evidencia para migrar")


def main():
    try:
        df = pd.read_csv(
            DATA_FILE,
            encoding="utf-8",
            on_bad_lines="skip",
            engine="python"
        )
    except Exception as e:
        print(f"❌ Error leyendo {DATA_FILE}: {e}")
        return

    if df.empty:
        print("❌ El dataset está vacío")
        return

    df = df.copy()

    summarize_column_coverage(df)

    required_min_cols = ["result_net", "ai_trade_decision", "pnl_net"]
    missing_min = [c for c in required_min_cols if c not in df.columns]
    if missing_min:
        print_section("ERROR")
        print(f"❌ Faltan columnas mínimas requeridas: {missing_min}")
        return

    df["result_net"] = safe_numeric(df["result_net"])
    df["ai_trade_decision"] = safe_numeric(df["ai_trade_decision"])
    df["pnl_net"] = safe_numeric(df["pnl_net"])

    if "shadow_prediction" in df.columns:
        df["shadow_prediction"] = safe_numeric(df["shadow_prediction"])
    else:
        df["shadow_prediction"] = pd.NA

    if "prob_live" in df.columns:
        df["prob_live"] = safe_numeric(df["prob_live"])
    if "prob_historical" in df.columns:
        df["prob_historical"] = safe_numeric(df["prob_historical"])
    if "prob_final" in df.columns:
        df["prob_final"] = safe_numeric(df["prob_final"])

    df = df[df["result_net"].isin([0, 1])]

    if df.empty:
        print_section("ERROR")
        print("❌ No hay trades cerrados con result_net válido")
        return

    # análisis global
    evaluate_subset("GLOBAL", df)

    # análisis últimos 50
    if "timestamp" in df.columns:
        df["timestamp"] = safe_numeric(df["timestamp"])
        df_sorted = df.sort_values("timestamp")
        evaluate_subset("ÚLTIMOS 50", df_sorted.tail(50))
        evaluate_subset("ÚLTIMOS 100", df_sorted.tail(100))

    # análisis por versión
    if "dataset_version" in df.columns:
        non_empty_versions = df["dataset_version"].astype(str).str.strip()
        versioned_df = df[non_empty_versions != ""].copy()

        if not versioned_df.empty:
            print_section("ACCURACY POR DATASET_VERSION")

            compare_version_df = versioned_df[
                versioned_df["ai_trade_decision"].isin([0, 1]) &
                versioned_df["shadow_prediction"].isin([0, 1])
            ].copy()

            if not compare_version_df.empty:
                compare_version_df["old_correct"] = (
                    compare_version_df["ai_trade_decision"] == compare_version_df["result_net"]
                ).astype(int)
                compare_version_df["new_correct"] = (
                    compare_version_df["shadow_prediction"] == compare_version_df["result_net"]
                ).astype(int)

                by_version = (
                    compare_version_df.groupby("dataset_version")
                    .agg(
                        trades=("result_net", "count"),
                        old_acc=("old_correct", "mean"),
                        new_acc=("new_correct", "mean"),
                        avg_pnl=("pnl_net", "mean"),
                    )
                    .reset_index()
                    .sort_values("trades", ascending=False)
                )

                print(by_version.to_string(index=False))
            else:
                print("⚠ No hay suficiente información para comparar por dataset_version")

    print_section("FIN ANÁLISIS")
    print("Listo.")


if __name__ == "__main__":
    main()
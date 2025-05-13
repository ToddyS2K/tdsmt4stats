    # === STATISTICHE EXTRA ===
    st.subheader("📈 Statistiche del Trading")

    total_trades = len(df)
    winning_trades = df[df['Profit'] > 0]
    losing_trades = df[df['Profit'] < 0]

    win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
    avg_profit_per_trade = df['Profit %'].mean()
    total_profit = df['Profit %'].sum()

    gross_profit = winning_trades['Profit'].sum()
    gross_loss = -losing_trades['Profit'].sum()  # positivo
    profit_factor = gross_profit / gross_loss if gross_loss != 0 else float('inf')

    win_loss_ratio = len(winning_trades) / len(losing_trades) if len(losing_trades) > 0 else float('inf')

    stats = {
        "Totale trade eseguiti": total_trades,
        "Win rate (%)": f"{win_rate:.2f}%",
        "Profitto medio per trade (%)": f"{avg_profit_per_trade:.2f}%",
        "Profitto totale (%)": f"{total_profit:.2f}%",
        "Profit factor": f"{profit_factor:.2f}",
        "Rapporto Win/Loss": f"{win_loss_ratio:.2f}"
    }

    for key, value in stats.items():
        st.write(f"**{key}:** {value}")

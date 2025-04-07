from datetime import date, datetime, time

import pandas as pd
import streamlit as st
from helper import get_direction, get_ltp, get_strick

# Constant Config
pnl = pd.DataFrame(
    data=[],
    columns=[
        "instrument",
        "entry_price",
        "transaction_type",
        "close_price",
        "entry_time",
        "exit_time",
        "quantity",
        "trade_id",
    ],
)
st.set_page_config(page_title="Future With Hedge", page_icon="🧊", layout="wide")
st.header("Future")
cont = st.container(border=True)
cont.subheader("Future Config")
id = 1
col1, col2, col3 = cont.columns(3, gap="small")
symbol = col1.selectbox(
    "Select Crypto",
    ("BTCUSD", "ETHUSD"),
)
diff = col1.selectbox(
    "Select Strick Diff",
    (200, 20),
)
avg = col3.selectbox(
    "Next Avg Level",
    (1000, 1500, 100, 150),
)
d: date = col2.date_input("Select Date", date(2024, 12, 31))
t: time = col2.time_input("Select Time", time(13, 0))
end = datetime(year=d.year, month=d.month, day=d.day, hour=t.hour, minute=t.minute)


if symbol and diff and st.button("submit"):
    st.write(f"{symbol} with diff {int(diff)}")
    df = get_direction(symbol, end=end, time_frame="1h")
    direction = df["SUPERTd_10_3.0"].iloc[0]
    close = df["close"].iloc[0]

    if direction == 1:
        atm_strick = get_strick(
            symbol=symbol, diff=diff, end=end, ltp=close, otm=0, type="C"
        )
        hedge_strick = get_strick(
            symbol=symbol, diff=diff, end=end, ltp=close, otm=7, type="C"
        )
    elif direction == -1:
        atm_strick = get_strick(
            symbol=symbol, diff=diff, end=end, ltp=close, otm=0, type="P"
        )
        hedge_strick = get_strick(
            symbol=symbol, diff=diff, end=end, ltp=close, otm=-7, type="P"
        )
    atm_strick_ltp = get_ltp(atm_strick, end=end)
    hedge_strick_ltp = get_ltp(hedge_strick, end=end)
    new_df = pd.DataFrame(
        {
            "instrument": [symbol, atm_strick, hedge_strick],
            "entry_price": [close, atm_strick_ltp, hedge_strick_ltp],
            "transaction_type": [direction, -1, 1],
            "close_price": [None, None, None],
            "entry_time": [end, end, end],
            "exit_time": [None, None, None],
            "quantity": [1, 2, 2],
            "trade_id": [id, id, id],
        }
    )
    pnl = pd.concat([pnl, new_df], ignore_index=True)
    id += 1

st.write(pnl)


def next_step():
    st.button("Next")
    # while True:


if id > 1:
    next_step()

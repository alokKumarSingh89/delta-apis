from datetime import date, datetime, time

import streamlit as st
from helper import get_direction

st.set_page_config(page_title="Future With Hedge", page_icon="🧊", layout="wide")
st.header("Future")

cont = st.container(border=True)
cont.subheader("Future Config")

col1, col2 = cont.columns(2, gap="small")
symbol = col1.selectbox(
    "Select Crypto",
    ("BTCUSD", "ETHUSD"),
)
diff = col1.selectbox(
    "Select Strick Diff",
    (200, 20),
)
d: date = col2.date_input("Select Date", date(2024, 12, 31))
t: time = col2.time_input("Select Time", time(13, 0))
end = datetime(year=d.year, month=d.month, day=d.day, hour=t.hour, minute=t.minute)
if symbol and diff and st.button("submit"):
    st.write(f"{symbol} with diff {int(diff)}")
    df = get_direction(symbol, end=end, time_frame="1h")
    direction = df["SUPERTd_10_3.0"].iloc[0]
    st.write(direction)
    st.write(df)

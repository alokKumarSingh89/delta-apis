import time
from datetime import timedelta

import pandas as pd
from delta_exchange import add_supertrend, calculate_heikin_ashi, get_historical_data


def get_direction(symbol, end, days=3, time_frame="5m"):
    start = end - timedelta(days=days)
    start = (time.mktime(start.timetuple())) + 19800
    end = (time.mktime(end.timetuple())) + 19800
    res = get_historical_data(symbol, start, end, time_frame)
    df = pd.DataFrame(res["result"])
    df["date"] = pd.to_datetime(df["time"], unit="s") + pd.Timedelta(
        hours=5, minutes=30
    )
    df = df.sort_values(by="time", ascending=True)
    df = df.reset_index()
    df = calculate_heikin_ashi(df, diff=1)
    df = add_supertrend(df.copy())
    return df


def get_ltp(symbol, end, days=3, time_frame="5m"):
    df = get_direction(symbol, end, days=3, time_frame="5m")
    return df["close"].iloc[0]


def get_strick(symbol, diff, end, ltp, otm=0, type="C"):
    now = end
    expiry = ""
    if now.hour >= 17 or (now.hour == 17 and now.minute >= 29):
        now += timedelta(days=1)
        expiry = f"{str(now.day).zfill(2)}{str(now.month).zfill(2)}{str(now.year)[2:]}"
    else:
        expiry = f"{str(now.day).zfill(2)}{str(now.month).zfill(2)}{str(now.year)[2:]}"
    atm = round(ltp / diff) * diff
    return f"{type}-{symbol[:-3]}-{atm + otm * diff}-{expiry}"

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

import httpx
import pandas_ta as ta

BASE_URL = "https://api.india.delta.exchange/v2"
HEADER = {"Accept": "application/json"}


def determine_ha_candle_type(data, diff):
    if data["HA_Close"] > data["HA_Open"] and data["HA_Open"] == data["HA_Low"]:
        return 1
    elif data["HA_Close"] < data["HA_Open"] and data["HA_Open"] == data["HA_High"]:
        return -1
    else:
        return 0


def calculate_heikin_ashi(df, diff=0):
    # Initialize the Heikin-Ashi columns
    df["HA_Open"] = 0.0
    df["HA_High"] = 0.0
    df["HA_Low"] = 0.0
    df["HA_Close"] = 0.0

    # Calculate the first Heikin-Ashi candle
    df.at[df.index[0], "HA_Open"] = (df["open"][0] + df["close"][0]) / 2
    df.at[df.index[0], "HA_Close"] = (
        df["open"][0] + df["high"][0] + df["low"][0] + df["close"][0]
    ) / 4
    df.at[df.index[0], "HA_High"] = df["high"][0]
    df.at[df.index[0], "HA_Low"] = df["low"][0]

    # Calculate the rest of the Heikin-Ashi candles
    for i in range(1, len(df)):
        df.at[df.index[i], "HA_Open"] = (
            df["HA_Open"][i - 1] + df["HA_Close"][i - 1]
        ) / 2
        df.at[df.index[i], "HA_Close"] = (
            df["open"][i] + df["high"][i] + df["low"][i] + df["close"][i]
        ) / 4
        df.at[df.index[i], "HA_High"] = max(
            df["high"][i], df["HA_Open"][i], df["HA_Close"][i]
        )
        df.at[df.index[i], "HA_Low"] = min(
            df["low"][i], df["HA_Open"][i], df["HA_Close"][i]
        )
    df["HA_Close"] = round(df["HA_Close"], 2)
    df["HA_Open"] = round(df["HA_Open"], 2)
    df["HA_High"] = round(df["HA_High"], 2)
    df["HA_Low"] = round(df["HA_Low"], 2)
    df["Candle_Type"] = df.apply(determine_ha_candle_type, diff=diff, axis=1)
    return df


def list_index():
    res = httpx.get(f"{BASE_URL}/products")
    return res.json()


def product_symbol(symbol):
    res = httpx.get(f"{BASE_URL}/products/{symbol}", params={}, headers=HEADER)
    return res.json()


def ticker_symbol(symbol):
    res = httpx.get(f"{BASE_URL}/tickers/{symbol}", params={}, headers=HEADER)
    return res.json()


def get_historical_data(symbol, start, end, time_frame="5m"):
    res = httpx.get(
        f"{BASE_URL}/history/candles",
        params={
            "resolution": time_frame,
            "symbol": symbol,
            "start": start,
            "end": end,
        },
        headers=HEADER,
    )
    return res.json()


def add_supertrend(df):
    super_trade = ta.supertrend(
        high=df["HA_High"],
        low=df["HA_Low"],
        close=df["HA_Close"],
        length=10,
        multiplier=3,
    )
    df = df.join(super_trade)
    return df

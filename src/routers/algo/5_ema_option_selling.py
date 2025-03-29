from src.routers.algo.delta_exchange import DeltaExchange
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from src.LogConfig import logger
from src.routers.ha import calculate_heikin_ashi



exchange = DeltaExchange()
data = {
    "Date": [],
    "Strick": [],
    "Entry_price": [],
    "Qunatity": [],
    "Exit Price": [],
    "Exit Date": [],
}
TRADE_TYPE = None
trade = {}


def create_file_and_save(pd_data):
    my_file = Path(__file__).parent.parent.parent.parent / "trade_5ema.csv"
    if my_file.exists():
        if len(pd_data.get("Date")) > 0:
            df = pd.DataFrame(pd_data)
            df.to_csv(my_file, mode="a", header=False, index=False)
        logger.info("file Exit")
    else:
        df = pd.DataFrame(pd_data)
        df.to_csv(my_file)
        logger.warning("Not Exit")


def get_ltp(strick, count=1):
    try:
        res = exchange.ticker_symbol(strick)
        return res["result"]["close"]
    except Exception as e:
        logger.warning(strick, e)
        if count <= 3:
            return get_ltp(strick=strick, count=count + 1)


def get_strick(sybmol, str_diff):
    now = datetime.now()
    expiry = ""
    if now.hour >= 17 or (now.hour == 17 and now.minute >= 29):
        now += timedelta(days=1)
        expiry = f"{str(now.day).zfill(2)}{str(now.month).zfill(2)}{str(now.year)[2:]}"
    else:
        expiry = f"{str(now.day).zfill(2)}{str(now.month).zfill(2)}{str(now.year)[2:]}"
    ltp = get_ltp(sybmol)
    atm = round(ltp / str_diff) * str_diff
    CE = f"C-BTC-{atm}-{expiry}"
    PE = f"P-BTC-{atm}-{expiry}"
    return {"ce": CE, "pe": PE, "atm": atm}


def get_candle(symbol):
    end = datetime.now()
    start = end - timedelta(days=3)
    start = (time.mktime(start.timetuple()))+19800
    end = (time.mktime(end.timetuple()))+19800
    result = exchange.get_historical_data(symbol=symbol,start=str(start), end=str(end))
    df = pd.DataFrame(result['result'])
    df["date"] = pd.to_datetime(df['time'], unit='s') + pd.Timedelta(hours=5, minutes=30)
    df = df.sort_values(by='time', ascending=True)
    df = df.reset_index()
    df['ema_short'] = df['close'].ewm(span=9, adjust=False).mean()
    df['ema_long'] = df['close'].ewm(span=50, adjust=False).mean()
    new_df = calculate_heikin_ashi(df.copy())
    return new_df


def place_paper_trade(strick, transaction_type):
    global trade
    ltp = get_ltp(strick)
    trade[transaction_type] = {
        "date": datetime.now(),
        "strick": strick,
        "entry": ltp,
        "qunatiry": 1,
    }
    logger.info(f"Place trade for {strick} with {trade[transaction_type]}")


def update_csv(new_data):
    df_data = {
        "Date": [new_data["date"]],
        "Strick": [new_data["strick"]],
        "Entry_price": [new_data["entry"]],
        "Qunatity": [new_data.get("qunatiry")],
        "Exit Price": [new_data.get("exit_price")],
        "Exit Date": [new_data.get("exit_date")],
    }
    create_file_and_save(df_data)


def book_profit(transaction_type):
    global trade
    trade_data = trade[transaction_type]
    ltp = get_ltp(trade_data["strick"])
    trade[transaction_type]["exit_price"] = ltp
    trade[transaction_type]["exit_date"] = datetime.now()
    logger.info(f"Booking Profit for {transaction_type} with {trade[transaction_type]}")
    update_csv(trade[transaction_type])


def check_and_update_trade(symbol):
    global TRADE_TYPE, trade
    if TRADE_TYPE is None:
        return
    ltp = get_ltp(trade[TRADE_TYPE]["strick"])
    logger.info(f"Checking Again. Current LTP: {ltp}")
    if ltp <= round(trade[TRADE_TYPE]["entry"]/2, 2):
        book_profit(TRADE_TYPE)
        strick = get_strick(sybmol=symbol, str_diff=200)
        pe_strick = strick[TRADE_TYPE]
        place_paper_trade(pe_strick, TRADE_TYPE)


def check_condition(df):
    curr_ema_short = df["ema_short"].iloc[-1]
    curr_ema_long = df["ema_long"].iloc[-1]
    ha_close = df['HA_Close'].iloc[-1]
    logger.info(f"curr_ema_short:{curr_ema_short} , curr_ema_long:{curr_ema_long}, ha_close:{ha_close}")
    if ha_close > curr_ema_short and ha_close > curr_ema_long:
        return 1
    elif ha_close < curr_ema_short and ha_close < curr_ema_long:
        return -1


def monitor_future(symbol):
    global TRADE_TYPE
    while True:
        now_time = datetime.now()
        while now_time.minute % 5 != 0 and TRADE_TYPE is None:
            print(now_time.minute % 5, now_time.minute, "will wait try again")
            time.sleep(10)
            now_time = datetime.now()
        df = get_candle(symbol)
        candle_type = df['Candle_Type'].iloc[-1]
        if TRADE_TYPE is None:
            strick = get_strick(sybmol=symbol, str_diff=200)
            if check_condition(df) == 1:
                pe_strick = strick["pe"]
                place_paper_trade(pe_strick, "pe")
                TRADE_TYPE = "pe"
            elif check_condition(df) == -1:
                ce_strick = strick["ce"]
                place_paper_trade(ce_strick, "ce")
                TRADE_TYPE = "ce"
        else:
            now = datetime.now()
            if now.hour == 17 and (24 <= now.minute <= 30):
                book_profit(TRADE_TYPE)
                logger.info("Now will wait for 15 min before new trade")
                time.sleep(300*3)
                TRADE_TYPE = None
                continue
            # Exit If Candle Reverse
            if candle_type == 1 and TRADE_TYPE == "ce":
                book_profit(TRADE_TYPE)
                TRADE_TYPE = None
            elif candle_type == -1 and TRADE_TYPE == "pe":
                book_profit(TRADE_TYPE)
                TRADE_TYPE = None

            # if curr_ema_short > curr_ema_long:
            #     strick = get_strick(sybmol=symbol, str_diff=200)
            #     pe_strick = strick["pe"]
            #     logger.info(f"BUY SIGNAL - Placing Order...{pe_strick}")
            #
            #     place_paper_trade(pe_strick, "pe")
            #     TRADE_TYPE = "pe"
            # elif curr_ema_short < curr_ema_long:
            #     logger.info("SELL SIGNAL - Placing Order...")
            #     strick = get_strick(sybmol=symbol, str_diff=200)
            #     ce_strick = strick["ce"]
            #     place_paper_trade(ce_strick, "ce")
            #     TRADE_TYPE = "ce"
        time.sleep(60*5)
        logger.info(f"candle_type:{candle_type} Trade_type:{TRADE_TYPE}, check_condition:{check_condition(df)}")
        check_and_update_trade(symbol)


def ema5_algo():
    symbol = "BTCUSD"
    create_file_and_save(data)
    monitor_future(symbol)


ema5_algo()
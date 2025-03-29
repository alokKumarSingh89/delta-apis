# Option selling on avg value

import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

from src.LogConfig import logger
from src.routers.algo.delta_exchange import DeltaExchange

exchange = DeltaExchange()

MAX_LOTS = 16
MAX_TRY = 3
loopConfig = {"isRunning": True}
data = {
    "Date": [],
    "Strick": [],
    "Type": [],
    "Entry_price": [],
    "Last_update": [],
    "Qunatity": [],
    "Exit Price": [],
    "Exit Date": [],
    "Avg Count": [],
}
trade = {}


def create_file_and_save(data):
    my_file = Path(__file__).parent.parent.parent.parent / "trade.csv"
    if my_file.exists():
        if len(data.get("Date")) > 0:
            df = pd.DataFrame(data)
            df.to_csv(my_file, mode="a", header=False, index=False)
        logger.info("file Exit")
    else:
        df = pd.DataFrame(data)
        df.to_csv(my_file)
        logger.warning("Not Exit")


def get_strick(sybmol, str_diff):
    now = datetime.now()
    expiry = ""
    print(now.hour, now.minute)
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


def get_ltp(strick, count=1):
    try:
        res = exchange.ticker_symbol(strick)
        return res["result"]["close"]
    except Exception as e:
        logger.warning(strick, e)
        if count <= MAX_TRY:
            return get_ltp(strick=strick, count=count + 1)


def update_csv(newData):
    data = {
        "Date": [newData["date"]],
        "Strick": [newData["strick"]],
        "Type": [newData["type"]],
        "Entry_price": [newData["entry"]],
        "Last_update": [newData.get("last_update")],
        "Qunatity": [newData.get("qunatiry")],
        "Exit Price": [newData.get("exit_price")],
        "Exit Date": [newData.get("exit_date")],
        "Avg Count": [newData.get("avg_count")],
    }
    create_file_and_save(data)


def place_paper_trade(strick, type):
    global trade
    ltp = get_ltp(strick)
    trade[type] = {
        "date": datetime.now(),
        "strick": strick,
        "type": type,
        "entry": ltp,
        "next_entry": ltp * 2,
        "last_update": datetime.now(),
        "qunatiry": 1,
        "next_sell_quantity": 1 * 2,
    }
    logger.info(f"Place trade for {strick} with {trade[type]}")


def book_profit(type):
    global trade
    data = trade[type]
    ltp = get_ltp(data["strick"])
    trade[type]["exit_price"] = ltp
    trade[type]["exit_date"] = datetime.now()
    logger.info(f"Booking Profit for {type} with {trade[type]}")
    update_csv(trade[type])


def avg_the_price(ltp, type):
    global trade
    avg_price = (
        trade[type]["entry"] * trade[type]["quantity"]
        + ltp * trade[type]["next_sell_quantity"]
    )
    avg_quantity = trade[type]["quantity"] + trade[type]["next_sell_quantity"]
    logger.info(
        f"{trade[type]['strick']}: Previous price:{trade[type]['entry']} and Quantity:{trade[type]['quantity']}"
    )
    logger.info(f"Avg price:{avg_price} and Quantity:{avg_quantity}")
    logger.info(f"Ltp:{ltp}")
    trade[type]["entry"] = round(avg_price / avg_quantity, 2)
    trade[type]["next_sell_quantity"] = trade[type]["next_sell_quantity"] * 2
    trade[type]["quantity"] = avg_quantity
    trade[type]["last_update"] = datetime.now()
    trade[type]["next_entry"] = ltp * 2
    logger.info(f"Update Trade {trade}")


def take_new_trade(type=None):
    global trade
    try:
        if type is None:
            trade = {}
            strick = get_strick("BTCUSD", 200)
            place_paper_trade(strick=strick.get("ce"), type="ce")
            place_paper_trade(strick=strick.get("pe"), type="pe")
        elif type == "ce" or type == "pe":
            trade[type] = {}
            strick = get_strick("BTCUSD", 200)
            place_paper_trade(strick=strick.get(type), type=type)
    except Exception as e:
        logger.warning(e)


def monitor_trade():
    global trade
    loopConfig["isRunning"] = True
    while loopConfig["isRunning"]:
        # check expiry time
        now = datetime.now()
        if now.hour == 17 and (now.minute >= 29 and now.minute <= 30):
            book_profit("ce")
            book_profit("pe")
            logger.info("Wait 15 minute to take new trade")
            time.sleep(60 * 15)
            take_new_trade()
            continue

        ce_ltp = get_ltp(trade["ce"]["strick"])
        pe_ltp = get_ltp(trade["pe"]["strick"])
        # Avg out the CE
        if (
            trade["ce"]["next_entry"] < ce_ltp
            and trade["ce"]["next_sell_quantity"] <= MAX_LOTS
        ):
            avg_the_price(ce_ltp, "ce")

        # Avg out the PE
        if (
            trade["pe"]["next_entry"] < pe_ltp
            and trade["pe"]["next_sell_quantity"] <= MAX_LOTS
        ):
            avg_the_price(ce_ltp, "pe")

        # Profit Booking for CE
        if round(trade["ce"]["entry"] / 2, 2) > ce_ltp:
            book_profit("ce")
            take_new_trade("ce")
        if round(trade["pe"]["entry"] / 2, 2) > pe_ltp:
            book_profit("pe")
            take_new_trade("pe")

        time.sleep(60)
        logger.warning(f"Checking Again, CE:{ce_ltp} and PE:{pe_ltp}")
    logger.info("Closing program")


def run_algo():
    create_file_and_save(data)
    take_new_trade()
    monitor_trade()

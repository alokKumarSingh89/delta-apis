import threading
from pathlib import Path
import pandas as pd
from src.LogConfig import logger
from src.routers.algo.delta_exchange import DeltaExchange
import time
from datetime import datetime, timedelta
from src.routers.ha import calculate_heikin_ashi


class FutureEma():
    def __init__(self, symbol):
        self.symbol = symbol
        self.file_name = Path(__file__).parent.parent.parent.parent / f"output/{symbol}_future_11ema.csv"
        self.exchange = DeltaExchange()
        self.data = {
            "Date": [],
            "Strick": [],
            "Entry_price": [],
            "Qunatity": [],
            "Exit Price": [],
            "Exit Date": [],
            "Transaction_Type": [],
        }
        self.trade = {}
        self.is_in_trade = None
        self.create_file()

    def create_file(self):
        if self.file_name.exists() is False:
            df = pd.DataFrame(self.data)
            df.to_csv(self.file_name, index=False)
            logger.warning("Not Exit")

    def save_file(self, pd_data):
        if self.file_name.exists():
            if len(pd_data.get("Date")) > 0:
                df = pd.DataFrame(pd_data)
                df.to_csv(self.file_name, mode="a", header=False, index=False)
            logger.info("file Exit")

    def get_ltp(self, count=1):
        try:
            res = self.exchange.ticker_symbol(self.symbol)
            return res["result"]["close"]
        except Exception as e:
            logger.warning(self.symbol, e)
            if count <= 3:
                return self.get_ltp(count=count + 1)

    def get_candle(self):
        end = datetime.now()
        start = end - timedelta(days=3)
        start = (time.mktime(start.timetuple())) + 19800
        end = (time.mktime(end.timetuple())) + 19800
        result = self.exchange.get_historical_data(symbol=self.symbol, start=str(start), end=str(end))
        df = pd.DataFrame(result['result'])
        df["date"] = pd.to_datetime(df['time'], unit='s') + pd.Timedelta(hours=5, minutes=30)
        df = df.sort_values(by='time', ascending=True)
        df = df.reset_index()
        new_df = calculate_heikin_ashi(df.copy())
        new_df['ema'] = new_df['HA_Close'].ewm(span=11, adjust=False).mean()
        return new_df

    def place_paper_trade(self, transaction_type):
        ltp = self.get_ltp()
        self.trade = {
            "date": datetime.now(),
            "entry": ltp,
            "qunatiry": 1,
            "transaction_type": transaction_type
        }
        logger.info(f"Place trade for {self.symbol} with {self.trade}")

    def update_csv(self):
        df_data = {
            "Date": [self.trade["date"]],
            "Strick": [self.symbol],
            "Entry_price": [self.trade["entry"]],
            "Qunatity": [self.trade.get("qunatiry")],
            "Exit Price": [self.trade.get("exit_price")],
            "Exit Date": [self.trade.get("exit_date")],
            "Transaction_Type": [self.trade.get("transaction_type")]
        }
        self.save_file(df_data)

    def book_profit(self):
        trade_data = self.trade
        ltp = self.get_ltp()
        self.trade["exit_price"] = ltp
        self.trade["exit_date"] = datetime.now()
        logger.info(f"Booking Profit for {datetime.now()} with {self.trade}")
        self.update_csv()

    def check_condition(self, df):
        curr_ema = df["ema"].iloc[-1]
        ha_close = df['HA_Close'].iloc[-1]
        candle_type = df['Candle_Type'].iloc[-1]
        logger.info(f"{self.symbol}:curr_ema_short:{curr_ema} == ha_close:{ha_close}")
        if ha_close > curr_ema and candle_type == 1:
            return 1
        elif ha_close < curr_ema and candle_type == -1:
            return -1

    def monitor_future(self):
        while True:
            now_time = datetime.now()
            while now_time.minute % 5 != 0 and self.is_in_trade is None:
                print(now_time.minute % 5, now_time.minute, "will wait for 10 sec and  try again")
                time.sleep(10)
                now_time = datetime.now()
            df = self.get_candle()
            ha_close = df['close'].iloc[-1]
            candle_type = df['Candle_Type'].iloc[-1]
            condition = self.check_condition(df)
            if self.is_in_trade is None:
                if condition == 1:
                    self.is_in_trade = "BUY"
                    self.place_paper_trade(self.is_in_trade)
                elif condition == -1:
                    self.is_in_trade = "SELL"
                    self.place_paper_trade(self.is_in_trade)
            else:
                if condition == 1 and self.is_in_trade == "SELL":
                    self.book_profit()
                    self.is_in_trade = None
                    continue
                elif condition == -1 and self.is_in_trade == "BUY":
                    self.book_profit()
                    self.is_in_trade = None
                    continue

            time.sleep(60 * 5)
            logger.info(f"{self.symbol}: candle_type:{candle_type} Trade_type:{self.is_in_trade}, check_condition:{condition}, HA_close:{ha_close}")


def start_algo():
    symbols = ["SOLUSD", "XRPUSD", "DOGEUSD", "LTCUSD"]
    threads = []
    for symbol in symbols:
        trade = FutureEma(symbol=symbol)
        thread = threading.Thread(target=trade.monitor_future)
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()


def retry():
    try:
        start_algo()
    except Exception as e:
        print(e)
        logger.info("Got exception, wait for 5 mins")
        time.sleep(60*3)
        retry()

retry()
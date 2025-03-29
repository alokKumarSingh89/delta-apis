from src.routers.algo.delta_exchange import DeltaExchange
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from src.LogConfig import logger
from src.routers.ha import calculate_heikin_ashi
import threading


class EmaOptionSelling60():
    """
        Price Cross 11 EMA
    """

    def __init__(self, symbol, strick_diff, name):
        self.symbol = symbol
        self.name = name
        self.strick_diff = strick_diff
        self.exchange = DeltaExchange()
        self.trade_type = None
        self.current_trade = {}
        self.time_frame = 15
        self.ema = 30  # 60 on 5 min time frame
        self.file_name = Path(__file__).parent.parent.parent.parent / f"output/{symbol}_{self.ema}ema.csv"
        self.create_file_if_not_exit()
        self.current_sl = 0

    def create_file_if_not_exit(self):
        if self.file_name.exists() is False:
            data = {
                "Date": [],
                "Strick": [],
                "Entry_price": [],
                "Qunatity": [],
                "Exit Price": [],
                "Exit Date": [],
            }
            df = pd.DataFrame(data)
            df.to_csv(self.file_name, index=False)
            logger.warning("Not Exit")

    def save_csv(self, strick_type):
        data = {
            "Date": [self.current_trade[strick_type]["date"]],
            "Strick": [self.current_trade[strick_type]["strick"]],
            "Entry_price": [self.current_trade[strick_type]["entry"]],
            "Qunatity": [self.current_trade[strick_type].get("qunatiry")],
            "Exit Price": [self.current_trade[strick_type].get("exit_price")],
            "Exit Date": [self.current_trade[strick_type].get("exit_date")],
        }
        if len(data.get("Date")) > 0:
            df = pd.DataFrame(data)
            df.to_csv(self.file_name, mode="a", header=False, index=False)
            logger.info("file Saved")

    def get_ltp(self, strick, count=1):
        try:
            res = self.exchange.ticker_symbol(strick)
            return res["result"]["close"]
        except Exception as e:
            logger.warning(strick, count, e)
            if count <= 3:
                return self.get_ltp(strick=strick, count=count + 1)

    def get_strick(self):
        now = datetime.now()
        expiry = ""
        if now.hour >= 17 or (now.hour == 17 and now.minute >= 29):
            now += timedelta(days=1)
            expiry = f"{str(now.day).zfill(2)}{str(now.month).zfill(2)}{str(now.year)[2:]}"
        else:
            expiry = f"{str(now.day).zfill(2)}{str(now.month).zfill(2)}{str(now.year)[2:]}"
        ltp = self.get_ltp(self.symbol)
        atm = round(ltp / self.strick_diff) * self.strick_diff
        CE = f"C-{self.name}-{atm}-{expiry}"
        PE = f"P-{self.name}-{atm}-{expiry}"
        return {"CE": CE, "PE": PE, "ATM": atm}

    def get_current_df(self):
        end = datetime.now()
        start = end - timedelta(days=3)
        start = (time.mktime(start.timetuple())) + 19800
        end = (time.mktime(end.timetuple())) + 19800
        result = self.exchange.get_historical_data(symbol=self.symbol, start=str(start), end=str(end),
                                                   time_frame=str(self.time_frame) + 'm')
        df = pd.DataFrame(result['result'])
        df["date"] = pd.to_datetime(df['time'], unit='s') + pd.Timedelta(hours=5, minutes=30)
        df = df.sort_values(by='time', ascending=True)
        df = df.reset_index()
        new_df = calculate_heikin_ashi(df.copy(), 1)
        new_df['ema'] = new_df['HA_Close'].ewm(span=self.ema, adjust=False).mean()
        return new_df

    def place_paper_trade(self, strick, transaction_type):
        ltp = self.get_ltp(strick)
        self.current_sl = round(ltp + (self.strick_diff / 10), 2)
        self.current_trade[transaction_type] = {
            "date": datetime.now(),
            "strick": strick,
            "entry": ltp,
            "qunatiry": 1,
        }
        logger.info(f"Place trade for {strick} with {self.current_trade[transaction_type]}")

    def book_profit(self, strick_type):
        trade_data = self.current_trade[strick_type]
        ltp = self.get_ltp(trade_data["strick"])
        self.current_trade[strick_type]["exit_price"] = ltp
        self.current_trade[strick_type]["exit_date"] = datetime.now()
        logger.info(f"Booking Profit for {strick_type} with {self.current_trade[strick_type]}")
        self.save_csv(strick_type)

    def update_trade(self):
        if self.trade_type is None:
            return
        strick = self.current_trade[self.trade_type]["strick"]
        ltp = self.get_ltp(strick)
        logger.info(f"{strick}:Checking Again. Current LTP: {ltp} with SL: {self.current_sl}")
        if ltp >= self.current_sl:
            self.book_profit(self.trade_type)
            self.trade_type = None
            return
        if self.current_sl - ltp >= ((self.strick_diff*2)/10):
            self.current_sl = round(ltp + (self.strick_diff / 10), 2)

        if ltp <= round(self.current_trade[self.trade_type]["entry"] / 2, 2):
            self.book_profit(self.trade_type)
            strick = self.get_strick()
            cpe_strick = strick[self.trade_type]
            self.place_paper_trade(cpe_strick, self.trade_type)

    def start(self):
        while True:
            now_time = datetime.now()
            while now_time.minute % self.time_frame != 0 and self.trade_type is None:
                print(now_time.minute % self.time_frame, now_time.minute, "will wait for 60 sec and  try again")
                time.sleep(60)
                now_time = datetime.now()

            now = datetime.now()
            if now.hour == 17 and (24 <= now.minute <= 30) and self.trade_type is not None:
                self.book_profit(self.trade_type)
                logger.info("Now will wait for 15 min before new trade")
                time.sleep(300 * 3)
                self.trade_type = None
                continue
            if self.trade_type is None:
                df = self.get_current_df()
                ema_value = df['ema'].iloc[-1]
                ha_close = df['HA_Close'].iloc[-1]
                candle_type = df['Candle_Type'].iloc[-1]
                if ha_close > ema_value:
                    self.trade_type = "PE"
                    strick = self.get_strick()
                    pe_strick = strick[self.trade_type]
                    self.place_paper_trade(pe_strick, self.trade_type)
                elif ha_close < ema_value:
                    self.trade_type = "CE"
                    strick = self.get_strick()
                    ce_strick = strick[self.trade_type]
                    self.place_paper_trade(ce_strick, self.trade_type)
            logger.warning(f"Check Condition for {self.symbol} at {datetime.now()}")
            self.update_trade()
            time.sleep(60 * self.time_frame)


symbols = [
    {"key": "BTCUSD", "diff": 200, "name": "BTC"},
    {"key": "ETHUSD", "diff": 20, "name": "ETH"}
]
threads = []
for symbol in symbols:
    obj = EmaOptionSelling60(symbol=symbol.get("key"), strick_diff=symbol.get("diff"), name=symbol.get("name"))
    thread = threading.Thread(target=obj.start)
    thread.start()
    time.sleep(1)
    threads.append(thread)

for thread in threads:
    thread.join()

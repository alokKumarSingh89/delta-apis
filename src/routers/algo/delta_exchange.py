import requests


class DeltaExchange:
    def __init__(self):
        self.base_url = "https://api.india.delta.exchange/v2"

        self.headers = {"Accept": "application/json"}

    def list_index(self):
        res = requests.get(f"{self.base_url}/products")
        return res.json()

    def product_symbol(self, symbol):
        res = requests.get(
            f"{self.base_url}/products/{symbol}", params={}, headers=self.headers
        )
        return res.json()

    def ticker_symbol(self, symbol):
        res = requests.get(
            f"{self.base_url}/tickers/{symbol}", params={}, headers=self.headers
        )
        return res.json()

    def get_historical_data(self, symbol, start, end, time_frame="5m"):
        res = requests.get(
            f"{self.base_url}/history/candles",
            params={
                "resolution": time_frame,
                "symbol": symbol,
                "start": start,
                "end": end,
            },
            headers=self.headers,
        )
        return res.json()

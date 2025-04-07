import sqlite3

conn = sqlite3.connect("trade.db")


cursor = conn.cursor()


def create_db():
    # Create a table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trade (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument TEXT NOT NULL,
            entry_price TEXT NOT NULL,
            close_price TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time TEXT NOT NULL,
            quantity TEXT NOT NULL,
            trade_id TEXT NOT NULL,
            transaction_type TEXT NOT NULL
        )
    """)


create_db()

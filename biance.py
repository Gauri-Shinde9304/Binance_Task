# import pandas as pd
# import numpy as np
# from binance.client import Client
# from binance.enums import *
# import time
# from datetime import datetime
# import logging
# import os

# # === CONFIG ===
# API_KEY = '57d9a4a7d3b496acf3a12b702e62528c4f9f6b6282aa22c03bd9e67ad7fe47a2'
# API_SECRET = '11ca329f9438ae648dc6e303d47bc0aeefe80b6a8cbe42aed4e794a1cf111560'
# SYMBOL = 'BTCUSDT'
# INTERVAL = Client.KLINE_INTERVAL_1MINUTE
# QUANTITY = 1
# SL_POINTS = 300
# TP_POINTS = 200
# USE_TESTNET = True

# LOG_CSV_FILE = 'live_tradess.csv'

# # Setup logging
# logging.basicConfig(
#     filename='trading_bot.log',
#     level=logging.INFO,
#     format='%(asctime)s %(levelname)s: %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S'
# )
# console = logging.StreamHandler()
# console.setLevel(logging.INFO)
# formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
# console.setFormatter(formatter)
# logging.getLogger('').addHandler(console)

# client = Client(API_KEY, API_SECRET)
# if USE_TESTNET:
#     client.API_URL = 'https://testnet.binancefuture.com/fapi/v1'
#     logging.info("Running in TESTNET mode")
# else:
#     logging.info("Running in LIVE mode")

# def get_klines(symbol, interval, limit=100):
#     klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
#     df = pd.DataFrame(klines, columns=[
#         'timestamp', 'open', 'high', 'low', 'close', 'volume',
#         'close_time', 'quote_asset_volume', 'number_of_trades',
#         'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
#     ])
#     df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
#     df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
#     return df

# def calculate_indicators(df):
#     df['ema'] = df['close'].ewm(span=9).mean()
#     df['is_red'] = df['close'] < df['open']
#     df['is_green'] = df['close'] > df['open']
#     return df

# def get_position():
#     try:
#         positions = client.futures_position_information(symbol=SYMBOL)
#         for p in positions:
#             qty = float(p['positionAmt'])
#             if qty != 0:
#                 side = 'LONG' if qty > 0 else 'SHORT'
#                 return {'side': side, 'qty': abs(qty)}
#         return None
#     except Exception as e:
#         logging.error(f"Error getting position: {e}")
#         return None

# def close_position(side, quantity):
#     opposite = 'SELL' if side == 'LONG' else 'BUY'
#     try:
#         client.futures_create_order(
#             symbol=SYMBOL,
#             side=opposite,
#             type='MARKET',
#             quantity=quantity,
#             reduceOnly=True
#         )
#         logging.info(f"Closed {side} position of {quantity} {SYMBOL}")
#         return True
#     except Exception as e:
#         logging.error(f"Error closing position: {e}")
#         return False

# def place_order(side, quantity, sl_price, tp_price):
#     opposite = 'SELL' if side == 'BUY' else 'BUY'
#     try:
#         # Market Entry
#         order = client.futures_create_order(
#             symbol=SYMBOL,
#             side=side,
#             type='MARKET',
#             quantity=quantity
#         )
#         logging.info(f"Placed {side} MARKET order, qty={quantity}")
#         time.sleep(1)

#         # TP Limit Order
#         client.futures_create_order(
#             symbol=SYMBOL,
#             side=opposite,
#             type='LIMIT',
#             timeInForce='GTC',
#             quantity=quantity,
#             price=str(round(tp_price, 2)),
#             reduceOnly=True
#         )
#         logging.info(f"Placed TP LIMIT order at {tp_price}")

#         # SL Stop Market Order
#         client.futures_create_order(
#             symbol=SYMBOL,
#             side=opposite,
#             type='STOP_MARKET',
#             stopPrice=str(round(sl_price, 2)),
#             timeInForce='GTC',
#             quantity=quantity,
#             reduceOnly=True,
#             priceProtect=True
#         )
#         logging.info(f"Placed SL STOP_MARKET order at {sl_price}")

#         return order
#     except Exception as e:
#         logging.error(f"Error placing orders: {e}")
#         return None

# def append_to_csv(row):
#     file_exists = os.path.isfile(LOG_CSV_FILE)
#     df = pd.DataFrame([row])
#     if not file_exists:
#         df.to_csv(LOG_CSV_FILE, index=False)
#     else:
#         df.to_csv(LOG_CSV_FILE, mode='a', header=False, index=False)

# def strategy_loop():
#     ready_long = False
#     ready_short = False
#     entry_price = None
#     position_open = False
#     position_side = None
#     position_qty = 0

#     while True:
#         try:
#             df = get_klines(SYMBOL, INTERVAL)
#             df = calculate_indicators(df)

#             last_3 = df.iloc[-4:-1]
#             current = df.iloc[-1]

#             position = get_position()
#             if position:
#                 position_open = True
#                 position_side = position['side']
#                 position_qty = position['qty']
#                 logging.info(f"Current position: {position_side} qty={position_qty}")
#             else:
#                 position_open = False
#                 position_side = None
#                 position_qty = 0
#                 logging.info("No open positions")

#             # Entry logic
#             if not position_open:
#                 if not ready_long and not ready_short:
#                     if last_3['is_red'].all() and (last_3['close'] < last_3['ema']).all():
#                         ready_long = True
#                         logging.info(">> Ready for LONG setup")
#                     elif last_3['is_green'].all() and (last_3['close'] > last_3['ema']).all():
#                         ready_short = True
#                         logging.info(">> Ready for SHORT setup")

#                 if ready_long and current['is_green'] and current['close'] > current['ema']:
#                     entry_price = current['close']
#                     order = place_order('BUY', QUANTITY, entry_price - SL_POINTS, entry_price + TP_POINTS)
#                     if order:
#                         ready_long = False
#                         position_open = True
#                         position_side = 'LONG'
#                         position_qty = QUANTITY
#                         logging.info(f"Entered LONG at {entry_price}")
#                         csv_row = {
#                             'timestamp': current['timestamp'],
#                             'open': current['open'],
#                             'high': current['high'],
#                             'low': current['low'],
#                             'close': current['close'],
#                             'volume': current['volume'],
#                             'ema': current['ema'],
#                             'is_red': current['is_red'],
#                             'is_green': current['is_green'],
#                             'position_side': position_side,
#                             'position_qty': position_qty,
#                             'entry_price': entry_price,
#                             'exit_price': '',
#                             'pnl': '',
#                             'trade_result': ''
#                         }
#                         append_to_csv(csv_row)

#                 elif ready_short and current['is_red'] and current['close'] < current['ema']:
#                     entry_price = current['close']
#                     order = place_order('SELL', QUANTITY, entry_price + SL_POINTS, entry_price - TP_POINTS)
#                     if order:
#                         ready_short = False
#                         position_open = True
#                         position_side = 'SHORT'
#                         position_qty = QUANTITY
#                         logging.info(f"Entered SHORT at {entry_price}")
#                         csv_row = {
#                             'timestamp': current['timestamp'],
#                             'open': current['open'],
#                             'high': current['high'],
#                             'low': current['low'],
#                             'close': current['close'],
#                             'volume': current['volume'],
#                             'ema': current['ema'],
#                             'is_red': current['is_red'],
#                             'is_green': current['is_green'],
#                             'position_side': position_side,
#                             'position_qty': position_qty,
#                             'entry_price': entry_price,
#                             'exit_price': '',
#                             'pnl': '',
#                             'trade_result': ''
#                         }
#                         append_to_csv(csv_row)
#             else:
#                 logging.info("Position open, waiting for TP or SL")

#         except Exception as e:
#             logging.error(f"Strategy loop error: {e}")

#         time.sleep(60)

# if __name__ == "__main__":
#     logging.info("Starting trading bot")
#     strategy_loop()
import pandas as pd
import numpy as np
from binance.client import Client
from binance.enums import *
import time
from datetime import datetime
import logging
import os

# === CONFIG ===
API_KEY = '74165082c12c015a7daede088bbe611c7c81c1fc878df69bfcd0e62b1c01b908'
API_SECRET = 'aa685ac966359366134c0094c7f8979841622e8e51e8e750398321f6cfa19756'
SYMBOL = 'BTCUSDT'
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
QUANTITY = 0.03
SL_POINTS = 200
TP_POINTS = 130
USE_TESTNET = True

LOG_CSV_FILE = 'btclive_tradess.csv'

# Setup logging
logging.basicConfig(
    filename='trading_bot.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

client = Client(API_KEY, API_SECRET)
if USE_TESTNET:
    client.API_URL = 'https://testnet.binancefuture.com/fapi/v1'
    client.FUTURES_URL = 'https://testnet.binancefuture.com/fapi'
    logging.info("Running in TESTNET mode")
else:
    logging.info("Running in LIVE mode")

def get_klines(symbol, interval, limit=100):
    klines = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

def calculate_indicators(df):
    df['ema'] = df['close'].ewm(span=9).mean()
    df['is_red'] = df['close'] < df['open']
    df['is_green'] = df['close'] > df['open']
    return df

def get_position():
    try:
        positions = client.futures_position_information(symbol=SYMBOL)
        for p in positions:
            qty = float(p['positionAmt'])
            if qty != 0:
                side = 'LONG' if qty > 0 else 'SHORT'
                return {'side': side, 'qty': abs(qty)}
        return None
    except Exception as e:
        logging.error(f"Error getting position: {e}")
        return None

def close_position(side, quantity):
    opposite = 'SELL' if side == 'LONG' else 'BUY'
    try:
        client.futures_create_order(
            symbol=SYMBOL,
            side=opposite,
            type='MARKET',
            quantity=quantity,
            reduceOnly=True
        )
        logging.info(f"Closed {side} position of {quantity} {SYMBOL}")
        return True
    except Exception as e:
        logging.error(f"Error closing position: {e}")
        return False

def place_order(side, quantity, sl_price, tp_price):
    opposite = 'SELL' if side == 'BUY' else 'BUY'
    try:
        # Market Entry
        order = client.futures_create_order(
            symbol=SYMBOL,
            side=side,
            type='MARKET',
            quantity=quantity
        )
        logging.info(f"Placed {side} MARKET order, qty={quantity}")
        time.sleep(1)

        # TP Limit Order
        client.futures_create_order(
            symbol=SYMBOL,
            side=opposite,
            type='LIMIT',
            timeInForce='GTC',
            quantity=quantity,
            price=str(round(tp_price, 2)),
            reduceOnly=True
        )
        logging.info(f"Placed TP LIMIT order at {tp_price}")

        # SL Stop Market Order
        client.futures_create_order(
            symbol=SYMBOL,
            side=opposite,
            type='STOP_MARKET',
            stopPrice=str(round(sl_price, 2)),
            timeInForce='GTC',
            quantity=quantity,
            reduceOnly=True,
            priceProtect=True
        )
        logging.info(f"Placed SL STOP_MARKET order at {sl_price}")

        return order
    except Exception as e:
        logging.error(f"Error placing orders: {e}")
        return None

def append_to_csv(row):
    file_exists = os.path.isfile(LOG_CSV_FILE)
    df = pd.DataFrame([row])
    if not file_exists:
        df.to_csv(LOG_CSV_FILE, index=False)
    else:
        df.to_csv(LOG_CSV_FILE, mode='a', header=False, index=False)

def update_last_trade(exit_price, pnl, trade_result):
    if not os.path.exists(LOG_CSV_FILE):
        logging.warning("Log file does not exist to update last trade.")
        return

    df = pd.read_csv(LOG_CSV_FILE)
    if df.empty:
        logging.warning("Log file is empty, cannot update last trade.")
        return

    # Update the last row
    df.iloc[-1, df.columns.get_loc("exit_price")] = exit_price
    df.iloc[-1, df.columns.get_loc("pnl")] = pnl
    df.iloc[-1, df.columns.get_loc("trade_result")] = trade_result

    df.to_csv(LOG_CSV_FILE, index=False)
    logging.info(f"Trade updated with exit_price: {exit_price}, pnl: {pnl}, result: {trade_result}")

def strategy_loop():
    ready_long = False
    ready_short = False
    entry_price = None
    position_open = False
    position_side = None
    position_qty = 0

    while True:
        try:
            df = get_klines(SYMBOL, INTERVAL)
            df = calculate_indicators(df)

            last_3 = df.iloc[-4:-1]
            current = df.iloc[-1]

            position = get_position()
            if position:
                position_open = True
                position_side = position['side']
                position_qty = position['qty']
                logging.info(f"Current position: {position_side} qty={position_qty}")
            else:
                # if previously open but now closed
                if position_open:
                    exit_price = current['close']
                    if position_side == 'LONG':
                        pnl = round((exit_price - entry_price) * QUANTITY, 2)
                    else:  # SHORT
                        pnl = round((entry_price - exit_price) * QUANTITY, 2)
                    trade_result = 'WIN' if pnl > 0 else 'LOSS'
                    update_last_trade(exit_price, pnl, trade_result)

                position_open = False
                position_side = None
                position_qty = 0
                entry_price = None
                logging.info("No open positions")

            # Entry logic
            if not position_open:
                if not ready_long and not ready_short:
                    if last_3['is_red'].all() and (last_3['close'] < last_3['ema']).all():
                        ready_long = True
                        logging.info(">> Ready for LONG setup")
                    elif last_3['is_green'].all() and (last_3['close'] > last_3['ema']).all():
                        ready_short = True
                        logging.info(">> Ready for SHORT setup")

                if ready_long and current['is_green'] and current['close'] > current['ema']:
                    entry_price = current['close']
                    order = place_order('BUY', QUANTITY, entry_price - SL_POINTS, entry_price + TP_POINTS)
                    if order:
                        ready_long = False
                        position_open = True
                        position_side = 'LONG'
                        position_qty = QUANTITY
                        logging.info(f"Entered LONG at {entry_price}")
                        csv_row = {
                            'timestamp': current['timestamp'],
                            'open': current['open'],
                            'high': current['high'],
                            'low': current['low'],
                            'close': current['close'],
                            'volume': current['volume'],
                            'ema': current['ema'],
                            'is_red': current['is_red'],
                            'is_green': current['is_green'],
                            'position_side': position_side,
                            'position_qty': position_qty,
                            'entry_price': entry_price,
                            'exit_price': '',
                            'pnl': '',
                            'trade_result': ''
                        }
                        append_to_csv(csv_row)

                elif ready_short and current['is_red'] and current['close'] < current['ema']:
                    entry_price = current['close']
                    order = place_order('SELL', QUANTITY, entry_price + SL_POINTS, entry_price - TP_POINTS)
                    if order:
                        ready_short = False
                        position_open = True
                        position_side = 'SHORT'
                        position_qty = QUANTITY
                        logging.info(f"Entered SHORT at {entry_price}")
                        csv_row = {
                            'timestamp': current['timestamp'],
                            'open': current['open'],
                            'high': current['high'],
                            'low': current['low'],
                            'close': current['close'],
                            'volume': current['volume'],
                            'ema': current['ema'],
                            'is_red': current['is_red'],
                            'is_green': current['is_green'],
                            'position_side': position_side,
                            'position_qty': position_qty,
                            'entry_price': entry_price,
                            'exit_price': '',
                            'pnl': '',
                            'trade_result': ''
                        }
                        append_to_csv(csv_row)

        except Exception as e:
            logging.error(f"Strategy loop error: {e}")

        time.sleep(60)

if __name__ == "__main__":
    logging.info("Starting trading bot")
    strategy_loop()

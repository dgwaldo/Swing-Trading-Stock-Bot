import biz_bot_scrape as bb1
import pandas as pd
from datetime import datetime, timedelta, timezone
from alpaca.common.enums import Sort
from alpaca.common.exceptions import APIError
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest
import config, time, math


def get_buying_power(account):
    if isinstance(account, dict):
        return float(account.get('buying_power') or 0.0)
    return float(account.buying_power or 0.0)


def remaining_capital(capital_limit, positions, pending_buy_orders):
    invested = sum(abs(float(position.market_value)) for position in positions)
    reserved = 0.0
    for order in pending_buy_orders:
        if order.notional is not None:
            reserved += float(order.notional)
        elif order.limit_price is not None and order.qty is not None:
            remaining_qty = max(float(order.qty) - float(order.filled_qty or 0), 0)
            reserved += remaining_qty * float(order.limit_price)
        else:
            return 0.0
    return max(capital_limit - invested - reserved, 0.0)


def get_latest_minute_price(data_client, symbol):
    end = datetime.now(timezone.utc)
    bars = data_client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame(1, TimeFrameUnit('Min')),
        start=end - timedelta(days=7),
        end=end,
        limit=1,
        feed=DataFeed.IEX,
        sort=Sort.DESC
    )).df
    if bars.empty:
        return None

    stock_price = float(bars.iloc[-1]['close'])
    if not math.isfinite(stock_price) or stock_price <= 0:
        return None
    return stock_price


##################################################-SETUP-##################################################
trading_client = TradingClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY)
capital_limit = float(getattr(config, 'MAX_CAPITAL', 500.0))
if not math.isfinite(capital_limit) or capital_limit <= 0:
    raise ValueError('MAX_CAPITAL must be a finite positive amount')
account = trading_client.get_account() # get account info
buying_power = get_buying_power(account)
print('${} is available as buying power.'.format(buying_power)) # check buying power


##################################################-FINAL CRITERIA FOR BUYING-##################################################
print('these are the best stocks to buy, if available:')
print(bb1.buy_stocks[['symbol', 'close', 'sma10', 'sma200', 'rsi']])
buy_stocks = bb1.buy_stocks['symbol'].tolist() # create a list of the stocks above
buy_stocks_list = [] # final buy list

for stock in buy_stocks:
    # we want to ensure we can afford each stock on our buy list
    # this loop filters out stocks we cannot afford by taking each element in buy_stocks, pulling its current price from the API, and adding it to our new list
    stock_price = get_latest_minute_price(data_client, stock)
    if stock_price is None:
        print(f'No valid recent minute bar for {stock}; skipping it')
        continue
    if stock_price < buying_power: # check if the stock's price is less than our buying power
        buy_stocks_list.append(stock)

# might add current price scraper here if needed


##################################################-BUY STOCKS-##################################################
while True: # will break when I don't want the bot to buy more stocks
    account = trading_client.get_account() # refresh account info
    buying_power = get_buying_power(account)
    portfolio = trading_client.get_all_positions()
    if buy_stocks_list: # check if there are stocks to buy
        pending_buy_orders = trading_client.get_orders(filter=GetOrdersRequest(
            status=QueryOrderStatus.OPEN,
            side=OrderSide.BUY,
            limit=500
        ))
        capital_left = remaining_capital(capital_limit, portfolio, pending_buy_orders)

        for stock in buy_stocks_list:
            """
            This loop ensures that we buy a similar ratio of each stock rather than buying the same quantity of each stock.
            If one stock has a price of $1000 and one has a price of $100, for example, we don't want ten shares of each stock.
            We'd rather have one share of stock one and ten shares of stock two to ensure our portfolio is more diversified
            """
            stock_price = get_latest_minute_price(data_client, stock)
            if stock_price is None:
                print(f'No valid recent minute bar for {stock}; skipping it')
                continue
            equity_limit = 600 # maximum equity you want to own of each stock
            buy_qty = 0

            while equity_limit > stock_price:
                buy_qty += 1 # increase buy quantity
                equity_limit -= stock_price # decrease equity_limit variable by the stock price after each iteration

            if buy_qty == 0:
                print(f'{stock} is above the per-stock equity limit; skipping it')
                continue

            affordable_qty = math.floor(min(capital_left, buying_power) / stock_price)
            buy_qty = min(buy_qty, affordable_qty)
            if buy_qty == 0:
                print(f'{stock} would exceed the remaining ${capital_limit:.2f} allocation; skipping it')
                continue

            # the following is currently not being used, but I will leave it here in case I want to use it again
            # if equity_limit < float(account.buying_power):
            #     buy_qty = math.floor(float(account.buying_power)/stock_price) # buy maximum number of stocks available with our buying power
            # else:
            #     pass

            try:
                # submit order for each stock in loop w/ our qty determined by our ratio calculator above
                trading_client.submit_order(order_data=MarketOrderRequest(
                    symbol=stock,
                    qty=buy_qty,
                    side=OrderSide.BUY,
                    type=OrderType.MARKET,
                    time_in_force=TimeInForce.GTC
                ))
                print(f'{buy_qty} shares of {stock} will be bought')
                capital_left -= buy_qty * stock_price
            except APIError:
                print("Insufficient buying power for best available stocks")
                break

    else:
        print("Either none of our scanned stocks meet our buying criteria or you don't have sufficient buying power")
        break
    break

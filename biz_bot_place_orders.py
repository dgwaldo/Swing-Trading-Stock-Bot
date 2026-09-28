import biz_bot_scrape as bb1
import pandas as pd
from alpaca.common.exceptions import APIError
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
import config, time, math

##################################################-SETUP-##################################################
trading_client = TradingClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY)
account = trading_client.get_account() # get account info
print('${} is available as buying power.'.format(account.buying_power)) # check buying power


##################################################-FINAL CRITERIA FOR BUYING-##################################################
print('these are the best stocks to buy, if available:')
print(bb1.buy_stocks[['symbol', 'close', 'sma10', 'sma200', 'rsi']])
buy_stocks = bb1.buy_stocks['symbol'].tolist() # create a list of the stocks above
buy_stocks_list = [] # final buy list

for stock in buy_stocks:
    # we want to ensure we can afford each stock on our buy list
    # this loop filters out stocks we cannot afford by taking each element in buy_stocks, pulling its current price from the API, and adding it to our new list
    bars = data_client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols=stock,
        timeframe=TimeFrame.Minute,
        limit=1
    )).df
    stock_price = bars.iloc[-1]['close'] #get current price of stock
    if stock_price < float(account.buying_power): # check if the stock's price is less than our buying power
        buy_stocks_list.append(stock)

# might add current price scraper here if needed


##################################################-BUY STOCKS-##################################################
while True: # will break when I don't want the bot to buy more stocks
    account = trading_client.get_account() # refresh account info
    portfolio = trading_client.get_all_positions()
    if buy_stocks_list: # check if there are stocks to buy

        for stock in buy_stocks_list:
            """
            This loop ensures that we buy a similar ratio of each stock rather than buying the same quantity of each stock.
            If one stock has a price of $1000 and one has a price of $100, for example, we don't want ten shares of each stock.
            We'd rather have one share of stock one and ten shares of stock two to ensure our portfolio is more diversified
            """
            bars = data_client.get_stock_bars(StockBarsRequest(
                symbol_or_symbols=stock,
                timeframe=TimeFrame.Minute,
                limit=1
            )).df
            stock_price = bars.iloc[-1]['close'] #get current price
            equity_limit = 600 # maximum equity you want to own of each stock
            buy_qty = 0

            while equity_limit > stock_price:
                buy_qty += 1 # increase buy quantity
                equity_limit -= stock_price # decrease equity_limit variable by the stock price after each iteration

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
            except APIError:
                print("Insufficient buying power for best available stocks")
                break

    else:
        print("Either none of our scanned stocks meet our buying criteria or you don't have sufficient buying power")
        break
    break

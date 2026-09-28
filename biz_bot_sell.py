import biz_bot_scrape as bb1
import pandas as pd
from alpaca.common.exceptions import APIError
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
import config
import ta
from datetime import *

##################################################-SETUP-##################################################
trading_client = TradingClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY)
portfolio = trading_client.get_all_positions() # get account info


##################################################-FIND CURRENT POSITIONS-##################################################
# create empty list for current holdings and quantity held
current_holdings_df = pd.DataFrame()
current_holdings = []
holding_qty = []
equity_owned = []
current_price = []

# loop used for getting data about currently owned stocks
i=0 # used for indexing each item in our portfolio - will increase with each iteration of the loop
for stock in portfolio:
    current_holdings.append(portfolio[i].symbol)
    holding_qty.append(portfolio[i].qty)
    equity_owned.append(portfolio[i].market_value)
    current_price.append(portfolio[i].current_price)
    i+=1

if not current_holdings:
    print('No open positions to sell')
    raise SystemExit(0)

# append each list to our dataframe
current_holdings_df['symbol'] = current_holdings

holding_qty = [float(i) for i in holding_qty]
current_holdings_df['qty_owned'] = holding_qty

equity_owned = [float(i) for i in equity_owned]
current_holdings_df['equity_owned'] = equity_owned

current_price = [float(i) for i in current_price]
current_holdings_df['current_price'] = current_price


##################################################-SCRAPE DATA FOR CURRENT HOLDINGS-##################################################
symbols = current_holdings

symbols = [symbol.split(',')[0].strip() for symbol in symbols] # use this line for QQQ holdings
#symbols = [holding.split(',')[0].strip() for holding in holdings][1:] # use this line for Wilshire 5000
symbols = ",".join(symbols)

bars = data_client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols=symbols.split(','),
    timeframe=TimeFrame.Day,
    limit=201
)).df
if bars.empty:
    bars = pd.DataFrame(columns=['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume'])
else:
    bars = bars.reset_index().sort_values(['symbol', 'timestamp'])


##################################################-SET UP DATA CONTAINERS-##################################################
df = pd.DataFrame() # create empty dataframe
# create empty lists for each piece of data we're scraping
time_list = []
open_list = []
high_list = []
low_list = []
close_list = []
volume_list = []
symbol_list = []


##################################################-SCRAPE DATA-##################################################
for _, bar in bars.iterrows():
    t = bar['timestamp'].to_pydatetime()
    day = t.strftime('%Y-%m-%d')
    time_list.append(day)
    open_list.append(bar['open'])
    high_list.append(bar['high'])
    low_list.append(bar['low'])
    close_list.append(bar['close'])
    volume_list.append(bar['volume'])
    symbol_list.append(bar['symbol'])
# append each list to its own column in df
df['symbol'] = symbol_list
df['time'] = time_list
df['open'] = open_list
df['high'] = high_list
df['low'] = low_list
df['close'] = close_list
df['volume'] = volume_list


##################################################-CALCULATE PIVOT POINT AND RESISTANCE LEVEL-##################################################
df['pivot_point'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1))/3
df['r1'] = (2*df['pivot_point']) - df['low'].shift(1)
df['s1'] = (2*df['pivot_point']) - df['high'].shift(1)
df['r2'] = (df['pivot_point'] - df['s1']) + (df['r1'])
df['take_profit'] = ((df['r2'] - df['close'].shift(1))*.75) + df['close'].shift(1)


##################################################-ADDING IN INDICATORS-##################################################
df['sma2'] = ta.trend.sma_indicator(df['close'], window=2)
df['sma5'] = ta.trend.sma_indicator(df['close'], window=5)
df['sma10'] = ta.trend.sma_indicator(df['close'], window=10)
df['sma20'] = ta.trend.sma_indicator(df['close'], window=20)
df['sma200'] = ta.trend.sma_indicator(df['close'], window=200)
df['rsi'] = ta.momentum.rsi(df['close'], window=6, fillna=False)


##################################################-JOIN THE TWO DATAFRAMES-##################################################
today = str(date.today())
df = df.loc[df['time']==today] # we only want today's records

df = df.merge(current_holdings_df, on='symbol', how='inner')


##################################################-CRITERIA FOR SELLING-##################################################
sell_df = df.loc[

                        ##########-(RSI > 70)-##########
                        (df['rsi'] > 70)

                        ##########-CLOSE HOLDS BELOW SMA10 LINE-##########
                    |   (
                        (df['close'].shift(1) < df['sma10'].shift(1)) & (df['close'] < df['sma10'])
                        )

                        ##########-CURRENT PRICE REACHES RESISTANCE LEVEL 2-##########
                    |   (df['current_price'] >= df['take_profit']) # CURRENT PRICE REACHES 75% OF RESISTANCE LEVEL 2 - NOT CURRENTLY USING
                #    | (df['current_price'] >=df['r2'])


                        ##########-CLOSE DIPS BELOW LONG-TERM SMA-##########
                    |   (df['close'] < df['sma200'])

                    ]


##################################################-SELL STOCKS-##################################################
if sell_df.empty == False: # if there are stocks to sell
    portfolio = trading_client.get_all_positions()
    print(f"stocks being sold: {list(sell_df['symbol'])}")
    i=0 # used for indexing
    for stock in sell_df['symbol']:
        try:
            trading_client.submit_order(order_data=MarketOrderRequest(
                symbol=sell_df['symbol'].iloc[i],
                qty=sell_df['qty_owned'].iloc[i],
                side=OrderSide.SELL,
                type=OrderType.MARKET,
                time_in_force=TimeInForce.GTC
            ))
            print(f'{stock} sold')
            i+=1
        except APIError:
            print(f"Either your order to sell {stock} hasn't been filled, or daytrade protection has been activated")
            continue

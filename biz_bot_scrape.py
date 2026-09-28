import config, time, ta
import pandas as pd
from datetime import datetime, timedelta, date
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient

##################################################-SETUP-##################################################
trading_client = TradingClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY)
portfolio = trading_client.get_all_positions()


##################################################-GET LIST OF SYMBOLS-##################################################
holdings=open('data/holdings.csv').readlines() # read csv of QQQ holdings - should be able to use any csv
#holdings=open('data/WILSHIRE-5000-Stock-Tickers-List.csv').readlines() # read csv of Wilshire 5000 - not using right now as I can only pass in 200 symbols

# pull symbols from holdings csv, assigns it to symbols variable (list of symbols)
symbols = [holding.split(',')[2].strip() for holding in holdings][1:] # use this line for QQQ holdings
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


##################################################-ADDING IN INDICATORS-##################################################
df['sma2'] = ta.trend.sma_indicator(df['close'], window=2)
df['sma5'] = ta.trend.sma_indicator(df['close'], window=5)
df['sma10'] = ta.trend.sma_indicator(df['close'], window=10)
df['sma20'] = ta.trend.sma_indicator(df['close'], window=20)
df['sma200'] = ta.trend.sma_indicator(df['close'], window=200)
df['rsi'] = ta.momentum.rsi(df['close'], window=6, fillna=False)


##################################################-CALCULATE PIVOT POINT AND RESISTANCE LEVEL-##################################################
df['pivot_point'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1))/3
df['r1'] = (2*df['pivot_point']) - df['low'].shift(1)
df['s1'] = (2*df['pivot_point']) - df['high'].shift(1)
df['r2'] = (df['pivot_point'] - df['s1']) + (df['r1'])
df['take_profit'] = ((df['r2'] - df['close'].shift(1))*.75) + df['close'].shift(1)

# for now, we will just trade on these levels
# if more are needed, they can be found and explained here:
# https://www.daytrading.com/pivot-points#:~:text=Calculation%20of%20Pivot%20Points,-Pivots%20points%20can&text=The%20central%20price%20level%20%E2%80%93%20the,or%20period%2C%20more%20generally).&text=Resistance%201%20%3D%20(2%20x%20Pivot,)%20%E2%80%93%20High%20(previous%20period)

##################################################-ADDING IN TIME-##################################################
# add in time - make sure the bot is not trying to trade based on the price of non-trading days
today = date.today()

# conditions to use last trading days as variables
if today.weekday() == 6: # sunday
    yesterday = today - timedelta(days=2)
    yesterday = yesterday.strftime('%Y-%m-%d')

    two_days_ago = today - timedelta(days=3)
    two_days_ago = two_days_ago.strftime('%Y-%m-%d')

    three_days_ago = today - timedelta(days=4)
    three_days_ago = three_days_ago.strftime('%Y-%m-%d')

    four_days_ago = today - timedelta(days=5)
    four_days_ago = four_days_ago.strftime('%Y-%m-%d')

if today.weekday() == 0: # monday
    yesterday = today - timedelta(days=3)
    yesterday = yesterday.strftime('%Y-%m-%d')

    two_days_ago = today -timedelta(days=4)
    two_days_ago = two_days_ago.strftime('%Y-%m-%d')

    three_days_ago = today - timedelta(days=5)
    three_days_ago = three_days_ago.strftime('%Y-%m-%d')

    four_days_ago = today - timedelta(days=6)
    four_days_ago = four_days_ago.strftime('%Y-%m-%d')

if today.weekday() == 1: # tuesday
    yesterday = today - timedelta(days=1)
    yesterday = yesterday.strftime('%Y-%m-%d')

    two_days_ago = today - timedelta(days=4)
    two_days_ago = two_days_ago.strftime('%Y-%m-%d')

    three_days_ago = today - timedelta(days=5)
    three_days_ago = three_days_ago.strftime('%Y-%m-%d')

    four_days_ago = today - timedelta(days=6)
    four_days_ago = four_days_ago.strftime('%Y-%m-%d')

if today.weekday() == 2: # wednesday
    yesterday = today - timedelta(days=1)
    yesterday = yesterday.strftime('%Y-%m-%d')

    two_days_ago = today - timedelta(days=2)
    two_days_ago = two_days_ago.strftime('%Y-%m-%d')

    three_days_ago = today - timedelta(days=5)
    three_days_ago = three_days_ago.strftime('%Y-%m-%d')

    four_days_ago = today - timedelta(days=6)
    four_days_ago = four_days_ago.strftime('%Y-%m-%d')

if today.weekday() == 3: # thursday
    yesterday = today - timedelta(days=1)
    yesterday = yesterday.strftime('%Y-%m-%d')

    two_days_ago = today - timedelta(days=2)
    two_days_ago = two_days_ago.strftime('%Y-%m-%d')

    three_days_ago = today - timedelta(days=3)
    three_days_ago = three_days_ago.strftime('%Y-%m-%d')

    four_days_ago = today - timedelta(days=6)
    four_days_ago = four_days_ago.strftime('%Y-%m-%d')

if today.weekday() == 4 or today.weekday() == 5: # friday or saturday
    yesterday = today - timedelta(days=1)
    yesterday = yesterday.strftime('%Y-%m-%d')

    two_days_ago = today - timedelta(days=2)
    two_days_ago = two_days_ago.strftime('%Y-%m-%d')

    three_days_ago = today - timedelta(days=3)
    three_days_ago = three_days_ago.strftime('%Y-%m-%d')

    four_days_ago = today - timedelta(days=4)
    four_days_ago = four_days_ago.strftime('%Y-%m-%d')

today = today.strftime('%Y-%m-%d')


##################################################-FILTER DATA-##################################################
# first, let's only work with the last three days of data
big_money_df = df.loc[(df['time']==today) |
                      (df['time']==yesterday) |
                      (df['time']==two_days_ago) |
                      (df['time']==three_days_ago)].copy() # only take records from up to three days ago


big_money_df.loc[:, 'above_sma10'] = (big_money_df['close'] > big_money_df['sma10']) # a simple column to detect if a stock is above or below the SMA 10-day line
# setwithcopy warning - uncomment the following to ensure the code worked correctly
# print((big_money_df['close'] > big_money_df['sma5']).sum())
# print(big_money_df['above_sma5'].value_counts())
# first value should match the true values

buy_stocks = big_money_df.loc[

                            ##########-RSI LESS THAN 70-##########
                            (big_money_df['rsi'] < 70)


                            ##########-CHECK IF SMA LINE HAS BEEN CROSSED-##########
                            # three days ago, the price action was below the SMA line
                            # two days ago and yesterday, the price action was above the SMA line
                            # we want to know if the price action has held above the SMA line for two days in a row after being below it
                            & (big_money_df['above_sma10'].shift(3) == False) # below SMA 3 days ago
                            & (big_money_df['above_sma10'].shift(2) == True) # above SMA 2 days ago
                            & (big_money_df['above_sma10'].shift(1) == True) # above SMA yesterday
                            & (big_money_df['above_sma10'] == True) # above SMA today
                            & (big_money_df['close'].shift(1) > big_money_df['sma200'])


                            ##########-CHECK IF SHORT TERM SMA > LONG TERM SMA FOR THREE DAYS-##########
                            & (big_money_df['sma10'] > big_money_df['sma200']) # today
                            & (big_money_df['sma10'].shift(1) > big_money_df['sma200'].shift(1)) # yesterday
                            & (big_money_df['sma10'].shift(2) > big_money_df['sma200'].shift(2)) # two days ago


                            ##########-ONLY RETURN RECORDS FROM TODAY-##########
                            & (big_money_df['time']==today)

                            ##########-CLOSE IS LESS THAN RESISTANCE LEVEL 2-##########
                            & (big_money_df['close'].shift(1) <=big_money_df['r2'])

                            & (big_money_df['close'].shift(1) <= big_money_df['take_profit']) # CURRENT PRICE REACHES 75% OF RESISTANCE LEVEL 2 - NOT CURRENTLY USING


                                ]


buy_stocks = buy_stocks.sort_values(by=['rsi']) # sort values by RSI

# don't buy more of a stock that we already own our desired equity of
my_symbols = []
for symbol in portfolio:
    my_symbols.append(symbol.symbol)

buy_stocks = buy_stocks[~buy_stocks.symbol.isin(my_symbols)]

#print(buy_stocks[['symbol', 'close', 'sma10', 'above_sma10', 'rsi']])
# print('these are the best stocks to buy, if available:')
#print(buy_stocks[['symbol', 'close', 'sma10', 'sma200', 'r2', 'rsi']])
#print(buy_stocks[['symbol', 'close', 'take_profit', 'r2']])



"""
The following takes into account the current price of each stock in our buy list. This slows down the bot tremendously and, since I don't
want to day trade, having the exact current price at any given time is not super important. I will leave the code here in case I decide to use it once
again.

##################################################-REMOVE IF CURRENT PRICE < SMA10 -##################################################
# construct that should avoid daytrades - may no longer be needed with sma10 if it works well enough (was meant to help sma5 issue)
data_client = StockHistoricalDataClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY)

# WILL NOT WORK IF NON-TRADING DAY
price_list = []
for stock in stocks_to_buy:
    bars = data_client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols=stock,
        timeframe=TimeFrame.Minute,
        limit=1
    )).df
    stock_price = bars.iloc[-1]['close'] #get current price
    price_list.append(stock_price)
buy_stocks['current_price'] = price_list

buy_stocks = buy_stocks[buy_stocks['time']==today]
buy_stocks = buy_stocks[buy_stocks.current_price >= buy_stocks.sma5]
# print(buy_stocks[['symbol', 'close', 'sma5', 'above_sma5', 'sma200']])

buy_stocks = buy_stocks.loc[(buy_stocks['current_price'] > buy_stocks['sma10'])]
buy_stocks = buy_stocks.sort_values(by=['rsi'])
#print(buy_stocks[['symbol', 'sma10', 'current_price', 'rsi']])

# PROBLEM - sma5 was super reactive - EA constantly fluctuated between a buy and a sell, which triggered
# lots of day trades. Going to try the bot with SMA10 for a while

"""

import config, time, ta
import pandas as pd
from datetime import datetime, timedelta, timezone
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient


def fetch_daily_bars(data_client, symbols):
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=320)
    batches = []

    for offset in range(0, len(symbols), 40):
        bars = data_client.get_stock_bars(StockBarsRequest(
            symbol_or_symbols=symbols[offset:offset + 40],
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
            limit=10000,
            feed=DataFeed.IEX
        )).df
        if not bars.empty:
            batches.append(bars.reset_index())

    if not batches:
        return pd.DataFrame(columns=['symbol', 'timestamp', 'open', 'high', 'low', 'close', 'volume'])

    return pd.concat(batches, ignore_index=True).sort_values(['symbol', 'timestamp'])


##################################################-SETUP-##################################################
trading_client = TradingClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(config.APCA_API_KEY_ID, config.APCA_API_SECRET_KEY)
portfolio = trading_client.get_all_positions()


##################################################-GET LIST OF SYMBOLS-##################################################
holdings = pd.read_csv('data/holdings.csv', dtype={'Holding Ticker': 'string'})
snapshot_dates = pd.to_datetime(holdings['Date'], format='mixed', errors='coerce')
latest_snapshot = snapshot_dates.max()
symbols = holdings.loc[snapshot_dates == latest_snapshot, 'Holding Ticker'].dropna().str.strip().tolist()
if not symbols:
    raise RuntimeError('No scanner symbols found in data/holdings.csv')
symbols = ",".join(symbols)

bars = fetch_daily_bars(data_client, symbols.split(','))
if bars.empty:
    raise RuntimeError('Alpaca returned no daily bars; check market-data access and the scanner universe')
else:
    bars = bars.reset_index().sort_values(['symbol', 'timestamp'])
    missing_symbols = sorted(set(symbols.split(',')) - set(bars['symbol']))
    if missing_symbols:
        print(f'No daily bars returned for {len(missing_symbols)} scanner symbols: {", ".join(missing_symbols)}')


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
for window in (2, 5, 10, 20, 200):
    df[f'sma{window}'] = df.groupby('symbol', sort=False)['close'].transform(
        lambda close: ta.trend.sma_indicator(close, window=window)
    )
df['rsi'] = df.groupby('symbol', sort=False)['close'].transform(
    lambda close: ta.momentum.rsi(close, window=6, fillna=False)
)


##################################################-CALCULATE PIVOT POINT AND RESISTANCE LEVEL-##################################################
previous_bars = df.groupby('symbol', sort=False)[['high', 'low', 'close']].shift(1)
df['pivot_point'] = (previous_bars['high'] + previous_bars['low'] + previous_bars['close'])/3
df['r1'] = (2*df['pivot_point']) - previous_bars['low']
df['s1'] = (2*df['pivot_point']) - previous_bars['high']
df['r2'] = (df['pivot_point'] - df['s1']) + (df['r1'])
df['take_profit'] = ((df['r2'] - previous_bars['close'])*.75) + previous_bars['close']

# for now, we will just trade on these levels
# if more are needed, they can be found and explained here:
# https://www.daytrading.com/pivot-points#:~:text=Calculation%20of%20Pivot%20Points,-Pivots%20points%20can&text=The%20central%20price%20level%20%E2%80%93%20the,or%20period%2C%20more%20generally).&text=Resistance%201%20%3D%20(2%20x%20Pivot,)%20%E2%80%93%20High%20(previous%20period)

##################################################-FILTER DATA-##################################################
big_money_df = df.groupby('symbol', sort=False).tail(4).copy()


big_money_df.loc[:, 'above_sma10'] = (big_money_df['close'] > big_money_df['sma10']) # a simple column to detect if a stock is above or below the SMA 10-day line
big_money_df.loc[:, 'is_latest_bar'] = big_money_df['time'].eq(
    big_money_df.groupby('symbol', sort=False)['time'].transform('max')
)
symbol_groups = big_money_df.groupby('symbol', sort=False)
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
                            & (symbol_groups['above_sma10'].shift(3) == False) # below SMA 3 days ago
                            & (symbol_groups['above_sma10'].shift(2) == True) # above SMA 2 days ago
                            & (symbol_groups['above_sma10'].shift(1) == True) # above SMA yesterday
                            & (big_money_df['above_sma10'] == True) # above SMA today
                            & (symbol_groups['close'].shift(1) > big_money_df['sma200'])


                            ##########-CHECK IF SHORT TERM SMA > LONG TERM SMA FOR THREE DAYS-##########
                            & (big_money_df['sma10'] > big_money_df['sma200']) # today
                            & (symbol_groups['sma10'].shift(1) > symbol_groups['sma200'].shift(1)) # yesterday
                            & (symbol_groups['sma10'].shift(2) > symbol_groups['sma200'].shift(2)) # two days ago


                            ##########-ONLY RETURN RECORDS FROM TODAY-##########
                            & big_money_df['is_latest_bar']

                            ##########-CLOSE IS LESS THAN RESISTANCE LEVEL 2-##########
                            & (symbol_groups['close'].shift(1) <= big_money_df['r2'])

                            & (symbol_groups['close'].shift(1) <= big_money_df['take_profit']) # CURRENT PRICE REACHES 75% OF RESISTANCE LEVEL 2 - NOT CURRENTLY USING


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

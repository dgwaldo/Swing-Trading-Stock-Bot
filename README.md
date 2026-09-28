# Swing-Trading-Stock-Bot

## Project Overview
A Python-based bot that uses the Alpaca API and swing trading principles to buy and sell securities. This bot has four scripts - one that scrapes data and calculates technical indicators, one that buys securities, one that sells securities, and a final script that calls the other scripts in a loop to run constantly. Currently, the bot buys and sells based on indicators that I pass to it. The bot currently only paper trades as I'd like to make sure there are absolutely no bugs that will cause issues when I use real money.

## How to Use
1) First, you need an Alpaca Paper Trading account. You can sign up [here](https://app.alpaca.markets/signup)
2) Click "generate new key" on your portfolio page to attain a key and secret key
3) Copy 'config.example.py' to 'config.py' and put your keys in the local 'config.py' file<br>
> the main key is assigned to the APCA_API_KEY_ID variable while the secret key is assigned to APCA_API_SECRET_KEY
> Set MAX_CAPITAL to the maximum total position exposure the bot may allocate; the default is $500 and includes current positions and pending buy orders.
4) In PowerShell, create a Python 3.14 environment and install the dependencies:
```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```
5) Run the bot from the repository folder with `\.venv\Scripts\python.exe biz_bot_final_script.py`. It continues until stopped with Ctrl+C and uses Alpaca paper trading.

Buy quantities are sized from the latest IEX minute price and capped by both MAX_CAPITAL and Alpaca buying power. Market-order slippage can make actual fill values differ slightly from the estimate.

## Tunable Parameters
The indicators I use are based on my personal trading preferences. If you don't like them, that's okay! You can go in and change them however you'd like. Here's where you should look for things you might want to tune to your liking:

Each section has a commented header that describes what the code below it will do - this is how I will reference what to look for.

### **biz_bot_scrape.py**<br>
- GET LIST OF SYMBOLS
>  - The scanner uses the newest dated snapshot in 'data/holdings.csv'. The current snapshot contains 101 [Nasdaq-100 constituents](https://en.wikipedia.org/wiki/List_of_NASDAQ-100_companies) as a QQQ universe proxy, dated 2026-09-19; refresh it when the index changes.
>  - Daily bars use IEX data in batches of up to 40 symbols, with a 320-calendar-day window to cover the 200-day indicator.
- ADDING IN INDICATORS
>  - SMA and RSI values are calculated independently for each ticker using the 'ta' package.
- CALCULATE PIVOT POINT AND RESISTANCE LEVEL
>  - You can add more resistance/support levels as you choose
- FILTER DATA
>  - Here's where you'd change the buying criteria

### **biz_bot_place_orders.py**<br>
- BUY STOCKS
>  - The equity_limit variable ensures stocks will be bought at a somewhat even ratio - this can be changed based on what your buying power is and how much diversification you >want in your portfolio

### **biz_bot_sell.py**<br>
- ADDING IN INDICATORS
>  - Anything you change in the 'scrape' script will also have to be changed here
- CALCULATE PIVOT POINT AND RESISTANCE LEVEL
>  - The take-profit target is set by `TAKE_PROFIT_PERCENT` in this file; it defaults to 0.01 (1% above Alpaca's average entry price), before fees and slippage.
- CRITERIA FOR SELLING
>  - Set `TAKE_PROFIT_PERCENT` in local `config.py`; use `1.0` for a 1% gain or `1.5` for a 1.5% gain above average entry price. This gross target excludes fees and slippage.
  
## Ideas for future versions
  - Implement a machine learning algorithm to predict stock prices and trade on those predictions in conjunction with some techincal indicators
  - Trade options with the same criteria - would need a different API
  - Find a way to scan more than Alpaca's 200 stock limit at one time<br>
  <br>
This will certainly be a long-term project for me as I look for ways to improve the bot and make it more efficient - if you have any ideas yourself, feel free to submit a pull request or email me at abzdel@bryant.edu. Thank you for your interest!

## Programs & Packages
- **Python**: Version 3.14
- **Packages**: alpaca-py, pandas, ta
- **Alpaca**: For scraping stock data and buying/selling securities



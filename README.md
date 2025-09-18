btc-liqs-correlation/
├─ .env.example            # copy to .env; switch TG group here
├─ .gitignore
├─ requirements.txt
├─ README.md
├─ data/
│  ├─ raw/                 # as-fetched CSVs
│  └─ processed/           # cleaned/aggregated/joined CSVs
├─ notebooks/
│  └─ analysis.ipynb       # plots & ad-hoc exploration (reads processed CSVs)
└─ src/
    ├─ fetch_telegram.py    # get messages from Telegram → data/raw/telegram_messages.csv
    ├─ fetch_price.py       # get BTC price (CoinGecko/Binance) → data/raw/btc_price.csv
    ├─ parse_aggregate.py   # parse long/short + USD; aggregate per interval → data/processed/liqs_<interval>.csv
    ├─ build_dataset.py     # join liqs + price; engineer features → data/processed/dataset.csv
   └─ analyze.py           # quick correlations & simple charts (prints results, saves PNG)

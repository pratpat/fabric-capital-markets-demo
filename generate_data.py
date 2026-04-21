"""
Capital Markets demo data generator for Microsoft Fabric Lakehouse.
Generates 8 CSV files: securities, clients, accounts, traders, eod_prices,
trades, market_quotes, positions.

Usage:
    python generate_data.py [--scale small|medium|large] [--out OUTPUT_DIR]
"""
from __future__ import annotations

import argparse
import csv
import os
import random
import string
from dataclasses import dataclass
from datetime import date, datetime, timedelta

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCALES = {
    # (n_securities, n_clients, n_accounts, n_traders, eod_years, n_trades, n_quotes)
    "small":  (100,   1_000,  1_500,  20,  1, 50_000,    200_000),
    "medium": (500,  10_000, 15_000,  50,  2, 1_000_000, 2_000_000),
    "large":  (1_500, 50_000, 75_000, 150, 3, 5_000_000, 10_000_000),
}

SECTORS = [
    ("Technology",            ["Software", "Semiconductors", "Hardware", "IT Services"]),
    ("Financials",            ["Banks", "Insurance", "Capital Markets", "Asset Management"]),
    ("Health Care",           ["Pharma", "Biotech", "Medical Devices", "Health Services"]),
    ("Consumer Discretionary",["Retail", "Autos", "Hotels", "Apparel"]),
    ("Consumer Staples",      ["Food", "Beverages", "Household Products"]),
    ("Energy",                ["Oil & Gas", "Renewables"]),
    ("Industrials",           ["Aerospace", "Machinery", "Transportation"]),
    ("Materials",             ["Chemicals", "Metals & Mining"]),
    ("Utilities",             ["Electric", "Water", "Gas"]),
    ("Communication",         ["Telecom", "Media", "Entertainment"]),
    ("Real Estate",           ["REITs", "Real Estate Services"]),
]

EXCHANGES = [
    ("XNYS", "USD", "US"),
    ("XNAS", "USD", "US"),
    ("XLON", "GBP", "GB"),
    ("XTKS", "JPY", "JP"),
    ("XHKG", "HKD", "HK"),
    ("XETR", "EUR", "DE"),
    ("XPAR", "EUR", "FR"),
    ("XTSE", "CAD", "CA"),
]

VENUES        = ["XNYS", "XNAS", "ARCA", "BATS", "IEX", "EDGX", "XLON", "CHIX"]
ORDER_TYPES   = ["MARKET", "LIMIT", "STOP", "STOP_LIMIT"]
TRADE_STATUS  = ["FILLED", "PARTIAL", "CANCELLED"]
CLIENT_TYPES  = ["INSTITUTIONAL", "RETAIL", "HEDGE_FUND", "PENSION", "SOVEREIGN"]
ACCOUNT_TYPES = ["CASH", "MARGIN", "PRIME_BROKERAGE", "CUSTODY"]
RISK_PROFILES = ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"]
KYC_TIERS     = ["TIER_1", "TIER_2", "TIER_3"]
DESKS         = ["EQUITY_CASH", "PROGRAM_TRADING", "ETF", "DERIVATIVES", "QUANT"]
REGIONS       = ["AMER", "EMEA", "APAC"]
COUNTRIES     = ["US", "GB", "DE", "FR", "JP", "HK", "SG", "CA", "AU", "CH", "NL", "BR", "IN"]

FIRST_NAMES = ["Alex","Maria","John","Priya","Wei","Sofia","Liam","Yuki","Noah","Zara",
               "Hugo","Aisha","Mateo","Chen","Olivia","Ahmed","Lucas","Fatima","Ethan","Anya"]
LAST_NAMES  = ["Smith","Garcia","Patel","Kim","Wang","Müller","Dubois","Tanaka","Rossi","Silva",
               "Khan","Nguyen","Jones","Cohen","Singh","Lopez","Brown","Ivanov","Murphy","Sato"]

INST_SUFFIX = ["Capital","Partners","Asset Management","Investments","Holdings","Group",
               "Securities","Advisors","Wealth","Fund Management"]
INST_PREFIX = ["Northstar","Apex","Bluewater","Summit","Atlas","Pinnacle","Vanguard","Helios",
               "Meridian","Cobalt","Quantum","Sterling","Granite","Orion","Crescent"]

random.seed(42)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rand_symbol(existing: set[str]) -> str:
    while True:
        n = random.choice([3, 4, 4, 4, 5])
        s = "".join(random.choices(string.ascii_uppercase, k=n))
        if s not in existing:
            existing.add(s)
            return s


def rand_isin(country: str) -> str:
    body = "".join(random.choices(string.ascii_uppercase + string.digits, k=9))
    check = random.randint(0, 9)
    return f"{country}{body}{check}"


def rand_cusip() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8)) + str(random.randint(0, 9))


def rand_person_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def rand_inst_name() -> str:
    return f"{random.choice(INST_PREFIX)} {random.choice(INST_SUFFIX)}"


def business_days(start: date, end: date) -> list[date]:
    days = []
    d = start
    while d <= end:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def write_csv(path: str, header: list[str], rows_iter):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        n = 0
        for row in rows_iter:
            w.writerow(row)
            n += 1
            if n % 500_000 == 0:
                print(f"  ...{n:,} rows written")
    print(f"  wrote {n:,} rows -> {path}")
    return n


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

@dataclass
class Security:
    symbol: str
    isin: str
    cusip: str
    name: str
    sector: str
    industry: str
    exchange: str
    currency: str
    country: str
    base_price: float


def gen_securities(n: int) -> list[Security]:
    print(f"Generating {n:,} securities...")
    seen: set[str] = set()
    out: list[Security] = []
    for _ in range(n):
        sym = rand_symbol(seen)
        sector, industries = random.choice(SECTORS)
        industry = random.choice(industries)
        exch, ccy, country = random.choice(EXCHANGES)
        out.append(Security(
            symbol=sym,
            isin=rand_isin(country),
            cusip=rand_cusip() if country == "US" else "",
            name=f"{sym} {random.choice(['Inc','Corp','PLC','SA','AG','Ltd','NV','Holdings'])}",
            sector=sector,
            industry=industry,
            exchange=exch,
            currency=ccy,
            country=country,
            base_price=round(random.uniform(5, 800), 2),
        ))
    return out


def write_securities(path: str, secs: list[Security]) -> int:
    header = ["symbol","isin","cusip","name","sector","industry","exchange","currency","country"]
    return write_csv(path, header,
        ([s.symbol, s.isin, s.cusip, s.name, s.sector, s.industry, s.exchange, s.currency, s.country] for s in secs))


def gen_clients(n: int, today: date) -> list[tuple]:
    print(f"Generating {n:,} clients...")
    rows = []
    for i in range(1, n + 1):
        ctype = random.choices(CLIENT_TYPES, weights=[35, 40, 10, 10, 5])[0]
        name = rand_person_name() if ctype == "RETAIL" else rand_inst_name()
        country = random.choice(COUNTRIES)
        kyc = random.choices(KYC_TIERS, weights=[60, 30, 10])[0]
        risk = random.choice(RISK_PROFILES)
        if ctype == "RETAIL":
            aum = round(random.uniform(10_000, 5_000_000), 2)
        elif ctype == "INSTITUTIONAL":
            aum = round(random.uniform(50_000_000, 5_000_000_000), 2)
        elif ctype == "HEDGE_FUND":
            aum = round(random.uniform(100_000_000, 20_000_000_000), 2)
        elif ctype == "PENSION":
            aum = round(random.uniform(500_000_000, 50_000_000_000), 2)
        else:
            aum = round(random.uniform(1_000_000_000, 200_000_000_000), 2)
        onboarded = today - timedelta(days=random.randint(30, 365 * 15))
        rows.append((f"C{i:08d}", name, ctype, country, kyc, risk, aum, onboarded.isoformat()))
    return rows


def write_clients(path: str, rows: list[tuple]) -> int:
    header = ["client_id","name","client_type","country","kyc_tier","risk_profile","aum_usd","onboarded_date"]
    return write_csv(path, header, iter(rows))


def gen_accounts(n: int, n_clients: int, today: date) -> list[tuple]:
    print(f"Generating {n:,} accounts...")
    rows = []
    for i in range(1, n + 1):
        client_idx = random.randint(1, n_clients)
        atype = random.choices(ACCOUNT_TYPES, weights=[40, 30, 20, 10])[0]
        ccy = random.choices(["USD","EUR","GBP","JPY","HKD","CAD"], weights=[50,20,10,8,7,5])[0]
        opened = today - timedelta(days=random.randint(10, 365 * 12))
        status = random.choices(["ACTIVE","ACTIVE","ACTIVE","CLOSED","FROZEN"], weights=[80,8,7,3,2])[0]
        rows.append((f"A{i:09d}", f"C{client_idx:08d}", atype, ccy, opened.isoformat(), status))
    return rows


def write_accounts(path: str, rows: list[tuple]) -> int:
    header = ["account_id","client_id","account_type","base_currency","opened_date","status"]
    return write_csv(path, header, iter(rows))


def gen_traders(n: int) -> list[tuple]:
    print(f"Generating {n:,} traders...")
    rows = []
    for i in range(1, n + 1):
        rows.append((f"T{i:04d}", rand_person_name(), random.choice(DESKS), random.choice(REGIONS)))
    return rows


def write_traders(path: str, rows: list[tuple]) -> int:
    header = ["trader_id","name","desk","region"]
    return write_csv(path, header, iter(rows))


def gen_eod_prices(secs: list[Security], years: int, today: date):
    """Geometric-Brownian-motion-ish price walks per symbol."""
    start = today - timedelta(days=365 * years)
    days = business_days(start, today)
    print(f"Generating EOD prices: {len(secs):,} symbols x {len(days):,} days = {len(secs)*len(days):,} rows...")
    # Pre-compute symbol drift/vol
    params = {s.symbol: (random.uniform(-0.0002, 0.0006), random.uniform(0.008, 0.035)) for s in secs}
    prices = {s.symbol: s.base_price for s in secs}
    final_prices: dict[str, float] = {}

    def gen():
        for d in days:
            iso = d.isoformat()
            for s in secs:
                mu, sigma = params[s.symbol]
                ret = random.gauss(mu, sigma)
                prev = prices[s.symbol]
                close = max(0.5, prev * (1 + ret))
                open_ = prev * (1 + random.gauss(0, sigma / 3))
                high = max(open_, close) * (1 + abs(random.gauss(0, sigma / 2)))
                low  = min(open_, close) * (1 - abs(random.gauss(0, sigma / 2)))
                vol = int(random.lognormvariate(13, 1.2))
                prices[s.symbol] = close
                yield (s.symbol, iso, round(open_,4), round(high,4), round(low,4), round(close,4), vol, round(close,4))
        for sym, px in prices.items():
            final_prices[sym] = px

    return gen, final_prices


def write_eod_prices(path: str, gen_fn) -> int:
    header = ["symbol","trade_date","open","high","low","close","volume","adj_close"]
    return write_csv(path, header, gen_fn())


def gen_trades(n: int, secs: list[Security], n_accounts: int, n_traders: int, years: int, today: date):
    print(f"Generating {n:,} trades...")
    start = today - timedelta(days=365 * years)
    span_secs = int((today - start).total_seconds())
    sec_list = secs

    def gen():
        for i in range(1, n + 1):
            offset = random.randint(0, span_secs)
            ts = datetime.combine(start, datetime.min.time()) + timedelta(seconds=offset)
            # bias to market hours 13:30-20:00 UTC
            ts = ts.replace(hour=random.randint(13, 19), minute=random.randint(0, 59), second=random.randint(0, 59))
            sec = random.choice(sec_list)
            qty = random.choice([100, 200, 500, 1000, 2500, 5000, 10000])
            price = round(sec.base_price * random.uniform(0.7, 1.4), 4)
            side = random.choice(["BUY", "SELL"])
            notional = round(qty * price, 2)
            yield (
                f"TR{i:010d}",
                ts.isoformat(timespec="seconds"),
                sec.symbol,
                f"A{random.randint(1, n_accounts):09d}",
                f"T{random.randint(1, n_traders):04d}",
                side,
                qty,
                price,
                notional,
                random.choice(VENUES),
                random.choices(ORDER_TYPES, weights=[50, 35, 10, 5])[0],
                random.choices(TRADE_STATUS, weights=[85, 10, 5])[0],
            )
    return gen


def write_trades(path: str, gen_fn) -> int:
    header = ["trade_id","trade_ts","symbol","account_id","trader_id","side","quantity","price","notional","venue","order_type","status"]
    return write_csv(path, header, gen_fn())


def gen_quotes(n: int, secs: list[Security], today: date):
    """Recent intraday quotes (last 5 trading days)."""
    print(f"Generating {n:,} market quotes...")
    days = business_days(today - timedelta(days=10), today)[-5:]
    sec_list = secs

    def gen():
        for _ in range(n):
            d = random.choice(days)
            ts = datetime.combine(d, datetime.min.time()) + timedelta(
                hours=random.randint(13, 19),
                minutes=random.randint(0, 59),
                seconds=random.randint(0, 59),
                microseconds=random.randint(0, 999_999),
            )
            sec = random.choice(sec_list)
            mid = sec.base_price * random.uniform(0.95, 1.05)
            spread = mid * random.uniform(0.0001, 0.002)
            bid = round(mid - spread / 2, 4)
            ask = round(mid + spread / 2, 4)
            yield (
                sec.symbol,
                ts.isoformat(timespec="microseconds"),
                bid,
                ask,
                random.choice([100, 200, 500, 1000, 2000]),
                random.choice([100, 200, 500, 1000, 2000]),
                random.choice(VENUES),
            )
    return gen


def write_quotes(path: str, gen_fn) -> int:
    header = ["symbol","quote_ts","bid","ask","bid_size","ask_size","venue"]
    return write_csv(path, header, gen_fn())


def gen_positions(secs: list[Security], n_accounts: int, today: date, final_prices: dict[str, float]):
    """Snapshot: each active account holds a few positions."""
    print("Generating positions snapshot...")
    rows = []
    iso = today.isoformat()
    for acct_idx in range(1, n_accounts + 1):
        if random.random() < 0.15:  # 15% empty accounts
            continue
        n_pos = random.randint(1, 8)
        chosen = random.sample(secs, k=min(n_pos, len(secs)))
        for s in chosen:
            qty = random.choice([100, 200, 500, 1000, 2500, 5000])
            avg_cost = round(s.base_price * random.uniform(0.7, 1.3), 4)
            mkt_px = final_prices.get(s.symbol, s.base_price)
            mv = round(qty * mkt_px, 2)
            pnl = round((mkt_px - avg_cost) * qty, 2)
            rows.append((iso, f"A{acct_idx:09d}", s.symbol, qty, avg_cost, mv, pnl))
    return rows


def write_positions(path: str, rows: list[tuple]) -> int:
    header = ["as_of_date","account_id","symbol","quantity","avg_cost","market_value_usd","unrealized_pnl_usd"]
    return write_csv(path, header, iter(rows))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", choices=list(SCALES.keys()), default="small")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()

    n_sec, n_cli, n_acc, n_trd, eod_yrs, n_trades, n_quotes = SCALES[args.scale]
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    today = date(2026, 4, 21)

    print(f"\n=== Capital Markets demo data | scale={args.scale} | out={out} ===\n")

    secs = gen_securities(n_sec)
    write_securities(os.path.join(out, "securities.csv"), secs)

    clients = gen_clients(n_cli, today)
    write_clients(os.path.join(out, "clients.csv"), clients)

    accounts = gen_accounts(n_acc, n_cli, today)
    write_accounts(os.path.join(out, "accounts.csv"), accounts)

    traders = gen_traders(n_trd)
    write_traders(os.path.join(out, "traders.csv"), traders)

    eod_gen, final_prices = gen_eod_prices(secs, eod_yrs, today)
    write_eod_prices(os.path.join(out, "eod_prices.csv"), eod_gen)

    trades_gen = gen_trades(n_trades, secs, n_acc, n_trd, eod_yrs, today)
    write_trades(os.path.join(out, "trades.csv"), trades_gen)

    quotes_gen = gen_quotes(n_quotes, secs, today)
    write_quotes(os.path.join(out, "market_quotes.csv"), quotes_gen)

    positions = gen_positions(secs, n_acc, today, final_prices)
    write_positions(os.path.join(out, "positions.csv"), positions)

    print("\nDone. Files:")
    for fn in sorted(os.listdir(out)):
        p = os.path.join(out, fn)
        print(f"  {fn:20s}  {os.path.getsize(p)/1_048_576:>8.2f} MB")


if __name__ == "__main__":
    main()

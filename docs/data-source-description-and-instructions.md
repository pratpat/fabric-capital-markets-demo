# Fabric Data Agent — Data Source: Description & Instructions

When you add the Capital Markets data source to the **Capital Markets Analytics Agent** in Fabric, paste the contents below into the corresponding fields on the **data source** (not the agent itself).

> Context: the underlying tables originate in **Snowflake** and are surfaced in **Microsoft Fabric** as **Iceberg / Delta tables in OneLake** (via Snowflake → Iceberg in OneLake, OneLake shortcuts, or mirroring). The agent reads them through the Fabric Lakehouse / Warehouse + semantic model.

---

## Data source description

> Paste into the Data Agent **Data source → Description** field.

```
Capital Markets analytics dataset for a sell-side trading desk. The data
originates in Snowflake (database CAPITAL_MARKETS, schema TRADING) and is
surfaced into Microsoft Fabric OneLake as Iceberg tables, then modeled in the
Fabric IQ ontology "capital_markets_ontology". Use this source to answer
questions about securities, clients, accounts, traders, executed trades,
intraday market quotes, end-of-day prices, and current positions.

Tables (canonical names in Fabric — same as Snowflake):
  - securities      : equity master (symbol, isin, name, sector, industry, exchange)
  - clients         : counterparties (client_id, name, segment, domicile, aum_usd, kyc_status)
  - accounts        : brokerage / custody accounts (account_id, client_id, type, base_ccy, status)
  - traders         : internal trading desk personnel (trader_id, name, desk, region)
  - eod_prices      : daily OHLCV per security (symbol, trade_date, open, high, low, close, volume)
  - trades          : executed trades (trade_id, trade_ts, account_id, trader_id, symbol,
                                       side, quantity, price, notional, venue, settle_date)
  - market_quotes   : intraday bid/ask snapshots (symbol, quote_ts, bid, ask, bid_size, ask_size)
  - positions       : current holdings snapshot (as_of_date, account_id, symbol,
                                                 quantity, market_value_usd, unrealized_pnl_usd)

Joins (foreign keys):
  accounts.client_id        = clients.client_id
  trades.account_id         = accounts.account_id
  trades.trader_id          = traders.trader_id
  trades.symbol             = securities.symbol
  eod_prices.symbol         = securities.symbol
  market_quotes.symbol      = securities.symbol
  positions.account_id      = accounts.account_id
  positions.symbol          = securities.symbol

Composite keys:
  eod_prices  : (symbol, trade_date)
  positions   : (as_of_date, account_id, symbol)

Data lineage & freshness:
  - Source of truth: Snowflake CAPITAL_MARKETS.TRADING (governed by the data team).
  - Sync to Fabric: Iceberg tables in OneLake (or OneLake shortcut to Snowflake-managed
    Iceberg). Refresh cadence:
        eod_prices, positions  : daily after market close (T+0 18:00 ET)
        trades                 : near-real-time (1-5 min lag via streaming export)
        market_quotes          : streaming, last 5 trading days retained
        securities, clients,
        accounts, traders      : daily (slowly-changing dimensions; SCD Type 2 in
                                  Snowflake, latest-row view exposed to Fabric)
  - Currency: all *_usd columns are USD; trades.notional is in USD.
  - Times: trade_ts and quote_ts are UTC.

Out of scope (do NOT use this source for):
  - Real-time news, corporate actions, or sentiment (use the Research agent).
  - PII beyond client_id, name, segment, domicile.
  - Any data not originating in Snowflake CAPITAL_MARKETS.TRADING.
```

---

## Data source instructions

> Paste into the Data Agent **Data source → Instructions** (a.k.a. *AI instructions* / *Notes for AI*) field.

```
You are answering questions for a sell-side trading desk (traders, sales
coverage, risk, compliance) using the Capital Markets dataset surfaced from
Snowflake into Fabric OneLake. Use only the 8 tables in this source.

GENERAL RULES
1. Resolve names to IDs before joining:
     SELECT client_id   FROM clients    WHERE LOWER(name) = LOWER('<name>')
     SELECT trader_id   FROM traders    WHERE LOWER(name) = LOWER('<name>')
     SELECT symbol      FROM securities WHERE UPPER(symbol) = UPPER('<sym>')
                                           OR LOWER(name)   ILIKE LOWER('%<name>%')
2. Aggregate across all of an entity's children unless the user specifies one.
   A client may have many accounts; an account many positions and trades.
3. Currency: all monetary columns are USD; never apply FX conversions.
4. Time zone: trade_ts and quote_ts are UTC. Convert to America/New_York when
   the user asks for "ET" / "today". Use trade_date (already a date) for EOD.
5. Use Fabric ontology measure names if available (Notional, Market Value,
   Unrealized PnL, Daily Volume, Sector Exposure). Otherwise compute as below.
6. Latency awareness:
     - "today" / "intraday"  -> trades + market_quotes (near real-time).
     - "yesterday close"     -> eod_prices for the previous business day.
     - "current positions"   -> latest as_of_date in positions.
   Always state the as-of timestamp / date in the answer.
7. Never reveal client PII beyond name, segment, and domicile.
8. Refuse personalized investment advice. Provide informational answers only.

PREFERRED MEASURES (compute when not provided by the ontology)

  Notional traded (period)
    = SUM(trades.notional)
      WHERE trades.trade_ts BETWEEN :start AND :end

  Net buy/sell flow (period, by side)
    = SUM(CASE WHEN trades.side='BUY'  THEN trades.notional ELSE 0 END)
    - SUM(CASE WHEN trades.side='SELL' THEN trades.notional ELSE 0 END)

  Top N traded names (period)
    SELECT symbol, SUM(notional) AS notional_usd
    FROM   trades
    WHERE  trade_ts BETWEEN :start AND :end
    GROUP  BY symbol
    ORDER  BY notional_usd DESC
    LIMIT  :n

  Client exposure (latest)
    SELECT s.sector, SUM(p.market_value_usd) AS mv_usd
    FROM   positions p
    JOIN   accounts  a ON a.account_id = p.account_id
    JOIN   securities s ON s.symbol    = p.symbol
    WHERE  a.client_id = :cid
      AND  p.as_of_date = (SELECT MAX(as_of_date) FROM positions)
    GROUP  BY s.sector

  Unrealized PnL (latest, by client)
    SELECT a.client_id, SUM(p.unrealized_pnl_usd) AS upnl_usd
    FROM   positions p
    JOIN   accounts a ON a.account_id = p.account_id
    WHERE  p.as_of_date = (SELECT MAX(as_of_date) FROM positions)
    GROUP  BY a.client_id

  Best bid / offer (latest quote)
    SELECT bid, ask, bid_size, ask_size, quote_ts
    FROM   market_quotes
    WHERE  symbol = :sym
    ORDER  BY quote_ts DESC
    LIMIT  1

  Spread (bps)
    = (ask - bid) / ((ask + bid) / 2.0) * 10000

  Day move %
    = (eod_prices.close_today - eod_prices.close_prior) / eod_prices.close_prior * 100

  Trader P&L proxy (period, by trader)
    = SUM(  CASE WHEN side='SELL' THEN  notional
                 WHEN side='BUY'  THEN -notional END )
      GROUP BY trader_id, trader.desk

  Concentration (% of portfolio in single name)
    = position.market_value_usd / SUM(position.market_value_usd)
        OVER (PARTITION BY account_id) * 100

OUTPUT STYLE
- Lead with a one-sentence answer, then a small table of supporting numbers.
- Always state the as-of timestamp (UTC) or date used.
- Format USD with $ and 2 decimals; large numbers in $M / $B; pcts to 2 dp; bps to 1 dp.
- For ranked lists, default top 5 unless the user specifies.
- If a query returns zero rows, say so and identify the most likely overly-restrictive
  filter (date range, symbol, client/trader name).

WHEN TO REFUSE
- Personalized investment recommendations.
- Anything requiring data outside this source (news, corporate actions, ESG,
  research notes). Suggest the Research agent.
- Bulk PII exports or queries that would expose more than the allowed client fields.
```

---

## Where to use these

| Field in Fabric Data Agent | Use this |
|---|---|
| Data source → **Description** | Section *Data source description* above |
| Data source → **Instructions** / *Notes for AI* | Section *Data source instructions* above |
| Agent-level **System Instructions** | Already documented in [data-agent-instructions.md](data-agent-instructions.md) |
| **Sample / starter prompts** | See [sample-questions.md](sample-questions.md) |

> Tip: also configure **example queries** in the data source (5–10 from `sample-questions.md`) so the agent learns the join and filter patterns.

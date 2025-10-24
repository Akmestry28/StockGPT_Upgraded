import yfinance as yf
import pandas as pd
from typing import Optional

def extract_ticker_from_text(text: str) -> Optional[str]:
    """
    Try to extract a ticker symbol or company name from user text.
    - Looks for $TICKER or uppercase tokens like AAPL, TSLA
    - If nothing found, returns None (we'll handle name-to-ticker later)
    """
    import re

    # 1) $TICKER pattern
    m = re.search(r"\$([A-Z]{1,5})\b", text)
    if m:
        return m.group(1).upper()

    # 2) Parentheses pattern like (AAPL)
    m = re.search(r"\(([A-Z]{1,5})\)", text)
    if m:
        return m.group(1).upper()

    # 3) Uppercase tokens
    tokens = re.findall(r"\b[A-Z]{1,5}\b", text)
    tokens = [t for t in tokens if len(t) > 1]  # avoid single letters
    if tokens:
        return tokens[0].upper()

    return None


def get_stock_info(query: str) -> str:
    """
    Universal stock info:
    - query can be ticker or company name
    - returns a readable summary string
    """
    try:
        # Try as ticker first
        stock = yf.Ticker(query.upper())
        info = stock.info or {}

        # If ticker not found, try searching by company name
        if 'shortName' not in info:
            search_results = yf.search(query)
            if search_results and 'quotes' in search_results and len(search_results['quotes']) > 0:
                best_match = search_results['quotes'][0]['symbol']
                stock = yf.Ticker(best_match)
                info = stock.info

        name = info.get("longName") or info.get("shortName") or query
        current_price = info.get("currentPrice")
        market_cap = info.get("marketCap")
        summary = info.get("longBusinessSummary", "")
        sector = info.get("sector", "N/A")
        industry = info.get("industry", "N/A")

        def fmt(x):
            if x is None:
                return "N/A"
            if isinstance(x, (int, float)):
                if abs(x) >= 1e12: return f"${x/1e12:.2f}T"
                if abs(x) >= 1e9: return f"${x/1e9:.2f}B"
                if abs(x) >= 1e6: return f"${x/1e6:.2f}M"
                return f"${x:.2f}"
            return str(x)

        lines = [
            f"**{name} ({info.get('symbol', query.upper())})**",
            f"Sector: {sector} • Industry: {industry}",
            f"Price: {fmt(current_price)}",
            f"Market Cap: {fmt(market_cap)}",
            "",
            "Summary:",
            summary[:1500] + ("..." if len(summary) > 1500 else "")
        ]
        return "\n".join(lines)

    except Exception as e:
        return f"Couldn't fetch info for '{query}'. Error: {e}"


def get_stock_history(ticker: str, period: str = "1y", interval: str = "1d") -> Optional[pd.DataFrame]:
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period, interval=interval)
        if df is None or df.empty:
            return None
        df = df.reset_index()
        return df
    except Exception:
        return None


def get_latest_news(ticker: str, count: int = 5) -> str:
    try:
        stock = yf.Ticker(ticker)
        news = getattr(stock, "news", None) or []
        if not news:
            return "No recent news found."
        formatted = []
        for i, n in enumerate(news[:count], start=1):
            title = n.get("title", "No title")
            publisher = n.get("publisher", "Unknown")
            link = n.get("link", "")
            if len(title) > 300:
                title = title[:297] + "..."
            formatted.append(f"{i}. **{title}**  \nSource: {publisher}  \n{link}")
        return "\n\n".join(formatted)
    except Exception as e:
        return f"Error fetching news: {e}"

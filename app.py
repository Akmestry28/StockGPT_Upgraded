import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import pandas as pd
import traceback
import yfinance as yf

from config import OPENAI_API_KEY
from utils import (
    extract_ticker_from_text,
    get_stock_info,
    get_stock_history,
    get_latest_news,
)

# --- Init ---
st.set_page_config(page_title="StockGPT - AI Stock Assistant", page_icon="📈")
st.title("📈 StockGPT – AI Stock Chat Assistant")

# Initialize OpenAI client
try:
    client = OpenAI(api_key=OPENAI_API_KEY)
except Exception as e:
    st.error(f"⚠️ Error initializing OpenAI client: {e}")
    st.stop()

# Session messages
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {
            "role": "assistant",
            "content": "Hi! I’m StockGPT. Ask me about any stock ticker (e.g., AAPL, TSLA, INFY) or market trend 📊"
        }
    ]

# Display previous chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# User input widget
user_input = st.chat_input("Ask about a stock or market trend (e.g., 'What's up with AAPL?' or 'Tell me about Tesla')")

if user_input:
    # Append user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # --- Extract ticker or company name ---
    ticker = extract_ticker_from_text(user_input)

    # If no ticker found, try treating input as company name
    resolved_ticker = ticker
    if not ticker:
        try:
            search_results = yf.search(user_input)
            if search_results and 'quotes' in search_results and len(search_results['quotes']) > 0:
                resolved_ticker = search_results['quotes'][0]['symbol']
        except Exception:
            resolved_ticker = None

    stock_data = None
    history_df = None
    news_md = None

    # Use resolved_ticker for all API calls
    if resolved_ticker:
        with st.spinner(f"Fetching data for {resolved_ticker}..."):
            try:
                stock_data = get_stock_info(resolved_ticker)
                history_df = get_stock_history(resolved_ticker, period="1y", interval="1d")
                news_md = get_latest_news(resolved_ticker, count=5)
            except Exception as e:
                st.warning(f"Couldn't fetch full data: {e}")

    else:
        st.warning("❌ Could not resolve any stock symbol from input.")

    # Build prompt for OpenAI
    prompt = (
        "You are a helpful and careful financial assistant. Be explicit about what is an "
        "opinion vs fact. Don't give trading advice (no 'buy' or 'sell' calls). "
        "When uncertain, say 'I don't know' and recommend the user verify facts.\n\n"
        f"User question: {user_input}\n\n"
    )
    if resolved_ticker and stock_data:
        prompt += f"Live company summary for {resolved_ticker}:\n{stock_data}\n\n"
    if resolved_ticker and news_md:
        prompt += f"Recent headlines for {resolved_ticker}:\n{news_md}\n\n"

    # Call OpenAI for assistant reply
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert stock assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.2,
        )
        ai_response = response.choices[0].message.content
    except Exception as e:
        ai_response = f"⚠️ Error generating response from OpenAI: {e}\n\n{traceback.format_exc()}"

    # Append AI response to chat
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.markdown(ai_response)

    # --- Show Ticker Data ---
    if resolved_ticker:
        st.markdown("---")
        st.subheader(f"Data for {resolved_ticker}")

        # Stock summary
        if stock_data:
            st.markdown(stock_data)
        else:
            st.info("No summary available.")

        # Key metrics and chart
        try:
            info = yf.Ticker(resolved_ticker).info or {}
        except Exception:
            info = {}

        # Key metrics
        st.markdown("### 📈 Key Financial Metrics")
        c1, c2, c3, c4 = st.columns(4)

        def safe_fmt(x, fallback="N/A", is_pct=False):
            try:
                if x is None:
                    return fallback
                if is_pct:
                    return f"{x*100:.2f}%"
                if isinstance(x, (int, float)):
                    return f"{x:,.2f}"
                return str(x)
            except Exception:
                return fallback

        c1.metric("Current Price", f"${safe_fmt(info.get('currentPrice'), 'N/A')}")
        c2.metric("P/E (TTM)", safe_fmt(info.get("trailingPE"), "N/A"))
        market_cap_raw = info.get("marketCap")
        if market_cap_raw:
            if market_cap_raw >= 1e12:
                market_cap_str = f"${market_cap_raw/1e12:.2f}T"
            elif market_cap_raw >= 1e9:
                market_cap_str = f"${market_cap_raw/1e9:.2f}B"
            elif market_cap_raw >= 1e6:
                market_cap_str = f"${market_cap_raw/1e6:.2f}M"
            else:
                market_cap_str = f"${market_cap_raw:,}"
        else:
            market_cap_str = "N/A"
        c3.metric("Market Cap", market_cap_str)
        c4.metric("Dividend Yield", safe_fmt(info.get("dividendYield"), "0.00%", is_pct=True))

        # Chart
        if history_df is not None and not history_df.empty:
            st.markdown("### 🕒 Price Chart (last 1 year)")
            df_plot = history_df.copy()
            df_plot["Date"] = pd.to_datetime(df_plot["Date"])
            df_plot = df_plot.set_index("Date")
            st.line_chart(df_plot["Close"])
        else:
            st.info("No historical price data available for charting.")

        # News
        st.markdown("### 🗞️ Latest News")
        if news_md and not news_md.lower().startswith("error"):
            st.markdown(news_md)
        else:
            st.info("No news found or an error occurred fetching news.")

        # Sentiment analysis on news
        if news_md and not news_md.lower().startswith("no recent news") and not news_md.lower().startswith("error"):
            with st.spinner("Analyzing news sentiment with AI..."):
                sentiment_prompt = (
                    f"You're a financial sentiment analyst. Given the following news headlines for {resolved_ticker}, "
                    "reply in one short paragraph labeling the overall sentiment as Positive, Neutral, or Negative, "
                    "then provide 1-2 bullet points explaining why (very concise). Do NOT give trading advice.\n\n"
                    f"{news_md}\n\nSentiment:"
                )
                try:
                    senti_resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a concise financial sentiment analyst."},
                            {"role": "user", "content": sentiment_prompt}
                        ],
                        max_tokens=200,
                        temperature=0.0,
                    )
                    sentiment_result = senti_resp.choices[0].message.content
                    st.markdown("**🧠 Sentiment analysis (AI):**")
                    st.markdown(sentiment_result)
                except Exception as e:
                    st.warning(f"Could not run sentiment analysis: {e}")

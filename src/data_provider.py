"""
data_provider.py — Camada de Aquisição de Dados (yfinance + cache)

Responsável por buscar dados financeiros do Yahoo Finance para ações B3,
com mecanismo de resiliência (reset de sessão/crumb) e cache Streamlit.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


# ─────────────────────────────────────────────
# Resiliência yfinance
# ─────────────────────────────────────────────

def _reset_yfinance_session():
    """Limpa sessão/crumb do yfinance para forçar reautenticação."""
    try:
        import yfinance.data as _yfdata
        if hasattr(_yfdata, '_crumb') and hasattr(_yfdata, '_cookie'):
            _yfdata._crumb = None
            _yfdata._cookie = None
    except Exception:
        pass
    try:
        if hasattr(yf, 'shared') and hasattr(yf.shared, '_CACHE'):
            yf.shared._CACHE = {}
    except Exception:
        pass


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _safe(df: pd.DataFrame, key: str) -> float:
    """Return the most recent non-NaN value from a yfinance statement row."""
    if df is None or df.empty:
        return 0.0
    if key in df.index:
        row = df.loc[key]
        for val in row:
            if pd.notna(val) and val != 0:
                return float(val)
    return 0.0


def _safe_series(df: pd.DataFrame, key: str) -> pd.Series:
    """Return full row Series from a yfinance statement DataFrame."""
    if df is None or df.empty:
        return pd.Series(dtype=float)
    if key in df.index:
        return df.loc[key].astype(float)
    return pd.Series(dtype=float)


def _first_found(df: pd.DataFrame, *keys) -> float:
    """Try multiple keys in order, return the first non-zero value."""
    for k in keys:
        v = _safe(df, k)
        if v != 0:
            return v
    return 0.0


# ─────────────────────────────────────────────
# Fallback Setorial Hardcoded
# ─────────────────────────────────────────────

SECTOR_FALLBACK = {
    # Utilities / Energia Elétrica / Saneamento
    "ELET3": "Utilities", "ELET6": "Utilities", "CMIG4": "Utilities", "CMIG3": "Utilities",
    "CPFE3": "Utilities", "EGIE3": "Utilities", "EQTL3": "Utilities", "ENEV3": "Utilities",
    "ENGI11": "Utilities", "TAEE11": "Utilities", "CPLE3": "Utilities", "CPLE6": "Utilities",
    "AURE3": "Utilities", "ALUP11": "Utilities", "ISAE4": "Utilities", "NEOE3": "Utilities",
    "AESB3": "Utilities", "LIGT3": "Utilities", "TRPL4": "Utilities", "SBSP3": "Utilities",
    "SAPR11": "Utilities", "SAPR4": "Utilities",

    # Financeiras
    "ITUB4": "Financial Services", "ITUB3": "Financial Services",
    "BBDC4": "Financial Services", "BBDC3": "Financial Services",
    "BBAS3": "Financial Services", "SANB11": "Financial Services",
    "BPAC11": "Financial Services", "B3SA3": "Financial Services",
    "BBSE3": "Financial Services", "CXSE3": "Financial Services",
    "ITSA4": "Financial Services", "ITSA3": "Financial Services",
    "PSSA3": "Financial Services", "IRBR3": "Financial Services",
    "BRSR6": "Financial Services", "ABCB4": "Financial Services",
    "BMGB4": "Financial Services", "BPAN4": "Financial Services",

    # Telecomunicações
    "VIVT3": "Communication Services", "TIMS3": "Communication Services",

    # Petróleo & Gás / Commodities
    "PETR4": "Energy", "PETR3": "Energy", "PRIO3": "Energy", "RECV3": "Energy",
    "RRRP3": "Energy", "UGPA3": "Energy", "VBBR3": "Energy", "CSAN3": "Energy",

    # Mineração / Siderurgia
    "VALE3": "Basic Materials", "GGBR4": "Basic Materials", "GOAU4": "Basic Materials",
    "CSNA3": "Basic Materials", "USIM5": "Basic Materials", "BRKM5": "Basic Materials",
    "CBAV3": "Basic Materials", "FESA4": "Basic Materials",

    # Papel & Celulose
    "SUZB3": "Basic Materials", "KLBN11": "Basic Materials", "DXCO3": "Basic Materials",

    # Agronegócio
    "SLCE3": "Consumer Defensive", "SMTO3": "Consumer Defensive",
    "JALL3": "Consumer Defensive", "AGRO3": "Consumer Defensive",

    # Alimentos & Bebidas
    "ABEV3": "Consumer Defensive", "JBSS3": "Consumer Defensive",
    "BEEF3": "Consumer Defensive", "MDIA3": "Consumer Defensive",
    "MRFG3": "Consumer Defensive", "BRFS3": "Consumer Defensive",
    "NATU3": "Consumer Defensive", "PCAR3": "Consumer Defensive",
    "ASAI3": "Consumer Defensive", "CAML3": "Consumer Defensive",

    # Varejo / Consumo Cíclico
    "MGLU3": "Consumer Cyclical", "LREN3": "Consumer Cyclical",
    "AZZA3": "Consumer Cyclical", "VIVA3": "Consumer Cyclical",
    "ALOS3": "Consumer Cyclical", "LJQQ3": "Consumer Cyclical",
    "PETZ3": "Consumer Cyclical", "GRND3": "Consumer Cyclical",
    "GUAR3": "Consumer Cyclical", "CEAB3": "Consumer Cyclical",
    "BHIA3": "Consumer Cyclical", "ALPA4": "Consumer Cyclical",

    # Saúde
    "HAPV3": "Healthcare", "RDOR3": "Healthcare", "FLRY3": "Healthcare",
    "RADL3": "Healthcare", "HYPE3": "Healthcare", "QUAL3": "Healthcare",
    "PNVL3": "Healthcare", "AALR3": "Healthcare",

    # Construção / Real Estate
    "CYRE3": "Real Estate", "MRVE3": "Real Estate", "EZTC3": "Real Estate",
    "DIRR3": "Real Estate", "CURY3": "Real Estate", "JHSF3": "Real Estate",
    "TRIS3": "Real Estate", "MILS3": "Real Estate", "TEND3": "Real Estate",
    "MULT3": "Real Estate", "IGTI11": "Real Estate", "LOGG3": "Real Estate",

    # Industrials / Transporte / Logística
    "WEGE3": "Industrials", "RAIL3": "Industrials", "EMBR3": "Industrials",
    "RENT3": "Industrials", "MOVI3": "Industrials", "VAMO3": "Industrials",
    "SIMH3": "Industrials", "RAPT4": "Industrials", "POMO4": "Industrials",
    "AZUL3": "Industrials", "CCRO3": "Industrials", "ECOR3": "Industrials",
    "TASA4": "Industrials", "MYPK3": "Industrials", "TUPY3": "Industrials",
    "POSI3": "Industrials",

    # Tecnologia
    "TOTS3": "Technology", "LWSA3": "Technology", "CASH3": "Technology",
    "INTB3": "Technology", "MLAS3": "Technology", "SEQL3": "Technology",

    # Educação
    "COGN3": "Consumer Defensive", "YDUQ3": "Consumer Defensive",
    "ANIM3": "Consumer Defensive",
}


# ─────────────────────────────────────────────
# TOP ~200 Ações B3
# ─────────────────────────────────────────────

TICKERS_B3 = [
    # Blue Chips / IBOVESPA
    "VALE3", "PETR4", "PETR3", "ITUB4", "BBDC4", "BBAS3", "WEGE3", "ABEV3",
    "RENT3", "BPAC11", "SUZB3", "ITSA4", "HAPV3", "EQTL3", "RDOR3", "LREN3",
    "PRIO3", "RADL3", "UGPA3", "GGBR4", "CSAN3", "VBBR3", "B3SA3", "VIVT3",
    "CMIG4", "HYPE3", "JBSS3", "TIMS3", "BBSE3", "SBSP3", "EGIE3", "CPFE3",
    "ENEV3", "CSNA3", "RAIL3", "EMBR3",

    # Mid Caps
    "TOTS3", "MULT3", "TAEE11", "GOAU4", "BRKM5", "USIM5", "SANB11", "KLBN11",
    "VAMO3", "ASAI3", "ALPA4", "BEEF3", "ALOS3", "AZZA3", "CPLE3", "ENGI11",
    "ISAE4", "RECV3", "SIMH3", "FLRY3", "MDIA3", "PSSA3", "IGTI11", "AURE3",
    "ALUP11", "SAPR11", "CXSE3", "DXCO3", "EZTC3", "JHSF3", "MRVE3", "CYRE3",
    "POSI3", "SLCE3", "SMTO3", "CCRO3", "ECOR3",

    # Small Caps Líquidas
    "MGLU3", "AZUL3", "YDUQ3", "CVCB3", "RAPT4", "POMO4", "TASA4", "MYPK3",
    "SEQL3", "LJQQ3", "GRND3", "INTB3", "MLAS3", "CBAV3", "TTEN3", "ORVR3",
    "LOGG3", "MOVI3", "JALL3", "ANIM3", "CURY3", "DIRR3", "BRFS3", "MRFG3",
    "COGN3", "IRBR3", "CASH3", "BHIA3", "LWSA3", "PCAR3", "NATU3",
    "LIGT3", "VIVA3", "PNVL3", "ELET3", "ELET6", "NEOE3", "TRPL4",
    "TUPY3", "ABCB4", "BRSR6", "FESA4", "CAML3", "TEND3", "TRIS3",
    "GUAR3", "CEAB3", "BPAN4", "BMGB4", "AGRO3", "AALR3", "PETZ3",
    "RRRP3", "MILS3",
]


# ─────────────────────────────────────────────
# Core Data Fetcher
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_stock_data(ticker_code: str) -> dict | None:
    """
    Fetch comprehensive financial data for a single B3 ticker.
    Returns a dict with all valuation-relevant metrics, or None on failure.
    """
    symbol = ticker_code if ticker_code.endswith(".SA") else f"{ticker_code}.SA"
    clean_ticker = ticker_code.replace(".SA", "")

    for attempt in range(2):
        try:
            tk = yf.Ticker(symbol)

            # ── Price via history (resiliente) ──
            hist = tk.history(period="5d")
            if hist.empty or 'Close' not in hist.columns:
                _reset_yfinance_session()
                time.sleep(0.5)
                continue
            current_price = float(hist['Close'].dropna().iloc[-1])
            if current_price <= 0:
                continue

            # ── Info metadata (com fallback) ──
            info = {}
            try:
                info = tk.info or {}
            except Exception:
                _reset_yfinance_session()

            sector = info.get('sector', '')
            industry = info.get('industry', '')
            if not sector:
                sector = SECTOR_FALLBACK.get(clean_ticker, 'N/A')

            shares_outstanding = info.get('sharesOutstanding', 0)
            market_cap = info.get('marketCap', 0)
            if market_cap <= 0 and shares_outstanding > 0:
                market_cap = current_price * shares_outstanding

            # ── EPS / LPA ──
            eps = info.get('trailingEps', 0)
            if not eps or eps == 0:
                try:
                    inc = tk.income_stmt
                    net_income = _first_found(inc, 'Net Income', 'Net Income Common Stockholders')
                    if net_income != 0 and shares_outstanding > 0:
                        eps = net_income / shares_outstanding
                except Exception:
                    eps = 0

            # ── Trailing P/E ──
            trailing_pe = info.get('trailingPE', 0)
            if (not trailing_pe or trailing_pe <= 0) and eps and eps > 0:
                trailing_pe = current_price / eps

            # ── Historical P/E average (5y approximation) ──
            historical_pe = trailing_pe  # fallback
            try:
                hist_5y = tk.history(period="5y")
                if not hist_5y.empty and eps and eps > 0:
                    avg_price_5y = hist_5y['Close'].mean()
                    historical_pe = avg_price_5y / eps
                    if historical_pe <= 0 or historical_pe > 100:
                        historical_pe = trailing_pe
            except Exception:
                pass

            # ── Dividends ──
            dpy = 0.0
            div_growth = 0.05  # default 5%
            try:
                dividends = tk.dividends
                if dividends is not None and not dividends.empty:
                    # Last 12 months dividends
                    one_year_ago = pd.Timestamp.now(tz='UTC') - pd.DateOffset(years=1)
                    recent_divs = dividends[dividends.index >= one_year_ago]
                    dpy = float(recent_divs.sum()) if not recent_divs.empty else 0.0

                    # Dividend growth (3-5 years annualized)
                    if len(dividends) >= 8:
                        yearly_divs = dividends.resample('YE').sum()
                        yearly_divs = yearly_divs[yearly_divs > 0]
                        if len(yearly_divs) >= 3:
                            first_val = yearly_divs.iloc[0]
                            last_val = yearly_divs.iloc[-1]
                            n_years = len(yearly_divs) - 1
                            if first_val > 0 and n_years > 0:
                                div_growth = (last_val / first_val) ** (1 / n_years) - 1
                                div_growth = max(0.02, min(div_growth, 0.15))
            except Exception:
                pass

            # ── Free Cash Flow ──
            fcf_per_share = 0.0
            fcf_growth = 0.05  # default
            try:
                cf = tk.cashflow
                if cf is not None and not cf.empty:
                    op_cf = _first_found(cf, 'Operating Cash Flow', 'Total Cash From Operating Activities',
                                          'Cash Flow From Continuing Operating Activities')
                    capex = _first_found(cf, 'Capital Expenditure', 'Capital Expenditures')
                    if capex > 0:
                        capex = -capex  # ensure negative
                    fcf = op_cf + capex
                    if shares_outstanding > 0:
                        fcf_per_share = fcf / shares_outstanding

                    # FCF growth via historical series
                    op_cf_series = _safe_series(cf, 'Operating Cash Flow')
                    if op_cf_series.empty:
                        op_cf_series = _safe_series(cf, 'Cash Flow From Continuing Operating Activities')
                    capex_series = _safe_series(cf, 'Capital Expenditure')
                    if capex_series.empty:
                        capex_series = _safe_series(cf, 'Capital Expenditures')

                    if not op_cf_series.empty and not capex_series.empty:
                        capex_adj = capex_series.apply(lambda x: -abs(x) if x > 0 else x)
                        fcf_series = op_cf_series + capex_adj
                        fcf_series = fcf_series.dropna()
                        fcf_positive = fcf_series[fcf_series > 0]
                        if len(fcf_positive) >= 2:
                            first_fcf = fcf_positive.iloc[-1]  # oldest
                            last_fcf = fcf_positive.iloc[0]   # most recent
                            n = len(fcf_positive) - 1
                            if first_fcf > 0 and n > 0:
                                fcf_growth = (last_fcf / first_fcf) ** (1 / n) - 1
                                fcf_growth = max(0.02, min(fcf_growth, 0.25))
            except Exception:
                pass

            # ── Net Debt / EBITDA ──
            net_debt_ebitda = 0.0
            try:
                bs = tk.balance_sheet
                inc = tk.income_stmt
                if bs is not None and not bs.empty and inc is not None and not inc.empty:
                    total_debt = _first_found(bs, 'Total Debt', 'Long Term Debt',
                                               'Long Term Debt And Capital Lease Obligation')
                    cash = _first_found(bs, 'Cash And Cash Equivalents',
                                         'Cash Cash Equivalents And Short Term Investments')
                    net_debt = total_debt - cash
                    ebitda = _first_found(inc, 'EBITDA', 'Normalized EBITDA')
                    if ebitda > 0:
                        net_debt_ebitda = net_debt / ebitda
            except Exception:
                pass

            # ── Interest Coverage Ratio ──
            interest_coverage = 999.0
            try:
                inc = tk.income_stmt
                if inc is not None and not inc.empty:
                    ebit = _first_found(inc, 'EBIT', 'Operating Income')
                    interest_expense = _first_found(inc, 'Interest Expense', 'Interest Expense Net Non Operating')
                    if interest_expense != 0:
                        interest_coverage = ebit / abs(interest_expense)
            except Exception:
                pass

            # ── Dividend Yield ──
            div_yield = (dpy / current_price * 100) if current_price > 0 and dpy > 0 else 0.0

            return {
                'ticker': clean_ticker,
                'symbol': symbol,
                'sector': sector,
                'industry': industry,
                'current_price': round(current_price, 2),
                'market_cap': market_cap,
                'shares_outstanding': shares_outstanding,
                'eps': round(eps, 4) if eps else 0,
                'trailing_pe': round(trailing_pe, 2) if trailing_pe else 0,
                'historical_pe': round(historical_pe, 2) if historical_pe else 0,
                'dpy': round(dpy, 4),
                'div_yield': round(div_yield, 2),
                'div_growth': round(div_growth, 4),
                'fcf_per_share': round(fcf_per_share, 4),
                'fcf_growth': round(fcf_growth, 4),
                'net_debt_ebitda': round(net_debt_ebitda, 2),
                'interest_coverage': round(interest_coverage, 2),
            }

        except Exception:
            _reset_yfinance_session()
            time.sleep(0.5)

    return None


def scan_all_stocks(
    tickers: list[str] | None = None,
    max_workers: int = 4,
    progress_callback=None,
    status_callback=None,
) -> pd.DataFrame:
    """
    Scan all tickers and return a DataFrame with financial data.
    Uses ThreadPoolExecutor for parallel fetching.
    """
    if tickers is None:
        tickers = TICKERS_B3

    results = []
    total = len(tickers)
    completed = 0

    if status_callback:
        status_callback(f"📡 Varrendo {total} ativos da B3...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ticker = {
            executor.submit(get_stock_data, t): t for t in tickers
        }
        for future in as_completed(future_to_ticker):
            completed += 1
            if progress_callback:
                progress_callback(completed / total)
            try:
                data = future.result(timeout=30)
                if data is not None:
                    results.append(data)
            except Exception:
                continue

    if status_callback:
        status_callback(f"✅ Varredura finalizada — {len(results)} ativos processados com sucesso.")

    df = pd.DataFrame(results)
    return df

"""
valuation.py — Motor de Valuation Algorítmico (FairPrice)

Modelos implementados:
  1. Gordon Growth Model (DDM) — para empresas de dividendos estáveis
  2. 2-Stage Discounted Cash Flow (FCD) — para empresas de crescimento/cíclicas
  3. Múltiplos Relativos (P/L Histórico × LPA) — cross-check universal

A seleção do modelo é feita automaticamente com base no perfil setorial.
"""

import numpy as np


# ─────────────────────────────────────────────
# Setores → Modelo (Classification Logic)
# ─────────────────────────────────────────────

DDM_SECTORS = {
    'Utilities', 'Financial Services', 'Communication Services',
}

DCF_SECTORS = {
    'Consumer Cyclical', 'Consumer Defensive', 'Technology',
    'Basic Materials', 'Industrials', 'Healthcare', 'Energy',
    'Real Estate',
}


def classify_model(sector: str, div_yield: float, eps: float,
                   fcf_per_share: float) -> str:
    """
    Classify which valuation model is most appropriate for a stock.

    Returns one of: 'DDM', 'DCF', 'Múltiplos'
    """
    sector_clean = sector.strip() if sector else ''

    # Rule 1: Utilities, Financial Services, Communication → DDM (if pays dividends)
    if sector_clean in DDM_SECTORS and div_yield > 1.0:
        return 'DDM'

    # Rule 2: Growth/Cyclical sectors → DCF (if has positive FCF)
    if sector_clean in DCF_SECTORS and fcf_per_share > 0:
        return 'DCF'

    # Rule 3: DDM sectors but low dividends → fallback to DCF or Múltiplos
    if sector_clean in DDM_SECTORS:
        if fcf_per_share > 0:
            return 'DCF'
        if eps > 0:
            return 'Múltiplos'

    # Rule 4: Any sector with positive FCF → DCF
    if fcf_per_share > 0:
        return 'DCF'

    # Rule 5: Positive earnings → Múltiplos
    if eps > 0:
        return 'Múltiplos'

    # Rule 6: No usable data
    return 'Múltiplos'


# ─────────────────────────────────────────────
# Model 1: Gordon Growth Model (DDM)
# ─────────────────────────────────────────────

def gordon_growth_model(dpy: float, div_growth: float, ke: float) -> dict:
    """
    Calculate fair value using the Gordon Growth Model.

    P_justo = D1 / (ke - g)

    Parameters:
        dpy: Current annual dividend per share
        div_growth: Expected dividend growth rate (decimal, e.g. 0.05 = 5%)
        ke: Cost of equity / discount rate (decimal, e.g. 0.1925 = 19.25%)

    Returns:
        dict with fair_value, d1, reasoning
    """
    if dpy <= 0 or ke <= div_growth or ke <= 0:
        return {
            'fair_value': 0,
            'reasoning': 'DDM inválido: dividendos insuficientes ou Ke ≤ g.',
            'valid': False,
        }

    d1 = dpy * (1 + div_growth)
    fair_value = d1 / (ke - div_growth)

    reasoning = (
        f"D₁ = R${dpy:.2f} × (1 + {div_growth:.1%}) = R${d1:.2f}\n"
        f"Ke = {ke:.1%}\n"
        f"g (crescimento) = {div_growth:.1%}\n"
        f"P_justo = R${d1:.2f} / ({ke:.1%} − {div_growth:.1%}) = R${fair_value:.2f}"
    )

    return {
        'fair_value': round(fair_value, 2),
        'd1': round(d1, 4),
        'ke': ke,
        'g': div_growth,
        'reasoning': reasoning,
        'valid': fair_value > 0,
    }


# ─────────────────────────────────────────────
# Model 2: 2-Stage Discounted Cash Flow (FCD)
# ─────────────────────────────────────────────

def two_stage_dcf(fcf_per_share: float, fcf_growth: float,
                  wacc: float, perpetuity_g: float,
                  projection_years: int = 5) -> dict:
    """
    Calculate fair value using a 2-Stage DCF.

    Stage 1: FCF grows at fcf_growth for projection_years
    Stage 2: Perpetuity at perpetuity_g

    Parameters:
        fcf_per_share: Current free cash flow per share
        fcf_growth: High-growth rate for stage 1 (decimal)
        wacc: Weighted Average Cost of Capital (decimal)
        perpetuity_g: Perpetuity growth rate for stage 2 (decimal)
        projection_years: Number of years for stage 1

    Returns:
        dict with fair_value, stage1_pv, terminal_value, reasoning
    """
    if fcf_per_share <= 0 or wacc <= perpetuity_g or wacc <= 0:
        return {
            'fair_value': 0,
            'reasoning': 'FCD inválido: FCF negativo ou WACC ≤ g_perpétuo.',
            'valid': False,
        }

    # Stage 1: Discount projected FCFs
    stage1_pv = 0.0
    projected_fcfs = []
    fcf_t = fcf_per_share
    for t in range(1, projection_years + 1):
        fcf_t = fcf_t * (1 + fcf_growth) if t > 1 else fcf_per_share * (1 + fcf_growth)
        pv = fcf_t / ((1 + wacc) ** t)
        stage1_pv += pv
        projected_fcfs.append((t, round(fcf_t, 4), round(pv, 4)))

    # Stage 2: Terminal value (perpetuity)
    terminal_fcf = fcf_t * (1 + perpetuity_g)
    terminal_value = terminal_fcf / (wacc - perpetuity_g)
    terminal_pv = terminal_value / ((1 + wacc) ** projection_years)

    fair_value = stage1_pv + terminal_pv

    # Build reasoning text
    reasoning_lines = [
        f"FCF/ação atual = R${fcf_per_share:.2f}",
        f"Crescimento Fase 1 ({projection_years}a) = {fcf_growth:.1%}",
        f"WACC = {wacc:.1%}",
        f"g perpétuo = {perpetuity_g:.1%}",
        f"",
        f"VP Fase 1 (Σ FCFs descontados) = R${stage1_pv:.2f}",
        f"Valor Terminal = R${terminal_value:.2f}",
        f"VP Terminal = R${terminal_pv:.2f}",
        f"",
        f"P_justo = R${stage1_pv:.2f} + R${terminal_pv:.2f} = R${fair_value:.2f}",
    ]

    return {
        'fair_value': round(fair_value, 2),
        'stage1_pv': round(stage1_pv, 2),
        'terminal_value': round(terminal_value, 2),
        'terminal_pv': round(terminal_pv, 2),
        'projected_fcfs': projected_fcfs,
        'reasoning': '\n'.join(reasoning_lines),
        'valid': fair_value > 0,
    }


# ─────────────────────────────────────────────
# Model 3: Múltiplos Relativos (P/L Histórico)
# ─────────────────────────────────────────────

def relative_multiples(eps: float, historical_pe: float,
                       custom_pe: float = None) -> dict:
    """
    Calculate fair value using historical P/E multiple.

    P_justo = LPA × P/L Histórico (or custom P/E)

    Parameters:
        eps: Earnings per share
        historical_pe: Average historical P/E (5 years)
        custom_pe: Optional user-defined target P/E

    Returns:
        dict with fair_value, reasoning
    """
    target_pe = custom_pe if custom_pe and custom_pe > 0 else historical_pe

    if eps <= 0 or target_pe <= 0:
        return {
            'fair_value': 0,
            'reasoning': 'Múltiplos inválido: LPA ≤ 0 ou P/L ≤ 0.',
            'valid': False,
        }

    fair_value = eps * target_pe
    pe_source = "customizado" if custom_pe and custom_pe > 0 else "histórico médio (5a)"

    reasoning = (
        f"LPA (EPS) = R${eps:.2f}\n"
        f"P/L {pe_source} = {target_pe:.1f}x\n"
        f"P_justo = R${eps:.2f} × {target_pe:.1f} = R${fair_value:.2f}"
    )

    return {
        'fair_value': round(fair_value, 2),
        'target_pe': round(target_pe, 2),
        'pe_source': pe_source,
        'reasoning': reasoning,
        'valid': fair_value > 0,
    }


# ─────────────────────────────────────────────
# ValuationEngine — Orchestrator
# ─────────────────────────────────────────────

class ValuationEngine:
    """
    Orchestrates valuation model selection and execution.

    Default parameters reflect the current Brazilian macroeconomic environment:
    - Selic at 14.25%
    - Equity Risk Premium ~5%
    - Ke ≈ 19.25%
    - WACC ≈ 16% (blended cost considering debt at ~CDI)
    """

    DEFAULT_KE = 0.1925       # 14.25% Selic + 5% ERP
    DEFAULT_WACC = 0.16       # Blended WACC
    DEFAULT_PERP_G = 0.05     # 5% perpetuity growth
    DEFAULT_CUSTOM_PE = None  # Use historical P/E

    def __init__(self, ke=None, wacc=None, perpetuity_g=None, custom_pe=None):
        self.ke = ke or self.DEFAULT_KE
        self.wacc = wacc or self.DEFAULT_WACC
        self.perpetuity_g = perpetuity_g or self.DEFAULT_PERP_G
        self.custom_pe = custom_pe or self.DEFAULT_CUSTOM_PE

    def valuate(self, stock_data: dict) -> dict:
        """
        Run the optimal valuation model for a given stock.

        Parameters:
            stock_data: dict from data_provider.get_stock_data()

        Returns:
            dict with ticker, sector, model_used, current_price,
                  fair_value, upside_pct, reasoning, and model details
        """
        if stock_data is None:
            return self._empty_result("N/A")

        ticker = stock_data.get('ticker', 'N/A')
        sector = stock_data.get('sector', 'N/A')
        current_price = stock_data.get('current_price', 0)
        eps = stock_data.get('eps', 0)
        dpy = stock_data.get('dpy', 0)
        div_yield = stock_data.get('div_yield', 0)
        div_growth = stock_data.get('div_growth', 0.05)
        fcf_per_share = stock_data.get('fcf_per_share', 0)
        fcf_growth = stock_data.get('fcf_growth', 0.05)
        historical_pe = stock_data.get('historical_pe', 0)
        net_debt_ebitda = stock_data.get('net_debt_ebitda', 0)
        interest_coverage = stock_data.get('interest_coverage', 999.0)

        # Classify model
        model = classify_model(sector, div_yield, eps, fcf_per_share)

        # Execute primary model
        result = None
        if model == 'DDM':
            result = gordon_growth_model(dpy, div_growth, self.ke)
            model_display = 'Gordon Growth (DDM)'
            model_icon = '💰'
        elif model == 'DCF':
            result = two_stage_dcf(fcf_per_share, fcf_growth, self.wacc,
                                    self.perpetuity_g)
            model_display = 'FCD 2 Estágios (DCF)'
            model_icon = '📈'
        else:
            result = relative_multiples(eps, historical_pe, self.custom_pe)
            model_display = 'Múltiplos Relativos'
            model_icon = '📊'

        # If primary model fails, try fallbacks
        if not result.get('valid', False):
            # Try DCF as first fallback
            if model != 'DCF' and fcf_per_share > 0:
                result = two_stage_dcf(fcf_per_share, fcf_growth,
                                        self.wacc, self.perpetuity_g)
                model_display = 'FCD 2 Estágios (DCF) [fallback]'
                model_icon = '📈'
            # Try Múltiplos as second fallback
            if not result.get('valid', False) and eps > 0:
                result = relative_multiples(eps, historical_pe, self.custom_pe)
                model_display = 'Múltiplos Relativos [fallback]'
                model_icon = '📊'

        fair_value = result.get('fair_value', 0)
        reasoning = result.get('reasoning', '')

        # Margin of safety / upside
        upside_pct = 0.0
        if current_price > 0 and fair_value > 0:
            upside_pct = ((fair_value - current_price) / current_price) * 100

        # Cross-check: Múltiplos Relativos (always calculated)
        cross_check = None
        if model != 'Múltiplos' and eps > 0 and historical_pe > 0:
            cross_check = relative_multiples(eps, historical_pe, self.custom_pe)

        return {
            'ticker': ticker,
            'sector': sector,
            'model_used': model_display,
            'model_icon': model_icon,
            'current_price': current_price,
            'fair_value': fair_value,
            'upside_pct': round(upside_pct, 1),
            'reasoning': reasoning,
            'cross_check': cross_check,
            'eps': eps,
            'dpy': dpy,
            'div_yield': div_yield,
            'fcf_per_share': fcf_per_share,
            'net_debt_ebitda': net_debt_ebitda,
            'interest_coverage': interest_coverage,
            'valid': result.get('valid', False),
        }

    def valuate_batch(self, stocks_df, progress_callback=None) -> list[dict]:
        """
        Run valuation for all stocks in a DataFrame.
        """
        results = []
        total = len(stocks_df)
        for idx, (_, row) in enumerate(stocks_df.iterrows()):
            stock_data = row.to_dict()
            val_result = self.valuate(stock_data)
            if val_result.get('valid', False):
                results.append(val_result)
            if progress_callback:
                progress_callback((idx + 1) / total)

        # Sort by upside descending
        results.sort(key=lambda x: x.get('upside_pct', 0), reverse=True)
        return results

    def _empty_result(self, ticker):
        return {
            'ticker': ticker,
            'sector': 'N/A',
            'model_used': 'N/A',
            'model_icon': '❌',
            'current_price': 0,
            'fair_value': 0,
            'upside_pct': 0,
            'reasoning': 'Dados insuficientes para valuation.',
            'cross_check': None,
            'eps': 0,
            'dpy': 0,
            'div_yield': 0,
            'fcf_per_share': 0,
            'net_debt_ebitda': 0,
            'interest_coverage': 999.0,
            'valid': False,
        }

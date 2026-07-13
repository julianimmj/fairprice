"""
app.py — FairPrice: Valuation Algorítmico para Ações B3

Interface Streamlit premium com duas abas:
  Tab 1: Avaliação Individual de uma ação
  Tab 2: TOP 10 Ações Mais Descontadas (screening automático)
"""

import streamlit as st
import pandas as pd
import numpy as np

from src.data_provider import get_stock_data, scan_all_stocks, TICKERS_B3
from src.valuation import ValuationEngine

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="FairPrice — Valuation Algorítmico B3",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================
# PREMIUM CSS
# =====================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');

/* ── Global ── */
html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif !important;
}
.stApp {
    background: linear-gradient(135deg, #0e1117 0%, #151b28 50%, #1a1e29 100%);
    color: #e2e8f0;
}

/* ── Main Title ── */
.fp-title {
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00E676 0%, #00B0FF 50%, #7C4DFF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0;
    padding-bottom: 0;
    letter-spacing: -0.5px;
}
.fp-subtitle {
    color: #94a3b8;
    font-weight: 300;
    font-size: 1.05rem;
    margin-bottom: 2rem;
    letter-spacing: 0.5px;
}

/* ── Glass Cards ── */
.glass-card {
    background: rgba(30, 41, 59, 0.45);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.glass-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0, 230, 118, 0.08);
    border-color: rgba(0, 230, 118, 0.15);
}

/* ── Hero Card (Single Valuation) ── */
.hero-card {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.6) 0%, rgba(20, 30, 48, 0.8) 100%);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    padding: 32px;
    margin: 16px 0 24px 0;
    box-shadow: 0 8px 40px rgba(0, 0, 0, 0.3);
    position: relative;
    overflow: hidden;
}
.hero-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #00E676, #00B0FF, #7C4DFF);
    border-radius: 20px 20px 0 0;
}

/* ── Price Display ── */
.price-current {
    font-size: 1.8rem;
    font-weight: 700;
    color: #94a3b8;
}
.price-fair {
    font-size: 2.6rem;
    font-weight: 800;
    margin: 4px 0;
}
.price-fair.upside { color: #00E676; }
.price-fair.downside { color: #FF1744; }

/* ── Badge ── */
.badge {
    display: inline-block;
    padding: 8px 20px;
    border-radius: 30px;
    font-weight: 700;
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.badge-green {
    background: rgba(0, 230, 118, 0.12);
    color: #00E676;
    border: 1px solid rgba(0, 230, 118, 0.25);
    box-shadow: 0 0 16px rgba(0, 230, 118, 0.1);
}
.badge-red {
    background: rgba(255, 23, 68, 0.12);
    color: #FF1744;
    border: 1px solid rgba(255, 23, 68, 0.25);
    box-shadow: 0 0 16px rgba(255, 23, 68, 0.1);
}
.badge-blue {
    background: rgba(0, 176, 255, 0.12);
    color: #00B0FF;
    border: 1px solid rgba(0, 176, 255, 0.25);
}
.badge-purple {
    background: rgba(124, 77, 255, 0.12);
    color: #7C4DFF;
    border: 1px solid rgba(124, 77, 255, 0.25);
}

/* ── Model Tag ── */
.model-tag {
    display: inline-block;
    padding: 5px 14px;
    border-radius: 8px;
    font-size: 0.8rem;
    font-weight: 600;
    color: #00B0FF;
    background: rgba(0, 176, 255, 0.08);
    border: 1px solid rgba(0, 176, 255, 0.2);
    margin: 6px 0;
}

/* ── Metric Row ── */
.metric-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    margin: 12px 0;
    flex-wrap: wrap;
}
.metric-item {
    flex: 1;
    text-align: center;
    padding: 12px 8px;
    background: rgba(15, 23, 42, 0.4);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.04);
    min-width: 100px;
}
.metric-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    color: #64748b;
    font-weight: 600;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.metric-value {
    font-size: 1.15rem;
    font-weight: 600;
    color: #e2e8f0;
}

/* ── Top 10 Table Card ── */
.rank-card {
    background: rgba(30, 41, 59, 0.4);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    transition: all 0.25s ease;
}
.rank-card:hover {
    transform: translateX(4px);
    border-color: rgba(0, 230, 118, 0.2);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}
.rank-number {
    font-size: 1.6rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00E676, #00B0FF);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-right: 16px;
    min-width: 36px;
}
.rank-ticker {
    font-size: 1.2rem;
    font-weight: 700;
    color: #f8fafc;
    letter-spacing: 0.5px;
}
.rank-sector {
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 400;
}
.rank-prices {
    text-align: right;
}
.rank-fair-val {
    font-size: 1.1rem;
    font-weight: 700;
    color: #00E676;
}
.rank-curr-val {
    font-size: 0.85rem;
    color: #94a3b8;
}

/* ── Sidebar ── */
.stSidebar {
    background-color: rgba(15, 23, 42, 0.95);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* ── Reasoning Box ── */
.reasoning-box {
    background: rgba(15, 23, 42, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 12px;
    padding: 16px 20px;
    font-family: 'Outfit', monospace;
    font-size: 0.88rem;
    color: #94a3b8;
    line-height: 1.7;
    white-space: pre-wrap;
}

/* ── Divider ── */
.fp-divider {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
    margin: 20px 0;
}

/* ── Tab styling ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0;
    padding: 10px 24px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# HEADER
# =====================================================
st.markdown('<div class="fp-title">FairPrice</div>', unsafe_allow_html=True)
st.markdown('<div class="fp-subtitle">Motor de Valuation Algorítmico para Ações B3 — '
            'Gordon Growth · FCD 2 Estágios · Múltiplos Relativos</div>',
            unsafe_allow_html=True)


# =====================================================
# SIDEBAR — Parameters
# =====================================================
st.sidebar.markdown("## 🎯 Painel de Controle")
st.sidebar.markdown("Ajuste os parâmetros macroeconômicos do motor de valuation.")
st.sidebar.markdown("---")

wacc_pct = st.sidebar.slider(
    "📉 WACC (%)", min_value=8.0, max_value=25.0, value=16.0, step=0.25,
    help="Custo Médio Ponderado de Capital. Default: 16% (Selic 14.25% + spread)")
ke_pct = st.sidebar.slider(
    "🏦 Ke — Custo de Equity (%)", min_value=8.0, max_value=30.0, value=19.25, step=0.25,
    help="Custo do capital próprio (DDM). Default: 19.25% (Selic + ERP)")
perp_g_pct = st.sidebar.slider(
    "🌱 Crescimento Perpétuo g (%)", min_value=2.0, max_value=10.0, value=5.0, step=0.25,
    help="Taxa de crescimento na perpetuidade (Fase 2 do DCF). Default: 5%")

st.sidebar.markdown("---")
use_custom_pe = st.sidebar.toggle("📊 Usar P/L customizado", value=False,
                                   help="Override do P/L histórico no modelo de Múltiplos")
custom_pe_val = None
if use_custom_pe:
    custom_pe_val = st.sidebar.slider("P/L Alvo", min_value=5.0, max_value=30.0,
                                       value=12.0, step=0.5)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡️ Filtros de Segurança Financeira")
filter_high_debt = st.sidebar.toggle(
    "Excluir Dívida Alta", value=True,
    help="Exclui empresas com Dív.Líq/EBITDA > 3.5x (ou > 4.5x para Utilities). Bancos e seguradoras são isentos por não utilizarem EBITDA.")
filter_low_coverage = st.sidebar.toggle(
    "Excluir Solvência Tensa", value=True,
    help="Exclui empresas cuja cobertura de juros (EBIT / Despesa de Juros) é menor que 1.5x (empresas incapazes de cobrir despesas financeiras com lucro operacional).")

st.sidebar.markdown("---")
st.sidebar.markdown(
    "<p style='font-size:0.75rem; color:#475569; text-align:center;'>"
    "FairPrice v1.0 — Ecossistema Antigravity<br>"
    "Dados via Yahoo Finance · Não é recomendação de investimento</p>",
    unsafe_allow_html=True)

# Create engine with user parameters
engine = ValuationEngine(
    ke=ke_pct / 100,
    wacc=wacc_pct / 100,
    perpetuity_g=perp_g_pct / 100,
    custom_pe=custom_pe_val,
)


# =====================================================
# TABS
# =====================================================
tab1, tab2 = st.tabs(["🎯  Avaliação Individual", "🏆  TOP 10 Descontadas"])


# ─────────────────────────────────────────────
# TAB 1: Single Stock Valuation
# ─────────────────────────────────────────────
with tab1:
    st.markdown("#### Insira o ticker de uma ação B3 para calcular o Preço Justo algorítmico.")

    col_input, col_spacer = st.columns([2, 3])
    with col_input:
        ticker_input = st.text_input(
            "Ticker", value="", placeholder="Ex: WEGE3, PETR4, TAEE11...",
            label_visibility="collapsed")

    if ticker_input:
        ticker_clean = ticker_input.strip().upper().replace(".SA", "")
        if len(ticker_clean) < 4:
            st.warning("Insira um ticker válido (ex: WEGE3, VALE3, ITUB4).")
        else:
            with st.spinner(f"Analisando {ticker_clean}..."):
                stock_data = get_stock_data(ticker_clean)

            if stock_data is None:
                st.error(f"❌ Não foi possível obter dados para **{ticker_clean}**. "
                         "Verifique o ticker ou tente novamente.")
            else:
                val = engine.valuate(stock_data)

                if not val.get('valid', False):
                    st.warning(f"⚠️ Dados insuficientes para calcular o Preço Justo de **{ticker_clean}**.")
                    st.markdown(f"<div class='reasoning-box'>{val.get('reasoning', '')}</div>",
                                unsafe_allow_html=True)
                else:
                    current_price = val['current_price']
                    fair_value = val['fair_value']
                    upside = val['upside_pct']
                    is_discount = upside > 0

                    # ── Hero Card ──
                    upside_class = "upside" if is_discount else "downside"
                    badge_class = "badge-green" if is_discount else "badge-red"
                    badge_text = f"▲ {upside:.1f}% DESCONTO" if is_discount else f"▼ {abs(upside):.1f}% SOBREPREÇO"

                    hero_header_html = f"""
                    <div class="hero-card">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap;">
                            <div>
                                <div style="font-size: 2rem; font-weight: 800; color: #f8fafc; letter-spacing: 1px;">
                                    {val['ticker']}
                                </div>
                                <div class="model-tag">{val['model_icon']} {val['model_used']}</div>
                                <div style="font-size: 0.85rem; color: #64748b; margin-top: 4px;">
                                    Setor: {val['sector']}
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <div class="price-current">Atual: R$ {current_price:.2f}</div>
                                <div class="price-fair {upside_class}">R$ {fair_value:.2f}</div>
                                <div class="badge {badge_class}">{badge_text}</div>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(hero_header_html, unsafe_allow_html=True)

                    interest_cov_val = val.get('interest_coverage', 999.0)
                    interest_cov_display = f"{interest_cov_val:.1f}x" if interest_cov_val < 990 else "Isento"

                    metrics_html = f"""
                    <div style="background: rgba(30, 41, 59, 0.45); backdrop-filter: blur(16px); border: 1px solid rgba(255,255,255,0.06); border-radius: 0 0 16px 16px; padding: 20px 24px; margin-top: -18px; margin-bottom: 16px;">
                        <div class="metric-row">
                            <div class="metric-item">
                                <div class="metric-label">LPA (EPS)</div>
                                <div class="metric-value">R$ {val['eps']:.2f}</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">Div. Yield</div>
                                <div class="metric-value">{val['div_yield']:.1f}%</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">FCF/Ação</div>
                                <div class="metric-value">R$ {val['fcf_per_share']:.2f}</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">Dív.Líq/EBITDA</div>
                                <div class="metric-value">{val['net_debt_ebitda']:.1f}x</div>
                            </div>
                            <div class="metric-item">
                                <div class="metric-label">Cobert. Juros</div>
                                <div class="metric-value">{interest_cov_display}</div>
                            </div>
                        </div>
                    </div>
                    """
                    st.markdown(metrics_html, unsafe_allow_html=True)

                    # ── Reasoning Expander ──
                    with st.expander("📐 Raciocínio do Modelo (passo a passo)", expanded=False):
                        st.markdown(f"<div class='reasoning-box'>{val['reasoning']}</div>",
                                    unsafe_allow_html=True)

                    # ── Cross-check ──
                    if val.get('cross_check') and val['cross_check'].get('valid'):
                        cc = val['cross_check']
                        with st.expander("📊 Cross-Check — Múltiplos Relativos", expanded=False):
                            cc_upside = ((cc['fair_value'] - current_price) / current_price) * 100 if current_price > 0 else 0
                            cc_class = "upside" if cc_upside > 0 else "downside"
                            st.markdown(f"""
                            <div class="glass-card">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-size: 0.85rem; color: #64748b;">Preço Justo (Múltiplos)</div>
                                        <div class="price-fair {cc_class}" style="font-size: 1.8rem;">R$ {cc['fair_value']:.2f}</div>
                                    </div>
                                    <div class="badge {'badge-green' if cc_upside > 0 else 'badge-red'}">
                                        {'▲' if cc_upside > 0 else '▼'} {abs(cc_upside):.1f}%
                                    </div>
                                </div>
                                <div class="reasoning-box" style="margin-top: 12px;">{cc['reasoning']}</div>
                            </div>
                            """, unsafe_allow_html=True)
    else:
        # Empty state
        st.markdown("""
        <div class="glass-card" style="text-align: center; padding: 48px 24px;">
            <div style="font-size: 3rem; margin-bottom: 12px;">🎯</div>
            <div style="font-size: 1.2rem; color: #94a3b8; font-weight: 400;">
                Insira um ticker acima para iniciar a análise de valuation
            </div>
            <div style="font-size: 0.85rem; color: #475569; margin-top: 8px;">
                O motor seleciona automaticamente o melhor modelo (DDM, DCF ou Múltiplos) conforme o perfil setorial
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# TAB 2: TOP 10 Discounted Stocks
# ─────────────────────────────────────────────
with tab2:
    st.markdown("#### Screening algorítmico das ações B3 mais descontadas")
    st.markdown("<p style='color: #64748b; font-size: 0.9rem;'>"
                "O motor varre ~150 ações da B3, calcula o Preço Justo de cada uma e "
                "ordena pelas maiores margens de segurança.</p>", unsafe_allow_html=True)

    # Filters
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        sector_filter = st.multiselect(
            "Filtrar por Setor",
            options=["Todos", "Utilities", "Financial Services", "Consumer Cyclical",
                     "Consumer Defensive", "Basic Materials", "Industrials",
                     "Technology", "Healthcare", "Energy", "Real Estate",
                     "Communication Services"],
            default=["Todos"])
    with col_f2:
        model_filter = st.multiselect(
            "Filtrar por Modelo",
            options=["Todos", "Gordon Growth (DDM)", "FCD 2 Estágios (DCF)", "Múltiplos Relativos"],
            default=["Todos"])
    with col_f3:
        top_n = st.selectbox("Quantidade", options=[10, 20, 30, 50], index=0)

    run_btn = st.button("🚀 INICIAR SCREENING", type="primary", use_container_width=True)

    if run_btn:
        status_text = st.empty()
        progress_bar = st.progress(0)

        # Phase 1: Data acquisition
        status_text.markdown("**📡 Fase 1/2** — Adquirindo dados financeiros de ~150 ativos da B3...")
        with st.spinner("Conectando ao Yahoo Finance..."):
            stocks_df = scan_all_stocks(
                tickers=TICKERS_B3,
                max_workers=4,
                progress_callback=lambda p: progress_bar.progress(p * 0.6),
                status_callback=lambda s: None,
            )

        if stocks_df.empty:
            st.error("❌ Não foi possível obter dados. Tente novamente em alguns minutos.")
        else:
            # Phase 2: Valuation
            status_text.markdown(f"**📐 Fase 2/2** — Executando valuation algorítmico em {len(stocks_df)} ativos...")
            val_results = engine.valuate_batch(
                stocks_df,
                progress_callback=lambda p: progress_bar.progress(0.6 + p * 0.4),
            )

            progress_bar.progress(1.0)

            # Apply filters
            filtered = val_results.copy()
            if "Todos" not in sector_filter and sector_filter:
                filtered = [r for r in filtered if r['sector'] in sector_filter]
            if "Todos" not in model_filter and model_filter:
                model_keys = []
                for m in model_filter:
                    if "Gordon" in m or "DDM" in m:
                        model_keys.append("DDM")
                    elif "FCD" in m or "DCF" in m:
                        model_keys.append("DCF")
                    elif "Múltiplos" in m:
                        model_keys.append("Múltiplos")
                filtered = [r for r in filtered if any(k in r['model_used'] for k in model_keys)]

            # Financial safety filters
            if filter_high_debt:
                filtered_clean = []
                for r in filtered:
                    if r['sector'] == 'Financial Services':
                        filtered_clean.append(r)
                    elif r['sector'] == 'Utilities':
                        if r['net_debt_ebitda'] <= 4.5:
                            filtered_clean.append(r)
                    else:
                        if r['net_debt_ebitda'] <= 3.5:
                            filtered_clean.append(r)
                filtered = filtered_clean

            if filter_low_coverage:
                filtered = [r for r in filtered if r['interest_coverage'] >= 1.5]

            # Only positive upside
            filtered = [r for r in filtered if r.get('upside_pct', 0) > 0]
            filtered = filtered[:top_n]

            status_text.markdown(
                f"**✅ Concluído!** Encontramos **{len(filtered)}** ações com potencial de upside "
                f"entre {len(val_results)} avaliadas.")

            if not filtered:
                st.info("Nenhuma ação com desconto significativo encontrada com os filtros selecionados.")
            else:
                # ── TOP 3 Highlight Cards ──
                st.markdown("<br>", unsafe_allow_html=True)
                top3 = filtered[:3]
                cols = st.columns(len(top3))

                for i, (col, r) in enumerate(zip(cols, top3)):
                    with col:
                        medal = ["🥇", "🥈", "🥉"][i]
                        st.markdown(f"""
                        <div class="hero-card" style="padding: 20px;">
                            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                                <span style="font-size: 1.6rem;">{medal}</span>
                                <span style="font-size: 1.4rem; font-weight: 800; color: #f8fafc;">{r['ticker']}</span>
                            </div>
                            <div class="model-tag">{r['model_icon']} {r['model_used']}</div>
                            <div style="font-size: 0.75rem; color: #64748b; margin: 4px 0 12px 0;">{r['sector']}</div>
                            <div style="display: flex; justify-content: space-between; align-items: flex-end;">
                                <div>
                                    <div style="font-size: 0.75rem; color: #64748b;">Atual</div>
                                    <div style="font-size: 1rem; color: #94a3b8;">R$ {r['current_price']:.2f}</div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-size: 0.75rem; color: #64748b;">Preço Justo</div>
                                    <div style="font-size: 1.2rem; font-weight: 700; color: #00E676;">R$ {r['fair_value']:.2f}</div>
                                </div>
                            </div>
                            <div style="text-align: center; margin-top: 12px;">
                                <span class="badge badge-green">▲ {r['upside_pct']:.1f}%</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                # ── Full Ranking ──
                st.markdown("<br>", unsafe_allow_html=True)
                st.markdown(f"##### 📋 Ranking Completo — TOP {len(filtered)} Ações Descontadas")

                for i, r in enumerate(filtered):
                    badge_html = (f'<span class="badge badge-green">▲ {r["upside_pct"]:.1f}%</span>')
                    alav_desc = f" · Dív/EBITDA: {r['net_debt_ebitda']:.1f}x" if r['sector'] != 'Financial Services' else ""
                    cov_val = r.get('interest_coverage', 999.0)
                    cov_desc = f" · Cob.Juros: {cov_val:.1f}x" if cov_val < 990 else ""

                    st.markdown(f"""
                    <div class="rank-card">
                        <div style="display: flex; align-items: center;">
                            <span class="rank-number">#{i+1}</span>
                            <div>
                                <div class="rank-ticker">{r['ticker']}</div>
                                <div class="rank-sector">{r['sector']} · {r['model_icon']} {r['model_used']}{alav_desc}{cov_desc}</div>
                            </div>
                        </div>
                        <div class="rank-prices">
                            <div class="rank-fair-val">R$ {r['fair_value']:.2f}</div>
                            <div class="rank-curr-val">Atual: R$ {r['current_price']:.2f}</div>
                        </div>
                        <div>{badge_html}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # ── DataFrame export ──
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("📊 Exportar tabela completa (DataFrame)", expanded=False):
                    df_export = pd.DataFrame([{
                        'Ticker': r['ticker'],
                        'Setor': r['sector'],
                        'Modelo': r['model_used'],
                        'Preço Atual (R$)': r['current_price'],
                        'Preço Justo (R$)': r['fair_value'],
                        'Upside (%)': r['upside_pct'],
                        'LPA': r['eps'],
                        'Div.Yield (%)': r['div_yield'],
                        'FCF/Ação': r['fcf_per_share'],
                        'Dív.Líq/EBITDA': r['net_debt_ebitda'] if r['sector'] != 'Financial Services' else np.nan,
                        'Cobertura Juros': r['interest_coverage'] if r['interest_coverage'] < 990 else np.nan,
                    } for r in filtered])
                    st.dataframe(df_export, use_container_width=True, hide_index=True)

    else:
        # Empty state
        st.markdown("""
        <div class="glass-card" style="text-align: center; padding: 48px 24px;">
            <div style="font-size: 3rem; margin-bottom: 12px;">🏆</div>
            <div style="font-size: 1.2rem; color: #94a3b8; font-weight: 400;">
                Clique em <strong>INICIAR SCREENING</strong> para varrer o mercado
            </div>
            <div style="font-size: 0.85rem; color: #475569; margin-top: 8px;">
                O motor avalia ~150 ações da B3 e apresenta as mais descontadas por margem de segurança
            </div>
        </div>
        """, unsafe_allow_html=True)

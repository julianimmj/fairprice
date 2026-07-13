# FairPrice — Valuation Algorítmico para Ações B3 🎯📊

Aplicação web de **screening e valuation automatizado** de ações brasileiras (B3).

O motor de precificação seleciona dinamicamente entre **três modelos** de valuation conforme o perfil setorial de cada empresa:

| Modelo | Aplicação | Equação |
|--------|-----------|---------|
| **Gordon Growth (DDM)** | Utilities, Financeiras, Saneamento | P = D₁ / (Ke - g) |
| **FCD 2 Estágios (DCF)** | Crescimento, Cíclicas, Varejo, Tecnologia | Σ FCF/(1+WACC)^t + Perpetuidade |
| **Múltiplos Relativos** | Cross-check universal | P = LPA × P/L Histórico |

## 🚀 Deploy

A aplicação está hospedada no Streamlit Cloud:
- **URL**: [fairprice.streamlit.app](https://fairprice.streamlit.app)

## 📦 Stack

- Python 3.12
- Streamlit
- yfinance
- pandas / numpy

## 🏗️ Estrutura

```
├── app.py                  # Frontend Streamlit
├── src/
│   ├── data_provider.py    # Camada de dados (yfinance + cache)
│   └── valuation.py        # Motor de Valuation
├── requirements.txt
├── runtime.txt
└── .streamlit/config.toml
```

## 📐 Parâmetros Default

| Parâmetro | Valor Default | Ajustável |
|-----------|--------------|-----------|
| WACC | 16% | ✅ (8% - 25%) |
| Ke (Custo de Equity) | 19.25% | ✅ |
| Crescimento Perpétuo (g) | 5% | ✅ (2% - 10%) |
| P/L Alvo | Automático (histórico 5a) | ✅ (5x - 30x) |

## 🧑‍💻 Autor

Desenvolvido por **Julian** como parte do ecossistema **Antigravity**.

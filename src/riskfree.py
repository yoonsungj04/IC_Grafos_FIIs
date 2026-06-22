"""
Taxa livre de risco diária, alinhada às datas dos retornos.

Centraliza a escolha da rf (config.RISK_FREE_SOURCE) num único lugar para que a
tabela estática, o backtest rolante e os custos usem exatamente a mesma série de
excesso. O padrão é o CDI diário (BCB/SGS), que é o custo de oportunidade real
de um investidor no Brasil; usar rf=0 infla artificialmente o Sharpe.
"""
from __future__ import annotations

import pandas as pd

import config


def serie_rf_diaria(index: pd.Index) -> pd.Series:
    """
    Devolve a taxa livre de risco em decimal por pregão, reindexada a `index`.

    "cdi"      -> CDI diário do cache (preenche pregões faltantes para frente);
    "constant" -> RISK_FREE_ANNUAL convertido para taxa diária equivalente;
    "zero"     -> série de zeros (Sharpe vira retorno/vol, sem excesso).
    """
    origem = config.RISK_FREE_SOURCE
    if origem == "cdi":
        from src import data_load
        cdi = data_load.carregar_cdi()
        return cdi.reindex(index).ffill().bfill()
    if origem == "constant":
        rf_d = (1.0 + config.RISK_FREE_ANNUAL) ** (1.0 / config.TRADING_DAYS_PER_YEAR) - 1.0
        return pd.Series(rf_d, index=index)
    if origem == "zero":
        return pd.Series(0.0, index=index)
    raise ValueError(f"RISK_FREE_SOURCE inválido: {origem!r}")

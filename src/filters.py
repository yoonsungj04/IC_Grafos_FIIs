"""
Seleção determinística do universo a partir dos dados em cache.

A lista final de FIIs não é digitada à mão: parte do painel baixado e mantém
apenas os tickers com histórico suficiente e poucos dados faltantes na janela.
Assim a seleção é reprodutível e exclui ativos por idade/liquidez reais, nunca
por falha de download.
"""
from __future__ import annotations

import pandas as pd

import config


def selecionar_universo(precos: pd.DataFrame,
                        min_historico: int = config.MIN_HISTORY_DAYS,
                        max_faltante: float = config.MAX_MISSING_FRACTION) -> list[str]:
    """Tickers que cobrem toda a janela com histórico e completude suficientes."""
    total = len(precos)
    aprovados = []
    for tk in precos.columns:
        serie = precos[tk]
        n_validos = serie.notna().sum()
        if n_validos < min_historico:
            continue
        # fração faltante a partir do primeiro pregão com dado do ativo
        primeiro = serie.first_valid_index()
        janela = serie.loc[primeiro:]
        if janela.isna().mean() > max_faltante:
            continue
        # exige cobertura quase completa da janela total (ativos antigos)
        if n_validos < total * (1 - max_faltante):
            continue
        aprovados.append(tk)
    return sorted(aprovados)


def painel_universo(precos: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Recorta o painel para o universo e preenche pequenos buracos."""
    painel = precos[tickers].copy()
    painel = painel.ffill().dropna()
    return painel

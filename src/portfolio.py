"""
Formação das carteiras a partir da centralidade.

Central    = k vértices mais centrais.
Periférica = k vértices menos centrais (a recomendação de Pozzi et al., 2013).
Híbrida    = metade central, metade periférica.

A ponderação padrão é igualitária; há também a opção de peso inversamente
proporcional à volatilidade.
"""
from __future__ import annotations

import pandas as pd

import config


def _pesos(tickers: list[str], volatilidades: pd.Series | None,
           esquema: str) -> dict[str, float]:
    if esquema == "inverse_vol" and volatilidades is not None:
        inv = 1.0 / volatilidades[tickers]
        w = inv / inv.sum()
        return w.to_dict()
    n = len(tickers)
    return {tk: 1.0 / n for tk in tickers}


def selecionar_carteira(centralidades: pd.DataFrame, tipo: str, tamanho: int,
                        medida: str = config.RANKING_MEASURE,
                        volatilidades: pd.Series | None = None,
                        esquema: str = config.WEIGHTING) -> dict[str, float]:
    """Devolve {ticker: peso} para uma carteira (central/peripheral/hybrid)."""
    ordenado = centralidades[medida].sort_values(ascending=False)
    nomes = list(ordenado.index)

    if tamanho > len(nomes):
        tamanho = len(nomes)

    if tipo == "central":
        escolhidos = nomes[:tamanho]
    elif tipo == "peripheral":
        escolhidos = nomes[-tamanho:]
    elif tipo == "hybrid":
        metade = tamanho // 2
        escolhidos = nomes[:metade] + nomes[-(tamanho - metade):]
    else:
        raise ValueError(f"tipo de carteira desconhecido: {tipo}")

    return _pesos(escolhidos, volatilidades, esquema)


def retorno_carteira(retornos: pd.DataFrame, pesos: dict[str, float]) -> pd.Series:
    """
    Série de retornos SIMPLES da carteira no período (pesos fixos na janela).
    Recebe retornos por ativo (log ou simples conforme config) e devolve sempre
    retorno simples, pois o retorno de uma carteira é a média ponderada dos
    retornos simples dos ativos — não dos logarítmicos.
    """
    import numpy as np

    tickers = [t for t in pesos if t in retornos.columns]
    w = pd.Series({t: pesos[t] for t in tickers})
    w = w / w.sum()
    simples = np.expm1(retornos[tickers]) if config.RETURN_TYPE == "log" else retornos[tickers]
    return simples.mul(w, axis=1).sum(axis=1)

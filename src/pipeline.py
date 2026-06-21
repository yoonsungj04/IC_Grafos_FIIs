"""
Preparação dos dados comum a todas as etapas da análise.

Carrega o cache, aplica a seleção determinística do universo e devolve os
retornos prontos. Mantém uma única definição de universo/janela para que a
tabela estática, o backtest rolante e a comparação usem exatamente os mesmos
dados.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
from src import data_load, filters


def preparar_dados() -> dict:
    precos = data_load.carregar_precos(ajustado=True)
    universo = filters.selecionar_universo(precos)
    painel = filters.painel_universo(precos, universo)

    retornos_log = data_load.calcular_retornos(painel)

    # benchmark (XFIX11 ou IFIX) em retorno simples, alinhado às mesmas datas
    bench_path = config.RAW_DIR / "benchmark.csv"
    benchmark = None
    if bench_path.exists():
        b = pd.read_csv(bench_path, index_col=0, parse_dates=True).iloc[:, 0]
        benchmark = (b / b.shift(1) - 1.0).reindex(retornos_log.index).dropna()

    return {
        "precos": painel,
        "universo": universo,
        "retornos_log": retornos_log,
        "retornos_simples": np.expm1(retornos_log),
        "benchmark": benchmark,
    }

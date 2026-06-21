"""
Custos de transação, giro (turnover) e tributação (Fase C).

Giro entre rebalanceamentos consecutivos; custo de 0,3% sobre o giro; imposto de
15% sobre o ganho de capital realizado em cada janela. Para PF, os dividendos
dos FIIs são isentos, então o imposto incide apenas sobre a valorização.
Produz as curvas bruta e líquida.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config


def turnover(pesos_ant: dict[str, float], pesos_novos: dict[str, float]) -> float:
    """Giro de um período: metade da soma das variações absolutas de peso."""
    ativos = set(pesos_ant) | set(pesos_novos)
    return 0.5 * sum(abs(pesos_novos.get(a, 0.0) - pesos_ant.get(a, 0.0)) for a in ativos)


def aplicar_custos(retornos_janela: pd.Series, giro: float,
                   custo: float = config.TRANSACTION_COST,
                   imposto: float = config.CAPITAL_GAINS_TAX) -> pd.Series:
    """
    Aplica, sobre os retornos de uma janela de manutenção:
      - custo de transação proporcional ao giro, debitado no 1º dia da janela;
      - imposto de 15% sobre o ganho de capital, se a janela fechar no positivo.
    Recebe e devolve retornos simples.
    """
    r = retornos_janela.copy()
    if len(r) == 0:
        return r
    # custo de transação proporcional ao giro, debitado no 1º dia da janela
    r.iloc[0] = r.iloc[0] - custo * giro

    # imposto incide UMA vez sobre o ganho da janela (não a cada dia): debita o
    # tributo no último dia, ajustando o fator acumulado da janela.
    ganho = (1.0 + r).prod() - 1.0
    if ganho > 0:
        fator = (1.0 + ganho * (1.0 - imposto)) / (1.0 + ganho)
        r.iloc[-1] = (1.0 + r.iloc[-1]) * fator - 1.0
    return r


def aplicar_custos_serie(retornos: pd.Series, giros: pd.Series,
                         custo: float = config.TRANSACTION_COST,
                         imposto: float = config.CAPITAL_GAINS_TAX) -> pd.Series:
    """
    Aplica custos e imposto janela a janela sobre a série contínua fora da
    amostra. Cada data de rebalanceamento (índice de `giros`) inicia uma janela
    de manutenção; os custos do giro entram no 1º dia e o imposto incide ao
    final de cada janela positiva.
    """
    rebal = giros.index
    pos = np.searchsorted(rebal, retornos.index, side="right") - 1
    partes = []
    for w in range(len(rebal)):
        seg = retornos[pos == w]
        if seg.empty:
            continue
        partes.append(aplicar_custos(seg, float(giros.iloc[w]), custo, imposto))
    return pd.concat(partes).sort_index() if partes else retornos

"""
Custos de transação, giro (turnover) e tributação (Fase C).

Giro entre rebalanceamentos consecutivos; custo de 0,3% sobre o giro; imposto de
20% sobre o ganho de capital REALIZADO em cada janela — isto é, sobre a fração
da carteira efetivamente vendida no rebalanceamento (o giro), não sobre todo o
valor de mercado. Ganho não realizado (posições mantidas) é diferido, e os
dividendos de FII são isentos para PF. Produz as curvas bruta e líquida.
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
                   imposto: float = config.CAPITAL_GAINS_TAX,
                   ganho_preco: float | None = None) -> pd.Series:
    """
    Aplica, sobre os retornos (simples, TOTAIS — preço + dividendo) de uma janela
    de manutenção:
      - custo de transação proporcional ao giro, debitado no 1º dia da janela;
      - imposto de ganho de capital, debitado no último dia, incidente APENAS
        sobre o ganho de PREÇO REALIZADO. "Realizado" = a fração da carteira
        efetivamente vendida no rebalanceamento (o giro); "de preço" = a
        valorização da cota (`ganho_preco`), excluindo os dividendos, que são
        isentos para PF. O imposto em dinheiro é:
            tributo = imposto * giro * max(ganho_preco, 0)
        e é debitado da riqueza total (que inclui o dividendo isento). Se
        `ganho_preco` não for informado, cai no ganho TOTAL da janela como
        aproximação (compatibilidade retroativa).
    Recebe e devolve retornos simples.
    """
    r = retornos_janela.copy()
    if len(r) == 0:
        return r
    # custo de transação proporcional ao giro, debitado no 1º dia da janela
    r.iloc[0] = r.iloc[0] - custo * giro

    # fator bruto (líquido de custo) da janela sobre a riqueza total
    fator_bruto = (1.0 + r).prod()
    base = ganho_preco if ganho_preco is not None else (fator_bruto - 1.0)

    # imposto incide UMA vez, só sobre o ganho de preço realizado (giro):
    # debita o tributo em dinheiro no último dia, reduzindo o fator acumulado.
    tributo = imposto * giro * max(base, 0.0)
    if tributo > 0 and fator_bruto > 0:
        fator_pos_imposto = (fator_bruto - tributo) / fator_bruto
        r.iloc[-1] = (1.0 + r.iloc[-1]) * fator_pos_imposto - 1.0
    return r


def aplicar_custos_serie(retornos: pd.Series, giros: pd.Series,
                         custo: float = config.TRANSACTION_COST,
                         imposto: float = config.CAPITAL_GAINS_TAX,
                         retornos_preco: pd.Series | None = None) -> pd.Series:
    """
    Aplica custos e imposto janela a janela sobre a série contínua fora da
    amostra. Cada data de rebalanceamento (índice de `giros`) inicia uma janela
    de manutenção; os custos do giro entram no 1º dia e o imposto incide ao
    final de cada janela positiva.

    `retornos` são os retornos TOTAIS (preço + dividendo) da carteira, dos quais
    o tributo em dinheiro é debitado. `retornos_preco`, quando informado, são os
    retornos de PREÇO da MESMA carteira (mesmas datas), usados para calcular o
    ganho de capital tributável de cada janela — excluindo o dividendo isento.
    Sem ele, o imposto recai (aproximadamente) sobre o ganho total da janela.
    """
    rebal = giros.index
    pos = np.searchsorted(rebal, retornos.index, side="right") - 1
    partes = []
    for w in range(len(rebal)):
        seg = retornos[pos == w]
        if seg.empty:
            continue
        ganho_preco = None
        if retornos_preco is not None:
            seg_p = retornos_preco.reindex(seg.index).fillna(0.0)
            ganho_preco = float((1.0 + seg_p).prod() - 1.0)
        partes.append(aplicar_custos(seg, float(giros.iloc[w]), custo, imposto,
                                     ganho_preco=ganho_preco))
    return pd.concat(partes).sort_index() if partes else retornos

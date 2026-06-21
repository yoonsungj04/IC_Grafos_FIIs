"""
Engine de janela rolante (validação fora da amostra) — núcleo científico.

Corrige o viés de look-ahead: a cada passo, forma-se a carteira usando apenas os
FORMATION_DAYS anteriores (constrói o GPMF, calcula centralidade e seleciona as
carteiras) e mantém-se a carteira nos TEST_DAYS seguintes, que não entraram na
formação. Depois avança ROLL_STEP_DAYS e repete. As janelas de manutenção são
emendadas em curvas contínuas fora da amostra.

Tudo é construído sobre funções puras (matriz_distancia -> construir_gpmf ->
calcular_centralidades -> selecionar_carteira -> retorno_carteira), o que torna
cada etapa testável isoladamente.
"""
from __future__ import annotations

import pandas as pd

import config
from src import centrality, gpmf, portfolio
from src.costs import turnover


def _labels(tipos, tamanhos) -> list[str]:
    return [f"{tipo}_{tam}" for tipo in tipos for tam in tamanhos]


def backtest_rolling(retornos: pd.DataFrame,
                     formation_days: int = config.FORMATION_DAYS,
                     test_days: int = config.TEST_DAYS,
                     step_days: int = config.ROLL_STEP_DAYS,
                     tipos=config.PORTFOLIO_TYPES,
                     tamanhos=config.PORTFOLIO_SIZES,
                     medida: str = config.RANKING_MEASURE,
                     construtor=gpmf.construir_gpmf) -> dict:
    """
    Roda o backtest completo.

    Devolve um dicionário com:
      retornos  -> DataFrame (datas x carteiras) de retornos simples fora da amostra
      giros     -> DataFrame (datas de rebalance x carteiras) de turnover
      composicao-> dict {label: [(data, {ticker: peso}), ...]}
      grafos    -> lista de resumos do GPMF a cada formação
    """
    datas = retornos.index
    labels = _labels(tipos, tamanhos)

    oos = {lbl: [] for lbl in labels}
    giros = {lbl: {} for lbl in labels}
    composicao = {lbl: [] for lbl in labels}
    pesos_ant = {lbl: {} for lbl in labels}
    resumos_grafo = []

    inicio = formation_days
    while inicio + test_days <= len(datas):
        janela_form = retornos.iloc[inicio - formation_days:inicio]
        janela_teste = retornos.iloc[inicio:inicio + test_days]
        data_rebal = janela_teste.index[0]

        # formação: grafo filtrado + centralidade sobre a janela passada
        dist = gpmf.matriz_distancia(janela_form)
        G = construtor(dist)
        cent = centrality.calcular_centralidades(G)
        resumos_grafo.append({"data": data_rebal, **gpmf.resumo_grafo(G)})

        for tipo in tipos:
            for tam in tamanhos:
                lbl = f"{tipo}_{tam}"
                pesos = portfolio.selecionar_carteira(cent, tipo, tam, medida)
                giros[lbl][data_rebal] = turnover(pesos_ant[lbl], pesos)
                oos[lbl].append(portfolio.retorno_carteira(janela_teste, pesos))
                composicao[lbl].append((data_rebal, pesos))
                pesos_ant[lbl] = pesos

        inicio += step_days

    retornos_oos = pd.DataFrame({lbl: pd.concat(oos[lbl]) for lbl in labels}).sort_index()
    df_giros = pd.DataFrame(giros).sort_index()

    return {
        "retornos": retornos_oos,
        "giros": df_giros,
        "composicao": composicao,
        "grafos": pd.DataFrame(resumos_grafo).set_index("data"),
    }

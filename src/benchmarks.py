"""
Benchmarks clássicos de média-variância (Markowitz) para comparação.

Responde ao pedido de comparar as carteiras por grafo não só com o índice
passivo, mas também com a otimização clássica. Para que a comparação seja
controlada, este módulo espelha `src.rolling.backtest_rolling` linha a linha:
mesma janela de formação, mesmo passo, mesma função de giro, mesma conversão
log->simples em `portfolio.retorno_carteira`. A ÚNICA coisa que muda é a regra
que decide os pesos. Assim, qualquer diferença de desempenho vem da regra de
alocação, e não de detalhe de implementação — que é exatamente a crítica que o
artigo faz à literatura.

Regras implementadas:
    equal_weight    1/N sobre todo o universo (DeMiguel et al., 2009)
    min_var         mínima variância long-only
    min_var_shrink  mínima variância sobre o estimador de Ledoit-Wolf (2004)
    tangency        máximo Sharpe long-only (o programa de Markowitz puro)

Também aceita um "seletor" opcional, que restringe o universo da janela antes
de ponderar. É assim que se obtém a linha "seleção por rede + pesos otimizados"
da tabela: o grafo escolhe os k fundos, a otimização decide os pesos dentro
deles, isolando o efeito da ponderação sobre o da seleção.

Convenções herdadas do projeto:
  - média e covariância estimadas sobre retornos SIMPLES da janela de formação
    (Markowitz é definido sobre retorno simples; no diário a diferença para o
    log é de terceira ordem, mas não há razão para introduzi-la);
  - rf da janela = média do CDI diário no período de formação;
  - long-only (venda a descoberto de FII é cara e frequentemente inviável).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

import config
from src import centrality, gpmf, portfolio, riskfree
from src.costs import turnover

_MAXITER = 500
_FTOL = 1e-12


# --------------------------------------------------------------------------- #
# Estimador de covariância
# --------------------------------------------------------------------------- #

def ledoit_wolf(X: np.ndarray) -> np.ndarray:
    """
    Estimador de encolhimento de Ledoit-Wolf (2004) em direção à identidade
    escalada. Implementado aqui em vez de importar o scikit-learn para não
    acrescentar dependência ao `requirements.txt` fixado do projeto.

    X: matriz T x N de retornos (observações nas linhas).
    """
    T, N = X.shape
    Xc = X - X.mean(axis=0)
    S = (Xc.T @ Xc) / T                      # covariância amostral (MLE)

    mu = np.trace(S) / N
    F = mu * np.eye(N)                       # alvo: identidade escalada

    d2 = np.sum((S - F) ** 2) / N            # distância ao alvo
    # dispersão das covariâncias instantâneas em torno de S
    b2_bar = sum(np.sum((np.outer(Xc[t], Xc[t]) - S) ** 2) for t in range(T))
    b2_bar /= (T ** 2) * N
    b2 = min(b2_bar, d2)                     # limitado por d2

    delta = 0.0 if d2 <= 0 else b2 / d2      # intensidade ótima
    return delta * F + (1.0 - delta) * S


# --------------------------------------------------------------------------- #
# Regras de ponderação
# --------------------------------------------------------------------------- #

def _normaliza(w: np.ndarray, nomes: list[str]) -> dict[str, float]:
    w = np.clip(np.asarray(w, dtype=float), 0.0, None)
    s = w.sum()
    w = np.full(len(w), 1.0 / len(w)) if s <= 0 else w / s
    return dict(zip(nomes, w))


def _otimiza(objetivo, n: int) -> np.ndarray:
    """SLSQP long-only com soma 1, partindo de 1/N. Cai em 1/N se não convergir."""
    x0 = np.full(n, 1.0 / n)
    res = minimize(objetivo, x0, method="SLSQP",
                   bounds=[(0.0, 1.0)] * n,
                   constraints=({"type": "eq", "fun": lambda w: w.sum() - 1.0},),
                   options={"maxiter": _MAXITER, "ftol": _FTOL})
    return res.x if res.success else x0


def peso_equal(ret_simples: pd.DataFrame, rf: float) -> dict[str, float]:
    nomes = list(ret_simples.columns)
    return {tk: 1.0 / len(nomes) for tk in nomes}


def peso_min_var(ret_simples: pd.DataFrame, rf: float) -> dict[str, float]:
    nomes = list(ret_simples.columns)
    cov = np.cov(ret_simples.to_numpy(), rowvar=False)
    w = _otimiza(lambda w: w @ cov @ w, len(nomes))
    return _normaliza(w, nomes)


def peso_min_var_shrink(ret_simples: pd.DataFrame, rf: float) -> dict[str, float]:
    nomes = list(ret_simples.columns)
    cov = ledoit_wolf(ret_simples.to_numpy())
    w = _otimiza(lambda w: w @ cov @ w, len(nomes))
    return _normaliza(w, nomes)


def peso_tangencia(ret_simples: pd.DataFrame, rf: float) -> dict[str, float]:
    nomes = list(ret_simples.columns)
    cov = np.cov(ret_simples.to_numpy(), rowvar=False)
    excesso = ret_simples.mean().to_numpy() - rf

    def neg_sharpe(w):
        vol = np.sqrt(w @ cov @ w)
        return 0.0 if vol < 1e-12 else -(w @ excesso) / vol

    return _normaliza(_otimiza(neg_sharpe, len(nomes)), nomes)


REGRAS = {
    "equal_weight": peso_equal,
    "min_var": peso_min_var,
    "min_var_shrink": peso_min_var_shrink,
    "tangency": peso_tangencia,
}


# --------------------------------------------------------------------------- #
# Seletor por rede (para a linha "seleção por rede + pesos otimizados")
# --------------------------------------------------------------------------- #

def seletor_rede(tipo: str, tamanho: int,
                 construtor=gpmf.construir_gpmf,
                 medida: str = config.RANKING_MEASURE):
    """Devolve uma função janela_log -> lista de tickers, usando o mesmo
    caminho de seleção do braço por grafo (distância -> filtro -> centralidade)."""
    def _sel(janela_log: pd.DataFrame) -> list[str]:
        dist = gpmf.matriz_distancia(janela_log)
        G = construtor(dist)
        cent = centrality.calcular_centralidades(G)
        return list(portfolio.selecionar_carteira(cent, tipo, tamanho, medida))
    return _sel


# --------------------------------------------------------------------------- #
# Motor
# --------------------------------------------------------------------------- #

def backtest_benchmarks(retornos: pd.DataFrame,
                        regras: dict | None = None,
                        seletores: dict | None = None,
                        retornos_preco: pd.DataFrame | None = None,
                        formation_days: int = config.FORMATION_DAYS,
                        test_days: int = config.TEST_DAYS,
                        step_days: int = config.ROLL_STEP_DAYS) -> dict:
    """
    Mesmo laço de `rolling.backtest_rolling`, com regras de ponderação no lugar
    da seleção por centralidade.

    `regras`    {label: f(ret_simples_formacao, rf) -> {ticker: peso}}
    `seletores` {label: (nome_da_regra, f(janela_log) -> [tickers])}, para as
                estratégias que primeiro restringem o universo e depois ponderam.

    Devolve o mesmo formato de `backtest_rolling` (retornos, retornos_preco,
    giros, composicao), para alimentar `costs.aplicar_custos_serie` e
    `metrics.estatisticas` sem nenhuma adaptação.
    """
    regras = REGRAS if regras is None else regras
    seletores = seletores or {}
    datas = retornos.index
    rf_diaria = riskfree.serie_rf_diaria(datas)
    if retornos_preco is not None:
        retornos_preco = retornos_preco.reindex(datas)

    labels = list(regras) + list(seletores)
    oos = {l: [] for l in labels}
    oos_preco = {l: [] for l in labels}
    giros = {l: {} for l in labels}
    composicao = {l: [] for l in labels}
    pesos_ant = {l: {} for l in labels}

    inicio = formation_days
    while inicio + test_days <= len(datas):
        janela_form = retornos.iloc[inicio - formation_days:inicio]
        janela_teste = retornos.iloc[inicio:inicio + test_days]
        janela_teste_preco = (retornos_preco.iloc[inicio:inicio + test_days]
                              if retornos_preco is not None else None)
        data_rebal = janela_teste.index[0]

        # retornos simples da janela de formação + rf média do período
        form_simples = (np.expm1(janela_form) if config.RETURN_TYPE == "log"
                        else janela_form)
        form_simples = form_simples.dropna(axis=1, how="any")
        rf_janela = float(rf_diaria.loc[janela_form.index].mean())

        planos = [(l, f, None) for l, f in regras.items()]
        planos += [(l, regras[nome] if isinstance(nome, str) else nome, sel)
                   for l, (nome, sel) in seletores.items()]

        for lbl, ponderador, seletor in planos:
            sub = form_simples
            if seletor is not None:
                escolhidos = [t for t in seletor(janela_form) if t in sub.columns]
                if not escolhidos:
                    continue
                sub = sub[escolhidos]

            pesos = ponderador(sub, rf_janela)
            giros[lbl][data_rebal] = turnover(pesos_ant[lbl], pesos)
            oos[lbl].append(portfolio.retorno_carteira(janela_teste, pesos))
            if janela_teste_preco is not None:
                oos_preco[lbl].append(
                    portfolio.retorno_carteira(janela_teste_preco, pesos))
            composicao[lbl].append((data_rebal, pesos))
            pesos_ant[lbl] = pesos

        inicio += step_days

    def _montar(d):
        return pd.DataFrame({l: pd.concat(v) for l, v in d.items() if v}).sort_index()

    return {
        "retornos": _montar(oos),
        "retornos_preco": _montar(oos_preco) if retornos_preco is not None else None,
        "giros": pd.DataFrame(giros).sort_index(),
        "composicao": composicao,
    }

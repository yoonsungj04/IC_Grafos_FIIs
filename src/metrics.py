"""
Métricas de desempenho/risco e testes de significância.

Inclui retorno e volatilidade anualizados, índice de Sharpe, drawdown máximo e
o teste de Jobson-Korkie (com correção de Memmel) para diferença de Sharpe
entre duas carteiras.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config


# Todas as funções abaixo assumem retornos SIMPLES diários.


def curva_acumulada(retornos: pd.Series) -> pd.Series:
    return (1.0 + retornos).cumprod()


def drawdown_maximo(retornos: pd.Series) -> float:
    curva = curva_acumulada(retornos)
    pico = curva.cummax()
    return float((curva / pico - 1.0).min())


def estatisticas(retornos: pd.Series,
                 rf_anual: float = config.RISK_FREE_ANNUAL,
                 periodos: int = config.TRADING_DAYS_PER_YEAR) -> dict:
    """Resumo de uma série de retornos simples diários."""
    r = retornos.dropna()
    ret_anual = (1.0 + r).prod() ** (periodos / len(r)) - 1.0
    vol_anual = r.std(ddof=1) * np.sqrt(periodos)
    rf_diario = (1.0 + rf_anual) ** (1.0 / periodos) - 1.0
    excesso = r - rf_diario
    sharpe = (excesso.mean() / excesso.std(ddof=1) * np.sqrt(periodos)
              if excesso.std(ddof=1) > 0 else np.nan)
    return {
        "retorno_anual": float(ret_anual),
        "vol_anual": float(vol_anual),
        "sharpe": float(sharpe),
        "drawdown_max": drawdown_maximo(r),
        "retorno_acumulado": float((1.0 + r).prod() - 1.0),
        "n_periodos": int(len(r)),
    }


def jobson_korkie(ret_a: pd.Series, ret_b: pd.Series) -> dict:
    """
    Testa H0: Sharpe(A) = Sharpe(B) com a estatística de Jobson-Korkie corrigida
    por Memmel (2003). Retorna a diferença, a estatística z e o p-valor.
    """
    from scipy import stats

    df = pd.concat([ret_a, ret_b], axis=1).dropna()
    df.columns = ["a", "b"]
    n = len(df)
    if n < 30:
        return {"diff_sharpe": np.nan, "z": np.nan, "p_valor": np.nan, "n": n}

    sh_a = df["a"].mean() / df["a"].std(ddof=1)
    sh_b = df["b"].mean() / df["b"].std(ddof=1)
    rho = df["a"].corr(df["b"])

    # variância assintótica da diferença de Sharpe (Jobson-Korkie com correção
    # de Memmel, 2003). Sharpe por período (não anualizado) — a anualização
    # cancela na razão.
    theta = (2 * (1 - rho) + 0.5 * (sh_a ** 2 + sh_b ** 2 - 2 * sh_a * sh_b * rho ** 2)) / n
    z = (sh_a - sh_b) / np.sqrt(theta)
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return {"diff_sharpe": float(sh_a - sh_b), "z": float(z), "p_valor": float(p), "n": n}

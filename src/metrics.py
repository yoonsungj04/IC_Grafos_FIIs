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


def _excesso(retornos: pd.Series, rf_diaria: pd.Series | None,
             rf_anual: float, periodos: int) -> pd.Series:
    """Retorno excedente sobre a rf. Série diária da rf tem prioridade; na
    ausência dela, usa a constante anual convertida para taxa por pregão."""
    r = retornos.dropna()
    if rf_diaria is not None:
        return r - rf_diaria.reindex(r.index).ffill().bfill()
    rf_d = (1.0 + rf_anual) ** (1.0 / periodos) - 1.0
    return r - rf_d


def estatisticas(retornos: pd.Series,
                 rf_diaria: pd.Series | None = None,
                 rf_anual: float = config.RISK_FREE_ANNUAL,
                 periodos: int = config.TRADING_DAYS_PER_YEAR) -> dict:
    """
    Resumo de uma série de retornos simples diários. O Sharpe é calculado sobre o
    retorno EXCEDENTE em relação à rf (CDI diário, se `rf_diaria` for passada);
    retorno e volatilidade anualizados permanecem sobre o retorno bruto da carteira.
    """
    r = retornos.dropna()
    ret_anual = (1.0 + r).prod() ** (periodos / len(r)) - 1.0
    vol_anual = r.std(ddof=1) * np.sqrt(periodos)
    excesso = _excesso(r, rf_diaria, rf_anual, periodos)
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


def jobson_korkie(ret_a: pd.Series, ret_b: pd.Series,
                  rf_diaria: pd.Series | None = None) -> dict:
    """
    Testa H0: Sharpe(A) = Sharpe(B) com a estatística de Jobson-Korkie corrigida
    por Memmel (2003). Retorna a diferença, a estatística z e o p-valor. Quando
    `rf_diaria` é passada, o teste usa os retornos EXCEDENTES sobre o CDI.
    """
    from scipy import stats

    df = pd.concat([ret_a, ret_b], axis=1).dropna()
    df.columns = ["a", "b"]
    if rf_diaria is not None:
        rf = rf_diaria.reindex(df.index).ffill().bfill()
        df["a"] = df["a"] - rf
        df["b"] = df["b"] - rf
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


def _sharpe_anual(r: np.ndarray, periodos: int) -> float:
    s = r.std(ddof=1)
    return r.mean() / s * np.sqrt(periodos) if s > 0 else np.nan


def bootstrap_diff_sharpe(ret_a: pd.Series, ret_b: pd.Series,
                          rf_diaria: pd.Series | None = None,
                          n_boot: int = config.N_BOOTSTRAP,
                          bloco: int = config.TEST_DAYS,
                          periodos: int = config.TRADING_DAYS_PER_YEAR,
                          seed: int = config.RANDOM_SEED) -> dict:
    """
    Intervalo de confiança (95%) da diferença de Sharpe ANUALIZADO (A - B) por
    bootstrap de blocos circulares. Os blocos (tamanho `bloco`, ~uma janela de
    manutenção) preservam a autocorrelação diária e a estrutura de pares A/B, o
    que o erro padrão assintótico de Jobson-Korkie ignora. Devolve a diferença
    pontual, o IC 95% e o p-valor bootstrap (proporção que cruza zero).
    """
    df = pd.concat([ret_a, ret_b], axis=1).dropna()
    df.columns = ["a", "b"]
    if rf_diaria is not None:
        rf = rf_diaria.reindex(df.index).ffill().bfill()
        df["a"] = df["a"] - rf
        df["b"] = df["b"] - rf
    a = df["a"].to_numpy()
    b = df["b"].to_numpy()
    n = len(a)
    if n < 30:
        return {"diff": np.nan, "ic_baixo": np.nan, "ic_alto": np.nan, "p_boot": np.nan, "n": n}

    diff_obs = _sharpe_anual(a, periodos) - _sharpe_anual(b, periodos)

    rng = np.random.default_rng(seed)
    n_blocos = int(np.ceil(n / bloco))
    diffs = np.empty(n_boot)
    for i in range(n_boot):
        inicios = rng.integers(0, n, size=n_blocos)
        idx = (inicios[:, None] + np.arange(bloco)[None, :]).ravel()[:n] % n
        diffs[i] = _sharpe_anual(a[idx], periodos) - _sharpe_anual(b[idx], periodos)

    ic_b, ic_a = np.percentile(diffs, [2.5, 97.5])
    # p-valor bidirecional: dobro da menor cauda em torno de zero
    p_boot = 2 * min((diffs <= 0).mean(), (diffs >= 0).mean())
    return {"diff": float(diff_obs), "ic_baixo": float(ic_b), "ic_alto": float(ic_a),
            "p_boot": float(min(p_boot, 1.0)), "n": n}

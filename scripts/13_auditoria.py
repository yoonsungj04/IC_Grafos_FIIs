"""
Auditoria: confere afirmações do artigo contra o código.

Não gera resultado novo do artigo; só verifica números citados no texto que
não saem diretamente de uma tabela já gravada.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import benchmarks, costs, gpmf, metrics, pipeline, riskfree, rolling


def main() -> None:
    d = pipeline.preparar_dados()
    ret_log, ret_preco = d["retornos_log"], d["retornos_log_preco"]

    oos_ref = pd.read_csv(config.PROCESSED_DIR / "retornos_oos.csv",
                          index_col=0, parse_dates=True)
    rf = riskfree.serie_rf_diaria(oos_ref.index)

    # ---- MST: bruto vs líquido, giro por k, e teste de Pozzi ---------------
    r = rolling.backtest_rolling(ret_log, construtor=gpmf.construir_mst,
                                 retornos_preco=ret_preco)
    oos, giros, preco = r["retornos"], r["giros"], r["retornos_preco"]
    liq = pd.DataFrame({l: costs.aplicar_custos_serie(oos[l], giros[l],
                                                      retornos_preco=preco[l])
                        for l in oos.columns})
    print("MST  carteira        sharpe_bruto  sharpe_liq   giro")
    for l in oos.columns:
        sb = metrics.estatisticas(oos[l], rf_diaria=rf)["sharpe"]
        sl = metrics.estatisticas(liq[l], rf_diaria=rf)["sharpe"]
        print(f"     {l:<16}{sb:12.3f}{sl:12.3f}{giros[l].mean():8.3f}")

    bs = metrics.bootstrap_diff_sharpe(liq["peripheral_10"], liq["central_10"], rf_diaria=rf)
    jk = metrics.jobson_korkie(liq["peripheral_10"], liq["central_10"], rf_diaria=rf)
    print(f"\nMST Perif-10 - Central-10 (liq): d={bs['diff']:+.2f} "
          f"IC=[{bs['ic_baixo']:+.2f},{bs['ic_alto']:+.2f}] "
          f"p_boot={bs['p_boot']:.2f} p_JK={jk['p_valor']:.2f}")

    # ---- giro do 1o rebalanceamento (convenção) ----------------------------
    print(f"\ngiro no 1o rebalance (GPMF central_10): "
          f"{rolling.backtest_rolling(ret_log, retornos_preco=ret_preco)['giros']['central_10'].iloc[0]:.2f}")

    # ---- tangência: quantas janelas têm TODO excesso esperado negativo? ----
    datas = ret_log.index
    rf_all = riskfree.serie_rf_diaria(datas)
    n_jan = n_todos_neg = 0
    frac_neg = []
    inicio = config.FORMATION_DAYS
    while inicio + config.TEST_DAYS <= len(datas):
        jf = np.expm1(ret_log.iloc[inicio - config.FORMATION_DAYS:inicio]).dropna(axis=1)
        exc = jf.mean() - rf_all.loc[jf.index].mean()
        n_jan += 1
        frac_neg.append((exc < 0).mean())
        n_todos_neg += int((exc < 0).all())
        inicio += config.ROLL_STEP_DAYS
    print(f"\ntangência: janelas com excesso esperado negativo em TODOS os fundos: "
          f"{n_todos_neg}/{n_jan}; fração média de fundos com excesso<0: "
          f"{np.mean(frac_neg):.2f}")

    # ---- universo dos benchmarks após dropna ------------------------------
    print(f"universo nos benchmarks (fundos por janela após dropna): "
          f"{jf.shape[1]} (de {ret_log.shape[1]})")

    # ---- CDI médio ----------------------------------------------------------
    print(f"CDI médio: janela total {rf_all.mean()*252*100:.1f}% a.a. | "
          f"fora da amostra {rf.mean()*252*100:.1f}% a.a.")

    # ---- buracos preenchidos: maior sequência de NaN antes do ffill --------
    precos = pd.read_csv(config.RAW_DIR / "precos_ajustados.csv",
                         index_col=0, parse_dates=True)[d["universo"]]
    precos = precos.loc[precos.dropna(how="all").index]
    maior = 0
    for c in precos.columns:
        s = precos[c].loc[precos[c].first_valid_index():]
        runs = s.isna().astype(int).groupby(s.notna().cumsum()).sum()
        maior = max(maior, int(runs.max()))
    print(f"maior sequência de pregões faltantes preenchida por ffill: {maior}")


if __name__ == "__main__":
    main()

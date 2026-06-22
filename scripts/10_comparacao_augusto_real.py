"""
Comparação com os resultados REAIS do braço AGM (Augusto).

O Augusto enviou as séries diárias fora da amostra da AGM já alinhadas
(mesmo benchmark, retorno corrigido, Sharpe sobre o CDI). Porém o backtest dele
termina em fev/2025, enquanto o nosso vai até out/2025. Para comparar de forma
justa, restringimos os DOIS braços ao período comum (a janela mais curta dele) e
recomputamos tudo com a mesma métrica (Sharpe sobre o excesso ao CDI).

Faz também uma validação cruzada: a nossa AGM (mesmo método) deve bater com a AGM
do Augusto no período comum — se bater, a integração está correta.

Entradas: ~/Downloads/retornos_diarios_agm_eniac.csv (Augusto).
Saídas: results/tables/comparacao_augusto_real.csv e figura.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import costs, gpmf, metrics, pipeline, riskfree, rolling

AUGUSTO_CSV = Path.home() / "Downloads" / "retornos_diarios_agm_eniac.csv"
MEDIDA = "composite"          # mesma regra de seleção dos dois lados
TAMANHOS = (5, 10)


def _series_liquidas(ret_log, construtor):
    """Roda o backtest e devolve as séries LÍQUIDAS (simples) por carteira."""
    res = rolling.backtest_rolling(ret_log, tamanhos=TAMANHOS, medida=MEDIDA,
                                   construtor=construtor)
    oos, giros = res["retornos"], res["giros"]
    return {lbl: costs.aplicar_custos_serie(oos[lbl], giros[lbl]) for lbl in oos.columns}


def main():
    # --- séries do Augusto (log -> simples) ---
    ag = pd.read_csv(AUGUSTO_CSV, index_col=0, parse_dates=True)
    ag_simples = np.expm1(ag)               # estavam em log
    ini, fim = ag.index[0], ag.index[-1]
    print(f"período comum (do Augusto): {ini.date()} a {fim.date()} ({len(ag)} pregões)\n")

    # --- nossas séries (GPMF e AGM), restritas ao período comum ---
    dados = pipeline.preparar_dados()
    gpmf_liq = _series_liquidas(dados["retornos_log"], gpmf.construir_gpmf)
    agm_liq = _series_liquidas(dados["retornos_log"], gpmf.construir_mst)

    def corta(s):
        return s.loc[ini:fim]

    rf = riskfree.serie_rf_diaria(ag.index).loc[ini:fim]

    # --- validação cruzada: nossa AGM vs AGM do Augusto (mesmo período) ---
    print("=== validação: nossa AGM vs AGM do Augusto (período comum) ===")
    mapa = {"AGM_Central_5": "central_5", "AGM_Central_10": "central_10",
            "AGM_Periferica_5": "peripheral_5"}
    for col_ag, lbl in mapa.items():
        nossa = corta(agm_liq[lbl])
        dele = corta(ag_simples[col_ag])
        sh_n = metrics.estatisticas(nossa, rf_diaria=rf)["sharpe"]
        sh_d = metrics.estatisticas(dele, rf_diaria=rf)["sharpe"]
        ret_n = metrics.estatisticas(nossa, rf_diaria=rf)["retorno_anual"]
        ret_d = metrics.estatisticas(dele, rf_diaria=rf)["retorno_anual"]
        print(f"{lbl:14s}: nossa AGM ret={ret_n*100:6.2f}% sh={sh_n:+.2f} | "
              f"Augusto ret={ret_d*100:6.2f}% sh={sh_d:+.2f}")

    # --- comparação oficial: GPMF (nosso) vs AGM (Augusto), período comum ---
    print("\n=== comparação GPMF (Yoon) vs AGM (Augusto) — período comum, líquido ===")
    bench = corta(ag_simples["Benchmark_IFIX"])
    linhas = []
    for col_ag, lbl in mapa.items():
        g = corta(gpmf_liq[lbl])
        a = corta(ag_simples[col_ag])
        eg = metrics.estatisticas(g, rf_diaria=rf)
        ea = metrics.estatisticas(a, rf_diaria=rf)
        linhas.append({"carteira": lbl,
                       "GPMF_ret_aa": round(eg["retorno_anual"], 4),
                       "GPMF_sharpe": round(eg["sharpe"], 3),
                       "AGM_ret_aa": round(ea["retorno_anual"], 4),
                       "AGM_sharpe": round(ea["sharpe"], 3)})
    eb = metrics.estatisticas(bench, rf_diaria=rf)
    tab = pd.DataFrame(linhas).set_index("carteira")
    print(tab.to_string())
    print(f"\nbenchmark (período comum): ret={eb['retorno_anual']*100:.2f}%  "
          f"sharpe={eb['sharpe']:.3f}")
    tab.to_csv(config.TABLES_DIR / "comparacao_augusto_real.csv")

    # teste de significância GPMF vs AGM (Periférica-5 e Central-10)
    print("\n=== Jobson-Korkie + bootstrap (GPMF vs AGM, período comum) ===")
    for col_ag, lbl in [("AGM_Periferica_5", "peripheral_5"), ("AGM_Central_10", "central_10")]:
        g, a = corta(gpmf_liq[lbl]), corta(ag_simples[col_ag])
        bt = metrics.bootstrap_diff_sharpe(g, a, rf_diaria=rf)
        print(f"GPMF {lbl} vs AGM: ΔSharpe(aa)={bt['diff']:+.2f} "
              f"IC95=[{bt['ic_baixo']:+.2f}, {bt['ic_alto']:+.2f}] p_boot={bt['p_boot']:.3f}")

    _figura(gpmf_liq, ag_simples, bench, ini, fim)


def _figura(gpmf_liq, ag_simples, bench, ini, fim):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from src.metrics import curva_acumulada

        idx = bench.index
        fig, ax = plt.subplots(figsize=(11, 6))
        ax.plot(idx, curva_acumulada(gpmf_liq["peripheral_5"].loc[ini:fim]),
                color="C2", label="GPMF Periférica-5 (Yoon)")
        ax.plot(idx, curva_acumulada(ag_simples["AGM_Periferica_5"].loc[ini:fim]),
                color="C2", ls="--", label="AGM Periférica-5 (Augusto)")
        ax.plot(idx, curva_acumulada(gpmf_liq["central_10"].loc[ini:fim]),
                color="C3", label="GPMF Central-10 (Yoon)")
        ax.plot(idx, curva_acumulada(ag_simples["AGM_Central_10"].loc[ini:fim]),
                color="C3", ls="--", label="AGM Central-10 (Augusto)")
        ax.plot(idx, curva_acumulada(bench), color="k", ls=":", label="benchmark")
        ax.set_title("GPMF (Yoon) vs AGM (Augusto) — período comum, líquido, fora da amostra")
        ax.set_ylabel("crescimento de R$ 1")
        ax.legend(fontsize=8)
        fig.tight_layout()
        caminho = config.FIGURES_DIR / "comparacao_augusto_real.png"
        fig.savefig(caminho, dpi=130)
        print(f"\nfigura salva em {caminho}")
    except Exception as e:
        print(f"(figura ignorada: {e})")


if __name__ == "__main__":
    main()

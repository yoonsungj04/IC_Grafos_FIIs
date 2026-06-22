"""
Comparação GPMF vs MST/AGM (Fase D).

Roda o mesmo backtest rolante com os dois filtros — GPMF (planar, 3N-6 arestas)
e MST/AGM (árvore, N-1 arestas) — sobre exatamente o mesmo universo e janela,
aplicando custos e tributos. Gera a tabela e a figura comparativas. Os números
do braço MST podem depois ser substituídos pelos do trabalho do parceiro; aqui
servem de referência sob metodologia idêntica.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import costs, gpmf, metrics, pipeline, riskfree, rolling


def _backtest_liquido(ret_log, construtor):
    res = rolling.backtest_rolling(ret_log, construtor=construtor)
    oos, giros = res["retornos"], res["giros"]
    liq = {lbl: costs.aplicar_custos_serie(oos[lbl], giros[lbl]) for lbl in oos.columns}
    return oos, pd.DataFrame(liq), res["grafos"]


def main() -> None:
    dados = pipeline.preparar_dados()
    ret_log = dados["retornos_log"]

    rf = riskfree.serie_rf_diaria(ret_log.index)
    filtros = {"GPMF": gpmf.construir_gpmf, "MST": gpmf.construir_mst}
    linhas = []
    curvas = {}
    for nome, construtor in filtros.items():
        oos, liq, grafos = _backtest_liquido(ret_log, construtor)
        print(f"{nome}: arestas médias {grafos['arestas'].mean():.0f} "
              f"(limite/N: {grafos['limite_3n_6'].iloc[0]})")
        for tipo in config.PORTFOLIO_TYPES:
            lbl = f"{tipo}_10"
            est = metrics.estatisticas(liq[lbl], rf_diaria=rf)
            linhas.append({"filtro": nome, "carteira": tipo,
                           "sharpe_liq": round(est["sharpe"], 4),
                           "ret_liq": round(est["retorno_acumulado"], 4),
                           "dd": round(est["drawdown_max"], 4)})
            curvas[f"{nome}-{tipo}"] = liq[lbl]

    bench = pd.read_csv(config.PROCESSED_DIR / "benchmark_oos.csv",
                        index_col=0, parse_dates=True).iloc[:, 0]
    est_b = metrics.estatisticas(bench.reindex(list(curvas.values())[0].index).dropna(),
                                 rf_diaria=rf)
    linhas.append({"filtro": "benchmark", "carteira": "-",
                   "sharpe_liq": round(est_b["sharpe"], 4),
                   "ret_liq": round(est_b["retorno_acumulado"], 4),
                   "dd": round(est_b["drawdown_max"], 4)})

    tabela = pd.DataFrame(linhas)
    print("\n" + tabela.to_string(index=False))
    tabela.to_csv(config.TABLES_DIR / "tabela_comparacao_gpmf_mst.csv", index=False)

    _significancia_pozzi(curvas, rf)
    _figura(curvas, bench)


def _significancia_pozzi(curvas, rf) -> None:
    """
    Testa, para CADA filtro, se a diferença de Sharpe Periférica-10 menos
    Central-10 (a inversão de Pozzi) é estatisticamente significativa, com
    Jobson-Korkie (Memmel) e bootstrap de blocos. Responde diretamente à dúvida
    do revisor: a inversão da MST em N=10 é real ou é ruído amostral?
    """
    print("\n--- significância da inversão de Pozzi (Periférica-10 - Central-10), por filtro ---")
    linhas = []
    for nome in ("GPMF", "MST"):
        peri = curvas[f"{nome}-peripheral"]
        cent = curvas[f"{nome}-central"]
        jk = metrics.jobson_korkie(peri, cent, rf_diaria=rf)
        bs = metrics.bootstrap_diff_sharpe(peri, cent, rf_diaria=rf)
        cruza_zero = bs["ic_baixo"] <= 0 <= bs["ic_alto"]
        print(f"{nome}: ΔSharpe(aa)={bs['diff']:+.2f}  "
              f"IC95=[{bs['ic_baixo']:+.2f}, {bs['ic_alto']:+.2f}]  "
              f"p_boot={bs['p_boot']:.3f}  p_JK={jk['p_valor']:.3f}  "
              f"signif.={'não' if cruza_zero else 'sim'}")
        linhas.append({"filtro": nome, "diff_sharpe": jk["diff_sharpe"], "z": jk["z"],
                       "p_valor": jk["p_valor"], "diff_sharpe_aa": bs["diff"],
                       "ic95_baixo": bs["ic_baixo"], "ic95_alto": bs["ic_alto"],
                       "p_boot": bs["p_boot"], "n": jk["n"]})
    pd.DataFrame(linhas).round(4).to_csv(
        config.TABLES_DIR / "pozzi_significancia.csv", index=False)


def _figura(curvas, bench) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from src.metrics import curva_acumulada
        from src import plotting
        plotting.aplicar_estilo_pb()

        idx = list(curvas.values())[0].index
        fig, ax = plt.subplots(figsize=(11, 6))
        # Em P&B: o FILTRO é distinguido pelo traço (GPMF sólido, MST tracejado)
        # e o TIPO de carteira pelo tom de cinza + marcador.
        estilos = {"GPMF": "-", "MST": "--"}
        cinza = {"central": "0.0", "peripheral": "0.45", "hybrid": "0.65"}
        marca = {"central": "o", "peripheral": "s", "hybrid": "^"}
        for chave, serie in curvas.items():
            nome, tipo = chave.split("-")
            ax.plot(serie.index, curva_acumulada(serie), label=chave,
                    color=cinza[tipo], linestyle=estilos[nome], linewidth=1.6,
                    marker=marca[tipo], markevery=0.12, markersize=4)
        ax.plot(idx, curva_acumulada(bench.reindex(idx).dropna()),
                color="0.0", ls=":", linewidth=1.4, label="benchmark")
        ax.set_title("GPMF vs MST — carteiras (tam. 10), líquido, fora da amostra")
        ax.set_ylabel("crescimento de R$ 1")
        ax.legend(ncol=2, fontsize=8)
        caminho = config.FIGURES_DIR / "comparacao_gpmf_mst.png"
        plotting.salvar_pb(fig, caminho)
        print(f"\nfigura comparativa em {caminho}")
    except Exception as e:
        print(f"(figura ignorada: {e})")


if __name__ == "__main__":
    main()

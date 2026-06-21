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
from src import costs, gpmf, metrics, pipeline, rolling


def _backtest_liquido(ret_log, construtor):
    res = rolling.backtest_rolling(ret_log, construtor=construtor)
    oos, giros = res["retornos"], res["giros"]
    liq = {lbl: costs.aplicar_custos_serie(oos[lbl], giros[lbl]) for lbl in oos.columns}
    return oos, pd.DataFrame(liq), res["grafos"]


def main() -> None:
    dados = pipeline.preparar_dados()
    ret_log = dados["retornos_log"]

    filtros = {"GPMF": gpmf.construir_gpmf, "MST": gpmf.construir_mst}
    linhas = []
    curvas = {}
    for nome, construtor in filtros.items():
        oos, liq, grafos = _backtest_liquido(ret_log, construtor)
        print(f"{nome}: arestas médias {grafos['arestas'].mean():.0f} "
              f"(limite/N: {grafos['limite_3n_6'].iloc[0]})")
        for tipo in config.PORTFOLIO_TYPES:
            lbl = f"{tipo}_10"
            est = metrics.estatisticas(liq[lbl])
            linhas.append({"filtro": nome, "carteira": tipo,
                           "sharpe_liq": round(est["sharpe"], 4),
                           "ret_liq": round(est["retorno_acumulado"], 4),
                           "dd": round(est["drawdown_max"], 4)})
            curvas[f"{nome}-{tipo}"] = liq[lbl]

    bench = pd.read_csv(config.PROCESSED_DIR / "benchmark_oos.csv",
                        index_col=0, parse_dates=True).iloc[:, 0]
    est_b = metrics.estatisticas(bench.reindex(list(curvas.values())[0].index).dropna())
    linhas.append({"filtro": "benchmark", "carteira": "-",
                   "sharpe_liq": round(est_b["sharpe"], 4),
                   "ret_liq": round(est_b["retorno_acumulado"], 4),
                   "dd": round(est_b["drawdown_max"], 4)})

    tabela = pd.DataFrame(linhas)
    print("\n" + tabela.to_string(index=False))
    tabela.to_csv(config.TABLES_DIR / "tabela_comparacao_gpmf_mst.csv", index=False)

    _figura(curvas, bench)


def _figura(curvas, bench) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from src.metrics import curva_acumulada

        idx = list(curvas.values())[0].index
        fig, ax = plt.subplots(figsize=(11, 6))
        estilos = {"GPMF": "-", "MST": "--"}
        cores = {"central": "C0", "peripheral": "C1", "hybrid": "C2"}
        for chave, serie in curvas.items():
            nome, tipo = chave.split("-")
            ax.plot(serie.index, curva_acumulada(serie), estilos[nome],
                    color=cores[tipo], label=chave)
        ax.plot(idx, curva_acumulada(bench.reindex(idx).dropna()),
                color="k", ls=":", label="benchmark")
        ax.set_title("GPMF vs MST — carteiras (tam. 10), líquido, fora da amostra")
        ax.set_ylabel("crescimento de R$ 1")
        ax.legend(ncol=2, fontsize=8)
        fig.tight_layout()
        caminho = config.FIGURES_DIR / "comparacao_gpmf_mst.png"
        fig.savefig(caminho, dpi=130)
        print(f"\nfigura comparativa em {caminho}")
    except Exception as e:
        print(f"(figura ignorada: {e})")


if __name__ == "__main__":
    main()

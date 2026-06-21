"""
Custos, tributos e testes de significância (Fase C).

Aplica custo de transação (0,3% sobre o giro) e imposto de ganho de capital
(15%) sobre as carteiras fora da amostra, compara bruto vs líquido e roda o
teste de Jobson-Korkie para a diferença de Sharpe entre as carteiras e o
benchmark.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import costs, metrics


def main() -> None:
    oos = pd.read_csv(config.PROCESSED_DIR / "retornos_oos.csv", index_col=0, parse_dates=True)
    giros = pd.read_csv(config.PROCESSED_DIR / "giros.csv", index_col=0, parse_dates=True)
    bench_path = config.PROCESSED_DIR / "benchmark_oos.csv"
    bench = (pd.read_csv(bench_path, index_col=0, parse_dates=True).iloc[:, 0]
             if bench_path.exists() else None)

    # --- bruto vs líquido ---
    linhas = []
    liquidos = {}
    for lbl in oos.columns:
        liq = costs.aplicar_custos_serie(oos[lbl], giros[lbl])
        liquidos[lbl] = liq
        eb = metrics.estatisticas(oos[lbl])
        el = metrics.estatisticas(liq)
        linhas.append({
            "carteira": lbl,
            "giro_medio": float(giros[lbl].mean()),
            "sharpe_bruto": eb["sharpe"], "ret_bruto": eb["retorno_acumulado"],
            "sharpe_liq": el["sharpe"], "ret_liq": el["retorno_acumulado"],
            "dd_liq": el["drawdown_max"],
        })
    tabela = pd.DataFrame(linhas).set_index("carteira").round(4)
    print(tabela.to_string())
    tabela.to_csv(config.TABLES_DIR / "tabela_custos.csv")
    pd.DataFrame(liquidos).to_csv(config.PROCESSED_DIR / "retornos_oos_liquidos.csv")

    # --- testes de significância (Jobson-Korkie) sobre o líquido ---
    print("\n--- testes de Jobson-Korkie (diferença de Sharpe, líquido) ---")
    pares = [("peripheral_10", "central_10"), ("hybrid_10", "central_10")]
    if bench is not None:
        bench_liq = bench.reindex(oos.index).dropna()
        for lbl in ("central_10", "peripheral_10", "hybrid_10"):
            pares.append((lbl, "benchmark"))
        liquidos["benchmark"] = bench_liq

    res_testes = []
    for a, b in pares:
        jk = metrics.jobson_korkie(liquidos[a], liquidos[b])
        sig = "sim" if (jk["p_valor"] is not None and jk["p_valor"] < 0.05) else "não"
        print(f"{a:>14} vs {b:<12}: ΔSharpe={jk['diff_sharpe']:+.3f}  "
              f"z={jk['z']:+.2f}  p={jk['p_valor']:.3f}  signif.(5%)={sig}")
        res_testes.append({"a": a, "b": b, **jk})
    pd.DataFrame(res_testes).to_csv(config.TABLES_DIR / "testes_significancia.csv", index=False)

    _figura_liquido(oos, liquidos, bench)


def _figura_liquido(oos, liquidos, bench) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from src.metrics import curva_acumulada

        fig, ax = plt.subplots(figsize=(10, 6))
        for lbl in ("central_10", "peripheral_10", "hybrid_10"):
            ax.plot(oos.index, curva_acumulada(liquidos[lbl]), label=f"{lbl} (líq.)")
        if bench is not None:
            b = bench.reindex(oos.index).dropna()
            ax.plot(b.index, curva_acumulada(b), label="benchmark", color="k", ls="--")
        ax.set_title("Retorno acumulado fora da amostra (líquido de custos e IR)")
        ax.set_ylabel("crescimento de R$ 1")
        ax.legend()
        fig.tight_layout()
        caminho = config.FIGURES_DIR / "curvas_oos_liquido.png"
        fig.savefig(caminho, dpi=130)
        print(f"\nfigura líquida em {caminho}")
    except Exception as e:
        print(f"(figura ignorada: {e})")


if __name__ == "__main__":
    main()

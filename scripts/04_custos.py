"""
Custos, tributos e testes de significância (Fase C).

Aplica custo de transação (0,3% sobre o giro) e imposto de ganho de capital
(20%) sobre as carteiras fora da amostra, compara bruto vs líquido e roda o
teste de Jobson-Korkie para a diferença de Sharpe entre as carteiras e o
benchmark.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import costs, metrics, riskfree


def main() -> None:
    oos = pd.read_csv(config.PROCESSED_DIR / "retornos_oos.csv", index_col=0, parse_dates=True)
    oos_preco = pd.read_csv(config.PROCESSED_DIR / "retornos_oos_preco.csv",
                            index_col=0, parse_dates=True)
    giros = pd.read_csv(config.PROCESSED_DIR / "giros.csv", index_col=0, parse_dates=True)
    bench_path = config.PROCESSED_DIR / "benchmark_oos.csv"
    bench = (pd.read_csv(bench_path, index_col=0, parse_dates=True).iloc[:, 0]
             if bench_path.exists() else None)

    rf = riskfree.serie_rf_diaria(oos.index)
    print(f"rf: {config.RISK_FREE_SOURCE} (média {rf.mean()*config.TRADING_DAYS_PER_YEAR*100:.1f}% a.a.)\n")

    # --- bruto vs líquido ---
    linhas = []
    liquidos = {}
    for lbl in oos.columns:
        liq = costs.aplicar_custos_serie(oos[lbl], giros[lbl], retornos_preco=oos_preco[lbl])
        liquidos[lbl] = liq
        eb = metrics.estatisticas(oos[lbl], rf_diaria=rf)
        el = metrics.estatisticas(liq, rf_diaria=rf)
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

    _decompor_custos(oos, oos_preco, giros, rf)

    # --- testes de significância sobre o líquido: Jobson-Korkie + bootstrap ---
    print("\n--- diferença de Sharpe líquido (Jobson-Korkie + IC bootstrap 95%) ---")
    pares = [("peripheral_10", "central_10"), ("hybrid_10", "central_10")]
    if bench is not None:
        bench_liq = bench.reindex(oos.index).dropna()
        for lbl in ("central_10", "peripheral_10", "hybrid_10"):
            pares.append((lbl, "benchmark"))
        liquidos["benchmark"] = bench_liq

    res_testes = []
    for a, b in pares:
        jk = metrics.jobson_korkie(liquidos[a], liquidos[b], rf_diaria=rf)
        bs = metrics.bootstrap_diff_sharpe(liquidos[a], liquidos[b], rf_diaria=rf)
        cruza_zero = bs["ic_baixo"] <= 0 <= bs["ic_alto"]
        sig = "não" if cruza_zero else "sim"
        print(f"{a:>14} vs {b:<12}: ΔSharpe(aa)={bs['diff']:+.2f}  "
              f"IC95=[{bs['ic_baixo']:+.2f}, {bs['ic_alto']:+.2f}]  "
              f"p_boot={bs['p_boot']:.3f}  p_JK={jk['p_valor']:.3f}  signif.={sig}")
        res_testes.append({"a": a, "b": b, "diff_sharpe": jk["diff_sharpe"],
                           "z": jk["z"], "p_valor": jk["p_valor"],
                           "diff_sharpe_aa": bs["diff"], "ic95_baixo": bs["ic_baixo"],
                           "ic95_alto": bs["ic_alto"], "p_boot": bs["p_boot"], "n": jk["n"]})
    pd.DataFrame(res_testes).round(4).to_csv(
        config.TABLES_DIR / "testes_significancia.csv", index=False)

    _figura_liquido(oos, liquidos, bench)


def _decompor_custos(oos, oos_preco, giros, rf) -> None:
    """
    Decompõe o arrasto de desempenho em custo de transação e imposto, isolando
    cada parcela. Reporta giro e custo médios por rebalanceamento (~mensal),
    como na versão Colab, e o arrasto anualizado de cada componente.
    """
    print("\n--- decomposição de custos (bruto -> custo -> imposto) ---")
    linhas = []
    for lbl in oos.columns:
        so_custo = costs.aplicar_custos_serie(oos[lbl], giros[lbl], imposto=0.0)
        liq = costs.aplicar_custos_serie(oos[lbl], giros[lbl], retornos_preco=oos_preco[lbl])
        rb = metrics.estatisticas(oos[lbl], rf_diaria=rf)["retorno_anual"]
        rc = metrics.estatisticas(so_custo, rf_diaria=rf)["retorno_anual"]
        rl = metrics.estatisticas(liq, rf_diaria=rf)["retorno_anual"]
        g = giros[lbl]
        linhas.append({
            "carteira": lbl,
            "giro_medio_am": float(g.mean()),
            "custo_medio_am": float((config.TRANSACTION_COST * g).mean()),
            "ret_bruto_aa": rb,
            "arrasto_custo_aa": rb - rc,
            "arrasto_imposto_aa": rc - rl,
            "ret_liq_aa": rl,
        })
    tab = pd.DataFrame(linhas).set_index("carteira").round(4)
    print(tab.to_string())
    tab.to_csv(config.TABLES_DIR / "tabela_custos_decomposta.csv")


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

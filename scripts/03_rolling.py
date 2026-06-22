"""
Backtest de janela rolante (fora da amostra) — resultado científico principal.

Forma a carteira com 360 pregões, mantém por 22 e avança, reconstruindo o GPMF e
a centralidade a cada passo. Emenda as janelas de manutenção em curvas contínuas
e reavalia a hipótese de Pozzi (periferia vs centro) sem viés de look-ahead.

Saída bruta (sem custos); o líquido é tratado no script 04.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import metrics, pipeline, riskfree, rolling


def main() -> None:
    dados = pipeline.preparar_dados()
    ret_log = dados["retornos_log"]
    print(f"universo: {len(dados['universo'])} FIIs | janela total: {len(ret_log)} pregões")
    print(f"formação {config.FORMATION_DAYS}d / teste {config.TEST_DAYS}d / "
          f"passo {config.ROLL_STEP_DAYS}d\n")

    res = rolling.backtest_rolling(ret_log)
    oos = res["retornos"]
    print(f"período fora da amostra: {oos.index[0].date()} a {oos.index[-1].date()} "
          f"({len(oos)} pregões, {len(res['grafos'])} rebalanceamentos)\n")

    # planaridade/conectividade mantidas a cada formação?
    g = res["grafos"]
    print(f"GPMF a cada passo: arestas médias {g['arestas'].mean():.0f}, "
          f"sempre planar={g['planar'].all()}, sempre conexo={g['conexo'].all()}\n")

    # benchmark alinhado ao período fora da amostra
    bench = dados["benchmark"].reindex(oos.index).dropna() if dados["benchmark"] is not None else None

    # taxa livre de risco (CDI diário) para o Sharpe sobre o excesso
    rf = riskfree.serie_rf_diaria(oos.index)
    print(f"rf: {config.RISK_FREE_SOURCE} (média {rf.mean()*config.TRADING_DAYS_PER_YEAR*100:.1f}% a.a.)\n")

    linhas = []
    for lbl in oos.columns:
        linhas.append({"carteira": lbl, **metrics.estatisticas(oos[lbl], rf_diaria=rf)})
    if bench is not None:
        linhas.append({"carteira": "benchmark", **metrics.estatisticas(bench, rf_diaria=rf)})
    tabela = pd.DataFrame(linhas).set_index("carteira").round(4)
    print(tabela.to_string())
    tabela.to_csv(config.TABLES_DIR / "tabela_rolling_bruta.csv")

    # persiste séries para os próximos scripts
    oos.to_csv(config.PROCESSED_DIR / "retornos_oos.csv")
    res["giros"].to_csv(config.PROCESSED_DIR / "giros.csv")
    g.to_csv(config.PROCESSED_DIR / "grafos_rolling.csv")
    if bench is not None:
        bench.rename("benchmark").to_csv(config.PROCESSED_DIR / "benchmark_oos.csv")

    _teste_pozzi(oos, rf)
    _figura_curvas(oos, bench)


def _teste_pozzi(oos: pd.DataFrame, rf) -> None:
    """Compara centro vs periferia para o tamanho de referência (10)."""
    print("\n--- hipótese de Pozzi (periferia vence?) fora da amostra ---")
    for tam in config.PORTFOLIO_SIZES:
        c = metrics.estatisticas(oos[f"central_{tam}"], rf_diaria=rf)["sharpe"]
        p = metrics.estatisticas(oos[f"peripheral_{tam}"], rf_diaria=rf)["sharpe"]
        venc = "PERIFERIA" if p > c else "CENTRO"
        print(f"tam {tam:>2}: Sharpe centro={c:.3f}  periferia={p:.3f}  -> vence {venc}")


def _figura_curvas(oos: pd.DataFrame, bench) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from src.metrics import curva_acumulada

        fig, ax = plt.subplots(figsize=(10, 6))
        for lbl in ("central_10", "peripheral_10", "hybrid_10"):
            ax.plot(oos.index, curva_acumulada(oos[lbl]), label=lbl)
        if bench is not None:
            ax.plot(bench.index, curva_acumulada(bench), label="benchmark", color="k", ls="--")
        ax.set_title("Retorno acumulado fora da amostra (sem custos)")
        ax.set_ylabel("crescimento de R$ 1")
        ax.legend()
        fig.tight_layout()
        caminho = config.FIGURES_DIR / "curvas_oos_bruto.png"
        fig.savefig(caminho, dpi=130)
        print(f"\nfigura das curvas em {caminho}")
    except Exception as e:
        print(f"(figura ignorada: {e})")


if __name__ == "__main__":
    main()

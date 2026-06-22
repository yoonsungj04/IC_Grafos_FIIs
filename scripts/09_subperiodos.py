"""
Robustez por sub-período (fora da amostra).

O resultado principal cobre uma única janela (2023–2025). Um avaliador pergunta:
"isso vale só nesse pedaço de mercado?" Para responder, partimos a série fora da
amostra em sub-períodos consecutivos e reavaliamos a hipótese de Pozzi (periferia
vs centro) e o desempenho frente ao benchmark em cada um, em base LÍQUIDA (já com
custo e imposto) e com Sharpe sobre o excesso ao CDI. Se o ordenamento se mantém
em sub-períodos distintos, a conclusão é robusta; se inverte, é dependente de
regime e isso precisa constar no artigo.

Lê o cache fora da amostra (scripts 03/04). Saída: tabela_subperiodos.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import metrics, riskfree


def _blocos(idx: pd.DatetimeIndex, n: int) -> list[tuple]:
    """Divide o índice em n sub-períodos consecutivos de tamanho ~igual."""
    cortes = np.array_split(np.arange(len(idx)), n)
    return [(idx[c[0]], idx[c[-1]]) for c in cortes if len(c)]


def main(n_sub: int = 2) -> None:
    liq_path = config.PROCESSED_DIR / "retornos_oos_liquidos.csv"
    if not liq_path.exists():
        raise FileNotFoundError("rode os scripts 03 e 04 antes (faltam séries líquidas).")
    liq = pd.read_csv(liq_path, index_col=0, parse_dates=True)
    bench_path = config.PROCESSED_DIR / "benchmark_oos.csv"
    bench = (pd.read_csv(bench_path, index_col=0, parse_dates=True).iloc[:, 0]
             if bench_path.exists() else None)

    rf = riskfree.serie_rf_diaria(liq.index)
    periodos = _blocos(liq.index, n_sub)
    rotulos = ["completo"] + [f"sub{i+1}" for i in range(len(periodos))]
    janelas = [(liq.index[0], liq.index[-1])] + periodos

    print(f"OOS líquido: {liq.index[0].date()} a {liq.index[-1].date()} "
          f"({len(liq)} pregões) | sub-períodos: {n_sub}\n")

    linhas = []
    for rot, (ini, fim) in zip(rotulos, janelas):
        sl = liq.loc[ini:fim]
        rf_sl = rf.loc[ini:fim]
        reg = {"periodo": rot, "inicio": ini.date(), "fim": fim.date(), "n": len(sl)}
        for tam in config.PORTFOLIO_SIZES:
            sc = metrics.estatisticas(sl[f"central_{tam}"], rf_diaria=rf_sl)["sharpe"]
            sp = metrics.estatisticas(sl[f"peripheral_{tam}"], rf_diaria=rf_sl)["sharpe"]
            reg[f"sharpe_central_{tam}"] = round(sc, 3)
            reg[f"sharpe_perif_{tam}"] = round(sp, 3)
            reg[f"pozzi_{tam}"] = bool(sp > sc)
        if bench is not None:
            b = bench.reindex(sl.index).dropna()
            reg["sharpe_benchmark"] = round(metrics.estatisticas(b, rf_diaria=rf_sl)["sharpe"], 3)
        linhas.append(reg)

    tab = pd.DataFrame(linhas).set_index("periodo")
    print(tab.to_string())
    tab.to_csv(config.TABLES_DIR / "tabela_subperiodos.csv")

    # veredito: a hipótese de Pozzi se sustenta em todos os sub-períodos?
    cols_pozzi = [f"pozzi_{t}" for t in config.PORTFOLIO_SIZES]
    sub = tab.loc[[r for r in tab.index if r.startswith("sub")], cols_pozzi]
    print("\n--- robustez da hipótese de Pozzi (periferia > centro, líquido) ---")
    for tam in config.PORTFOLIO_SIZES:
        vals = sub[f"pozzi_{tam}"]
        print(f"tam {tam:>2}: confirma em {int(vals.sum())}/{len(vals)} sub-períodos "
              f"-> {'ROBUSTO' if vals.all() else 'DEPENDE DO PERÍODO'}")
    print(f"\nsalvo em {config.TABLES_DIR / 'tabela_subperiodos.csv'}")


if __name__ == "__main__":
    main()

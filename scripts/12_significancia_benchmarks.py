"""
Significância das diferenças de Sharpe envolvendo os benchmarks clássicos.

Mesmo par de testes do script 04 (bootstrap de blocos circulares como principal,
Jobson-Korkie/Memmel como secundário), para que as novas linhas entrem na
tabela de significância do artigo na mesma base das já existentes.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import benchmarks, costs, gpmf, metrics, pipeline, riskfree, rolling


def _liq(oos, giros, preco):
    return pd.DataFrame({
        lbl: costs.aplicar_custos_serie(oos[lbl], giros[lbl], retornos_preco=preco[lbl])
        for lbl in oos.columns})


def main() -> None:
    dados = pipeline.preparar_dados()
    ret_log, ret_preco = dados["retornos_log"], dados["retornos_log_preco"]

    seletores = {
        "gpmf_peripheral_10_minvar": ("min_var", benchmarks.seletor_rede("peripheral", 10)),
        "gpmf_central_10_minvar": ("min_var", benchmarks.seletor_rede("central", 10)),
    }
    rb = benchmarks.backtest_benchmarks(ret_log, retornos_preco=ret_preco,
                                        seletores=seletores)
    liq_b = _liq(rb["retornos"], rb["giros"], rb["retornos_preco"])
    print(f"rebalanceamentos nos benchmarks: {len(rb['giros'])}")
    print("giro do 1o rebalance (equal_weight):",
          float(rb["giros"]["equal_weight"].iloc[0]),
          "| demais:", float(rb["giros"]["equal_weight"].iloc[1:].mean()), "\n")

    series = {f"bench::{c}": liq_b[c] for c in liq_b.columns}

    for nome, construtor in (("GPMF", gpmf.construir_gpmf), ("MST", gpmf.construir_mst)):
        r = rolling.backtest_rolling(ret_log, construtor=construtor,
                                     retornos_preco=ret_preco)
        l = _liq(r["retornos"], r["giros"], r["retornos_preco"])
        for c in l.columns:
            series[f"{nome}::{c}"] = l[c]

    idx = liq_b.index
    rf = riskfree.serie_rf_diaria(idx)
    bench = pd.read_csv(config.PROCESSED_DIR / "benchmark_oos.csv",
                        index_col=0, parse_dates=True).iloc[:, 0]
    series["IFIX"] = bench.reindex(idx).dropna()

    pares = [
        ("bench::min_var", "IFIX"),
        ("bench::min_var_shrink", "IFIX"),
        ("bench::tangency", "IFIX"),
        ("bench::equal_weight", "IFIX"),
        ("bench::min_var", "GPMF::peripheral_20"),
        ("bench::min_var", "GPMF::peripheral_10"),
        ("bench::min_var", "GPMF::central_10"),
        ("bench::min_var", "bench::tangency"),
        ("bench::min_var", "bench::equal_weight"),
        ("GPMF::peripheral_10", "bench::gpmf_peripheral_10_minvar"),
    ]

    linhas = []
    print(f"{'A':<32} {'B':<26} {'dSharpe':>8} {'IC95':>20} {'p_boot':>8} {'p_JK':>7}")
    for a, b in pares:
        bs = metrics.bootstrap_diff_sharpe(series[a], series[b], rf_diaria=rf)
        jk = metrics.jobson_korkie(series[a], series[b], rf_diaria=rf)
        ic = f"[{bs['ic_baixo']:+.2f}, {bs['ic_alto']:+.2f}]"
        print(f"{a:<32} {b:<26} {bs['diff']:+8.2f} {ic:>20} "
              f"{bs['p_boot']:8.3f} {jk['p_valor']:7.3f}")
        linhas.append({"a": a, "b": b, "diff_sharpe_aa": bs["diff"],
                       "ic95_baixo": bs["ic_baixo"], "ic95_alto": bs["ic_alto"],
                       "p_boot": bs["p_boot"], "p_jk": jk["p_valor"], "n": jk["n"]})

    pd.DataFrame(linhas).round(4).to_csv(
        config.TABLES_DIR / "significancia_benchmarks.csv", index=False)
    print(f"\ngravado em {config.TABLES_DIR / 'significancia_benchmarks.csv'}")


if __name__ == "__main__":
    main()

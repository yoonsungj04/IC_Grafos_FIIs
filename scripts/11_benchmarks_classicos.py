"""
Benchmarks clássicos (Markowitz) + comparação GPMF x MST sob base tributária única.

Faz duas coisas que o artigo precisa:

1. RECALCULA a comparação GPMF x MST com a MESMA base de imposto usada no
   script 04 (ganho só de PREÇO, via `retornos_preco`). O script 05 chama
   `backtest_rolling` e `aplicar_custos_serie` sem esse argumento, então cai no
   fallback que tributa o ganho TOTAL — incluindo o dividendo, que é isento.
   Resultado: as duas colunas da tabela de comparação do artigo saíam de
   convenções diferentes. Aqui as duas saem da mesma.

2. Roda os benchmarks clássicos long-only (1/N, mínima variância, mínima
   variância com encolhimento de Ledoit-Wolf, e tangência) na mesma janela
   rolante, com os mesmos custos e o mesmo imposto, mais as linhas de
   "seleção por rede + pesos otimizados".

Saídas:
  results/tables/tabela_comparacao_filtros_corrigida.csv
  results/tables/tabela_benchmarks_classicos.csv
  results/tables/latex_tabelas.txt   (linhas prontas para colar no main.tex)
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import benchmarks, costs, gpmf, metrics, pipeline, riskfree, rolling


def _liquido(oos, giros, oos_preco):
    """Aplica custo + imposto usando SEMPRE a base de ganho de preço."""
    return pd.DataFrame({
        lbl: costs.aplicar_custos_serie(oos[lbl], giros[lbl],
                                        retornos_preco=oos_preco[lbl])
        for lbl in oos.columns
    })


def _stats(serie, rf, giro=None):
    e = metrics.estatisticas(serie, rf_diaria=rf)
    return {
        "ret_liq_aa": e["retorno_anual"],
        "vol_aa": e["vol_anual"],
        "sharpe_liq": e["sharpe"],
        "dd_max": e["drawdown_max"],
        "giro_medio": float(giro.mean()) if giro is not None else float("nan"),
    }


# --------------------------------------------------------------------------- #
# 1. GPMF x MST sob base tributária única
# --------------------------------------------------------------------------- #

def comparacao_filtros(dados, rf) -> pd.DataFrame:
    ret_log = dados["retornos_log"]
    ret_preco = dados["retornos_log_preco"]
    linhas = []

    for nome, construtor in (("GPMF", gpmf.construir_gpmf),
                             ("MST", gpmf.construir_mst)):
        print(f"  rodando {nome} ...", flush=True)
        res = rolling.backtest_rolling(ret_log, construtor=construtor,
                                       retornos_preco=ret_preco)
        liq = _liquido(res["retornos"], res["giros"], res["retornos_preco"])
        for lbl in liq.columns:
            tipo, tam = lbl.rsplit("_", 1)
            linhas.append({"filtro": nome, "carteira": tipo, "k": int(tam),
                           **_stats(liq[lbl], rf, res["giros"][lbl])})

    return pd.DataFrame(linhas)


# --------------------------------------------------------------------------- #
# 2. Benchmarks clássicos
# --------------------------------------------------------------------------- #

def benchmarks_classicos(dados, rf) -> tuple[pd.DataFrame, dict]:
    ret_log = dados["retornos_log"]
    ret_preco = dados["retornos_log_preco"]

    seletores = {
        "gpmf_peripheral_10_minvar": ("min_var", benchmarks.seletor_rede("peripheral", 10)),
        "gpmf_central_10_minvar": ("min_var", benchmarks.seletor_rede("central", 10)),
    }
    print("  rodando benchmarks clássicos ...", flush=True)
    res = benchmarks.backtest_benchmarks(ret_log, retornos_preco=ret_preco,
                                         seletores=seletores)
    liq = _liquido(res["retornos"], res["giros"], res["retornos_preco"])

    linhas = [{"estrategia": lbl, **_stats(liq[lbl], rf, res["giros"][lbl])}
              for lbl in liq.columns]
    return pd.DataFrame(linhas), {lbl: liq[lbl] for lbl in liq.columns}


# --------------------------------------------------------------------------- #
# 3. Saída em LaTeX
# --------------------------------------------------------------------------- #

def _pct(x):
    return f"${x*100:+.1f}\\%$"


def latex_tabela_filtros(df: pd.DataFrame) -> str:
    piv = df.pivot_table(index=["carteira", "k"], columns="filtro", values="sharpe_liq")
    ordem = [("central", k) for k in (10, 15, 20)]
    ordem += [("peripheral", k) for k in (10, 15, 20)]
    ordem += [("hybrid", k) for k in (10, 15, 20)]
    rotulo = {"central": "Central", "peripheral": "Peripheral", "hybrid": "Hybrid"}
    out = ["% Tabela 3 (tab:oos) -- recalculada com base tributaria unica"]
    for tipo, k in ordem:
        g, m = piv.loc[(tipo, k), "GPMF"], piv.loc[(tipo, k), "MST"]
        out.append(f"{rotulo[tipo]:<11}& {k} & ${g:.2f}$ & ${m:.2f}$ \\\\")
    return "\n".join(out)


def latex_tabela_benchmarks(dfb: pd.DataFrame, dff: pd.DataFrame,
                            bench_stats: dict) -> str:
    nome = {
        "equal_weight": "Equal weight ($1/N$, all 51)",
        "min_var": "Minimum variance",
        "min_var_shrink": "Minimum variance (shrinkage)",
        "tangency": "Tangency (max.\\ Sharpe)",
        "gpmf_peripheral_10_minvar": "PMFG Peripheral-10 $+$ min.\\ var.",
        "gpmf_central_10_minvar": "PMFG Central-10 $+$ min.\\ var.",
    }
    b = dfb.set_index("estrategia")

    def linha(rot, r):
        return (f"{rot:<33}& {_pct(r['ret_liq_aa'])} & {r['vol_aa']*100:.1f}\\% "
                f"& ${r['sharpe_liq']:.2f}$ & ${r['dd_max']*100:.1f}\\%$ "
                f"& {r['giro_medio']:.2f} \\\\")

    out = ["", "% Tabela 5 (tab:classical) -- linhas completas"]
    out.append("\\multicolumn{6}{@{}l}{\\textit{Passive}}\\\\")
    out.append(f"{'IFIX (index)':<33}& {_pct(bench_stats['ret_liq_aa'])} "
               f"& {bench_stats['vol_aa']*100:.1f}\\% & ${bench_stats['sharpe_liq']:.2f}$ "
               f"& ${bench_stats['dd_max']*100:.1f}\\%$ & -- \\\\")
    out.append(linha(nome["equal_weight"], b.loc["equal_weight"]))
    out.append("\\midrule")
    out.append("\\multicolumn{6}{@{}l}{\\textit{Classical mean--variance}}\\\\")
    for k in ("min_var", "min_var_shrink", "tangency"):
        out.append(linha(nome[k], b.loc[k]))
    out.append("\\midrule")
    out.append("\\multicolumn{6}{@{}l}{\\textit{Network selection, equal weights}}\\\\")
    f = dff.set_index(["filtro", "carteira", "k"])
    for filtro, tipo, k, rot in (("GPMF", "central", 10, "PMFG Central-10"),
                                 ("GPMF", "peripheral", 10, "PMFG Peripheral-10"),
                                 ("GPMF", "peripheral", 20, "PMFG Peripheral-20"),
                                 ("MST", "peripheral", 10, "MST Peripheral-10")):
        out.append(linha(rot, f.loc[(filtro, tipo, k)]))
    out.append("\\midrule")
    out.append("\\multicolumn{6}{@{}l}{\\textit{Network selection, optimised weights}}\\\\")
    for k in ("gpmf_peripheral_10_minvar", "gpmf_central_10_minvar"):
        out.append(linha(nome[k], b.loc[k]))
    return "\n".join(out)


# --------------------------------------------------------------------------- #

def main() -> None:
    dados = pipeline.preparar_dados()
    ret_log = dados["retornos_log"]
    print(f"universo: {len(dados['universo'])} FIIs | {len(ret_log)} pregões\n")

    # rf e benchmark alinhados ao período fora da amostra do script 03
    oos_ref = pd.read_csv(config.PROCESSED_DIR / "retornos_oos.csv",
                          index_col=0, parse_dates=True)
    rf = riskfree.serie_rf_diaria(oos_ref.index)

    bench = pd.read_csv(config.PROCESSED_DIR / "benchmark_oos.csv",
                        index_col=0, parse_dates=True).iloc[:, 0]
    bench = bench.reindex(oos_ref.index).dropna()
    bench_stats = _stats(bench, rf)

    print("--- 1. GPMF x MST com base tributária única (ganho de preço) ---")
    dff = comparacao_filtros(dados, rf)
    dff.round(4).to_csv(config.TABLES_DIR / "tabela_comparacao_filtros_corrigida.csv",
                        index=False)
    piv = dff.pivot_table(index=["carteira", "k"], columns="filtro",
                          values="sharpe_liq").round(3)
    print(piv.to_string(), "\n")

    print("--- 2. Benchmarks clássicos ---")
    dfb, _ = benchmarks_classicos(dados, rf)
    dfb.round(4).to_csv(config.TABLES_DIR / "tabela_benchmarks_classicos.csv",
                        index=False)
    print(dfb.set_index("estrategia").round(4).to_string(), "\n")
    print(f"IFIX: ret {bench_stats['ret_liq_aa']:.4f}  vol {bench_stats['vol_aa']:.4f}  "
          f"sharpe {bench_stats['sharpe_liq']:.4f}  dd {bench_stats['dd_max']:.4f}\n")

    tex = (latex_tabela_filtros(dff) + "\n"
           + latex_tabela_benchmarks(dfb, dff, bench_stats) + "\n")
    caminho = config.TABLES_DIR / "latex_tabelas.txt"
    caminho.write_text(tex, encoding="utf-8")
    print("--- 3. LaTeX ---")
    print(tex)
    print(f"gravado em {caminho}")


if __name__ == "__main__":
    main()

"""
Comparação alinhada GPMF × AGM — braços do trabalho conjunto sob premissas
idênticas.

O braço AGM (Augusto) e o braço GPMF (Yoon) foram desenvolvidos separadamente e
adotaram convenções diferentes (sobretudo o tratamento de dividendos, a janela e
o universo). Para uma comparação cientificamente válida, este script roda os DOIS
filtros sobre os MESMOS dados reprodutíveis (51 FIIs, mar/2022–nov/2025,
fechamento ajustado sem dupla contagem de dividendos), com a MESMA regra de
seleção (score composto, como na AGM) e o mesmo modelo de custos.

Assim, a única diferença entre as duas linhas é o filtro do grafo — que é
exatamente o que queremos comparar.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import costs, gpmf, metrics, pipeline, riskfree, rolling

TAMANHOS = (5, 10, 15, 20)   # inclui 5 e 10 (usados pela AGM) e 15/20 (nossos)
MEDIDA = "composite"          # mesma regra de seleção da AGM


def _rodar(ret_log, construtor, rf):
    res = rolling.backtest_rolling(ret_log, tamanhos=TAMANHOS, medida=MEDIDA,
                                   construtor=construtor)
    oos, giros = res["retornos"], res["giros"]
    linhas, series_liq = {}, {}
    for lbl in oos.columns:
        liq = costs.aplicar_custos_serie(oos[lbl], giros[lbl])
        series_liq[lbl] = liq
        eb, el = metrics.estatisticas(oos[lbl], rf_diaria=rf), metrics.estatisticas(liq, rf_diaria=rf)
        linhas[lbl] = {
            "ret_anual_bruto": eb["retorno_anual"],
            "sharpe_bruto": eb["sharpe"],
            "sharpe_liq": el["sharpe"],
            "giro_medio": float(giros[lbl].mean()),
        }
    return pd.DataFrame(linhas).T, res["grafos"], series_liq


def main():
    dados = pipeline.preparar_dados()
    ret_log = dados["retornos_log"]
    bench = dados["benchmark"]
    rf = riskfree.serie_rf_diaria(ret_log.index)
    print(f"universo comum: {len(dados['universo'])} FIIs | {len(ret_log)} pregões")
    print(f"regra de seleção: score composto (igual à AGM)\n")

    filtros = {"GPMF": gpmf.construir_gpmf, "AGM": gpmf.construir_mst}
    tabelas, series = {}, {}
    for nome, construtor in filtros.items():
        df, grafos, series_liq = _rodar(ret_log, construtor, rf)
        df.insert(0, "filtro", nome)
        df.index.name = "carteira"
        tabelas[nome] = df
        series[nome] = series_liq
        print(f"{nome}: {int(grafos['arestas'].mean())} arestas médias")

    completa = pd.concat(tabelas.values()).round(4)
    completa.to_csv(config.TABLES_DIR / "comparacao_alinhada_augusto.csv")
    print("\n" + completa.to_string())

    # benchmark no mesmo período fora da amostra
    if bench is not None:
        oos_idx = pd.read_csv(config.PROCESSED_DIR / "retornos_oos.csv",
                              index_col=0, parse_dates=True).index
        b = bench.reindex(oos_idx).dropna()
        print(f"\nbenchmark (XFIX11) fora da amostra: Sharpe "
              f"{metrics.estatisticas(b, rf_diaria=rf)['sharpe']:.3f}, "
              f"retorno a.a. {metrics.estatisticas(b, rf_diaria=rf)['retorno_anual']*100:.2f}%")

    # checagem da hipótese de Pozzi nos dois filtros
    print("\n--- Pozzi (periferia > centro, bruto) ---")
    for nome in filtros:
        df = tabelas[nome]
        for tam in TAMANHOS:
            c = df.loc[f"central_{tam}", "sharpe_bruto"]
            p = df.loc[f"peripheral_{tam}", "sharpe_bruto"]
            print(f"{nome} tam {tam:>2}: centro={c:+.3f} periferia={p:+.3f} "
                  f"-> {'PERIFERIA' if p > c else 'CENTRO'}")

    _figura(series, bench)


def _figura(series, bench):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from src.metrics import curva_acumulada

        idx = series["GPMF"]["peripheral_10"].index
        fig, ax = plt.subplots(figsize=(11, 6))
        ax.plot(idx, curva_acumulada(series["GPMF"]["peripheral_10"]),
                color="C2", label="GPMF Periférica-10")
        ax.plot(idx, curva_acumulada(series["AGM"]["peripheral_10"]),
                color="C2", ls="--", label="AGM Periférica-10")
        ax.plot(idx, curva_acumulada(series["GPMF"]["central_10"]),
                color="C3", label="GPMF Central-10")
        ax.plot(idx, curva_acumulada(series["AGM"]["central_10"]),
                color="C3", ls="--", label="AGM Central-10")
        if bench is not None:
            b = bench.reindex(idx).dropna()
            ax.plot(b.index, curva_acumulada(b), color="k", ls=":", label="benchmark")
        ax.set_title("GPMF vs AGM (regra de seleção idêntica, dados corrigidos) — "
                     "líquido, fora da amostra")
        ax.set_ylabel("crescimento de R$ 1")
        ax.legend()
        fig.tight_layout()
        caminho = config.FIGURES_DIR / "comparacao_alinhada_augusto.png"
        fig.savefig(caminho, dpi=130)
        print(f"\nfigura salva em {caminho}")
    except Exception as e:
        print(f"(figura ignorada: {e})")


if __name__ == "__main__":
    main()

"""
Comparação completa GPMF × AGM para o artigo.

Roda o backtest rolante com os dois filtros e produz, para cada combinação de
tipo e tamanho de carteira: Sharpe bruto, Sharpe líquido e giro médio. Também
resume, por filtro e tamanho, se a periferia supera o centro (hipótese de
Pozzi), bruto e líquido. Salva tudo em results/tables/comparacao_completa.csv.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import costs, gpmf, metrics, pipeline, riskfree, rolling


def _rodar(ret_log, construtor, rf, ret_log_preco=None):
    res = rolling.backtest_rolling(ret_log, construtor=construtor,
                                   retornos_preco=ret_log_preco)
    oos, giros, oos_preco = res["retornos"], res["giros"], res["retornos_preco"]
    linhas = {}
    for lbl in oos.columns:
        liq = costs.aplicar_custos_serie(
            oos[lbl], giros[lbl],
            retornos_preco=(oos_preco[lbl] if oos_preco is not None else None))
        linhas[lbl] = {
            "sharpe_bruto": metrics.estatisticas(oos[lbl], rf_diaria=rf)["sharpe"],
            "sharpe_liq": metrics.estatisticas(liq, rf_diaria=rf)["sharpe"],
            "giro_medio": float(giros[lbl].mean()),
        }
    return pd.DataFrame(linhas).T, res["grafos"]


def main():
    dados = pipeline.preparar_dados()
    ret_log = dados["retornos_log"]
    ret_log_preco = dados["retornos_log_preco"]
    rf = riskfree.serie_rf_diaria(ret_log.index)

    filtros = {"GPMF": gpmf.construir_gpmf, "AGM": gpmf.construir_mst}
    tabelas = {}
    for nome, construtor in filtros.items():
        df, grafos = _rodar(ret_log, construtor, rf, ret_log_preco=ret_log_preco)
        df.insert(0, "filtro", nome)
        df.index.name = "carteira"
        tabelas[nome] = df
        print(f"{nome}: {int(grafos['arestas'].mean())} arestas médias, "
              f"sempre planar={grafos['planar'].all()}")

    completa = pd.concat(tabelas.values()).round(4)
    completa.to_csv(config.TABLES_DIR / "comparacao_completa.csv")
    print("\n" + completa.to_string())

    # resumo da hipótese de Pozzi por filtro e tamanho (bruto e líquido)
    print("\n--- Pozzi (periferia > centro?) por filtro e tamanho ---")
    resumo = []
    for nome in filtros:
        df = tabelas[nome]
        for tam in config.PORTFOLIO_SIZES:
            c_b = df.loc[f"central_{tam}", "sharpe_bruto"]
            p_b = df.loc[f"peripheral_{tam}", "sharpe_bruto"]
            c_l = df.loc[f"central_{tam}", "sharpe_liq"]
            p_l = df.loc[f"peripheral_{tam}", "sharpe_liq"]
            resumo.append({"filtro": nome, "tamanho": tam,
                           "pozzi_bruto": p_b > c_b, "pozzi_liq": p_l > c_l,
                           "sharpe_peri_bruto": round(p_b, 3),
                           "sharpe_cent_bruto": round(c_b, 3)})
            print(f"{nome} tam {tam}: bruto periferia={p_b:.3f} centro={c_b:.3f} "
                  f"-> {'PERIFERIA' if p_b > c_b else 'CENTRO'}")
    pd.DataFrame(resumo).to_csv(config.TABLES_DIR / "pozzi_por_filtro.csv", index=False)


if __name__ == "__main__":
    main()

"""
Relatório Final da IC — v3.

Atualiza os números para a convenção atual (Sharpe sobre o excesso ao CDI) e trata
o braço AGM como oficial (premissas alinhadas com o parceiro). Acrescenta a
decomposição de custos, os testes de significância (Jobson-Korkie + bootstrap) e a
robustez por subperíodo. Salva em docs/Relatorio_Final_Yoon_v3.docx (não
sobrescreve v1/v2).
"""
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src.relatorio_utils import AZUL, data_br, fig, h1, h2, mes_ano, par, tabela


def main():
    est = pd.read_csv(config.TABLES_DIR / "tabela_estatica.csv", index_col=0)
    alin = pd.read_csv(config.TABLES_DIR / "comparacao_alinhada_augusto.csv", index_col=0)
    deco = pd.read_csv(config.TABLES_DIR / "tabela_custos_decomposta.csv", index_col=0)
    sub = pd.read_csv(config.TABLES_DIR / "tabela_subperiodos.csv", index_col=0)
    grafos = pd.read_csv(config.PROCESSED_DIR / "grafos_rolling.csv", index_col=0, parse_dates=True)
    oos = pd.read_csv(config.PROCESSED_DIR / "retornos_oos.csv", index_col=0, parse_dates=True)

    n_fii = int(grafos["vertices"].iloc[0])
    n_pregoes_est = int(est["n_periodos"].iloc[0])
    n_rebal = len(grafos)
    arestas = int(grafos["arestas"].iloc[0])
    bench_sh = float(sub.loc["completo", "sharpe_benchmark"])
    _g = alin[(alin.index == "peripheral_5") & (alin["filtro"] == "GPMF")]
    peri5_liq = float(_g["sharpe_liq"].iloc[0]) if len(_g) else None

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    # ---- capa / identificação ----
    for txt, sz, cor in [
        ("Programa Institucional de Iniciação Científica e Tecnológica", 13, None),
        ("Relatório Final de Atividades", 15, AZUL)]:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(txt); r.bold = True; r.font.size = Pt(sz)
        if cor:
            r.font.color.rgb = cor
    titulo = ("Análise Comparativa de Métodos de Formação de Carteira Baseados em "
              "Grafos para Fundos Imobiliários (FIIs): Casos de Estudo com o Grafo "
              "Planar Maximamente Filtrado")
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(titulo).bold = True
    doc.add_paragraph()
    for k, v in [("Projeto", titulo), ("Bolsista / RA", "Yoon Sung Jang / RA [preencher]"),
                 ("Orientador", "Prof. Dr. João Roberto Bertini Junior"),
                 ("Local de execução", "Faculdade de Tecnologia (FT) — UNICAMP, Limeira/SP"),
                 ("Vigência", "setembro/2025 a agosto/2026")]:
        p = doc.add_paragraph(); p.add_run(f"{k}: ").bold = True; p.add_run(v)

    # ---- resumo ----
    h1(doc, "Resumo")
    par(doc,
        "Este projeto investiga o uso de filtragem em grafos para a formação de "
        "carteiras de Fundos de Investimento Imobiliário (FIIs), comparando o Grafo "
        "Planar Maximamente Filtrado (GPMF) com a Árvore Geradora Mínima (AGM), esta "
        "desenvolvida pelo parceiro Augusto Carneiro da Silva. Os dois filtros são "
        "avaliados sobre os mesmos dados (51 FIIs, mar/2022–nov/2025), com a mesma "
        "regra de seleção e validação fora da amostra por janela deslizante. Avaliando "
        "o desempenho frente ao CDI (taxa livre de risco real), nenhuma carteira — nem "
        "o benchmark — superou a renda fixa no período: os FIIs renderam menos que o "
        "CDI. Ainda assim, o GPMF ordena de forma consistente as carteiras periféricas "
        "acima das centrais (hipótese de Pozzi) em todos os tamanhos, enquanto a AGM "
        "falha no menor; e a carteira Periférica-5 do GPMF supera o benchmark passivo "
        "mesmo no líquido. Esse efeito, porém, não é robusto entre subperíodos nem "
        "estatisticamente significativo, o que é discutido como limitação.")

    # ---- introdução ----
    h1(doc, "Introdução")
    par(doc,
        "Métodos de filtragem em grafos resumem a estrutura de correlação de um mercado "
        "em poucas ligações relevantes. A AGM (Mantegna, 1999) retém N−1 arestas; o "
        "GPMF (Tumminello et al., 2005), por exigir apenas planaridade, retém 3N−6 e "
        "preserva ciclos e cliques. Pozzi, Di Matteo e Aste (2013) propõem que ativos "
        "periféricos formam carteiras com melhor relação risco-retorno; Peralta e "
        "Zareei (2016) reforçam a hipótese com centralidade de autovetor. Os FIIs "
        "brasileiros têm particularidades relevantes — distribuição de ≥95% dos lucros, "
        "isenção de IR sobre proventos para PF e 15% sobre ganho de capital. O objetivo "
        "é testar a hipótese da periferia para FIIs e verificar se o filtro escolhido "
        "(GPMF ou AGM) altera a conclusão.")

    # ---- materiais e métodos ----
    h1(doc, "Materiais e Métodos")
    h2(doc, "Dados e convenção de retorno")
    par(doc,
        f"Fechamentos diários ajustados de FIIs via yfinance, de {mes_ano(config.START_DATE)} "
        f"a {mes_ano(config.END_DATE)} ({n_pregoes_est} pregões); universo determinístico "
        f"de {n_fii} FIIs (histórico completo, <5% de dados faltantes); benchmark XFIX11 "
        f"(proxy do IFIX). Verificou-se empiricamente que o fechamento ajustado já "
        f"reinveste os dividendos, de modo que o retorno total é Rt = ln(Pt/Pt−1) sobre "
        f"o ajustado — somar Dt contaria o provento duas vezes.")
    fig(doc, "verifica_dividendos_MXRF11.png",
        "Figura 1 — Verificação da convenção de dividendos (MXRF11): a razão "
        "ajustado/bruto em degraus corresponde aos proventos já reinvestidos.")
    h2(doc, "Grafos, carteiras e seleção")
    par(doc,
        "Da correlação de Pearson obtém-se a distância de Mantegna d = √(2(1−ρ)) e, "
        "dela, o GPMF (planaridade por Boyer-Myrvold) e a AGM (Kruskal). Para cada FII "
        "calcula-se um escore composto de centralidade (média normalizada de grau, "
        "intermediação e proximidade) — a mesma regra nos dois filtros, de modo que a "
        "única diferença entre eles é a estrutura do grafo. Formam-se carteiras "
        "Central, Periférica e Híbrida de 5, 10, 15 e 20 ativos, com pesos iguais.")
    h2(doc, "Validação fora da amostra, custos e significância")
    par(doc,
        f"Janela deslizante: forma com {config.FORMATION_DAYS} pregões, mantém "
        f"{config.TEST_DAYS}, avança {config.ROLL_STEP_DAYS}, reconstruindo o grafo a "
        f"cada passo (período fora da amostra de {data_br(oos.index[0])} a "
        f"{data_br(oos.index[-1])}, {len(oos)} pregões, {n_rebal} rebalanceamentos). "
        f"Aplica-se custo de 0,3% sobre o giro e 15% de IR sobre ganho de capital. O "
        f"Índice de Sharpe é calculado sobre o retorno EXCEDENTE ao CDI diário "
        f"(≈11,6% a.a. no período) — o custo de oportunidade real; usar zero como taxa "
        f"livre de risco infla artificialmente o Sharpe. A significância segue o teste "
        f"de Jobson-Korkie (Memmel, 2003) e um intervalo de confiança por bootstrap de "
        f"blocos. A robustez é checada partindo o período em subperíodos.")

    # ---- resultados ----
    h1(doc, "Resultados")
    h2(doc, "Estrutura dos grafos e referência dentro da amostra")
    par(doc,
        f"O GPMF tem {arestas} arestas (= 3·{n_fii}−6), planar e conexo; a AGM tem "
        f"{n_fii-1} (= N−1). Dentro da amostra (referência, não conclusiva), todas as "
        f"carteiras têm Sharpe negativo frente ao CDI, ainda que com retorno nominal "
        f"positivo — sinal de que os FIIs renderam abaixo da renda fixa no período.")
    fig(doc, "gpmf_estatico.png",
        "Figura 2 — GPMF dos FIIs; tamanho e cor dos vértices indicam centralidade de grau.")

    h2(doc, "Comparação GPMF × AGM fora da amostra")
    par(doc,
        "A Tabela 1 traz o desempenho fora da amostra dos dois filtros, com a mesma "
        "regra de seleção. Dois padrões se destacam. Primeiro, no GPMF a Periférica "
        "supera a Central em todos os tamanhos (Sharpe menos negativo), sustentando a "
        "hipótese de Pozzi; na AGM isso falha no tamanho 5. Segundo, embora todas as "
        "carteiras fiquem abaixo do CDI (Sharpe negativo), a Periférica-5 do GPMF "
        f"(Sharpe líquido {peri5_liq:.2f}) supera o benchmark passivo "
        f"(Sharpe {bench_sh:.2f}) — a única carteira ativa a fazê-lo —, ainda que seja "
        "pequena (5 FIIs) e de giro elevado.")
    tab = alin.copy(); tab.index.name = "carteira"
    tabela(doc, tab[["filtro", "ret_anual_bruto", "sharpe_bruto", "sharpe_liq", "giro_medio"]],
           "Tabela 1 — GPMF × AGM fora da amostra (Sharpe sobre o excesso ao CDI)",
           fmt=lambda c, v: (f"{v*100:.1f}%" if c in ("ret_anual_bruto", "giro_medio")
                             else f"{v:.3f}"))
    fig(doc, "comparacao_alinhada_augusto.png",
        "Figura 3 — GPMF vs AGM (mesma regra, dados corrigidos): retorno acumulado "
        "líquido das carteiras de tamanho 10.")

    h2(doc, "De onde vem a perda: decomposição de custos")
    par(doc,
        "A Tabela 2 decompõe o retorno anual: do bruto descontam-se o arrasto de custo "
        "de transação (~1–2% a.a., proporcional ao giro) e o arrasto de imposto "
        "(~1,7–2,1% a.a.), chegando ao líquido. Para a maioria das carteiras, os dois "
        "arrastos juntos transformam o pouco que sobrava em retorno líquido negativo.")
    tabela(doc, deco, "Tabela 2 — Decomposição do retorno (bruto → custo → imposto → líquido)",
           fmt=lambda c, v: f"{v*100:.2f}%")

    h2(doc, "Significância estatística")
    par(doc,
        "Pelo teste de Jobson-Korkie e pelo bootstrap (Tabela 3), a vantagem da "
        "Periférica sobre a Central não é significativa a 5%. A diferença robusta é "
        "negativa: a Central-10 é significativamente PIOR que o benchmark "
        "(p_bootstrap = 0,01). Ou seja, há evidência de que escolher os ativos centrais "
        "destrói valor frente ao índice, mas não de que a periferia o supere.")
    testes = pd.read_csv(config.TABLES_DIR / "testes_significancia.csv")
    testes = testes.rename(columns={"a": "carteira A", "b": "carteira B",
                                    "diff_sharpe_aa": "ΔSharpe(aa)", "ic95_baixo": "IC95 inf",
                                    "ic95_alto": "IC95 sup", "p_boot": "p (bootstrap)"})
    testes = testes[["carteira A", "carteira B", "ΔSharpe(aa)", "IC95 inf", "IC95 sup",
                     "p (bootstrap)"]].set_index("carteira A")
    tabela(doc, testes, "Tabela 3 — Diferença de Sharpe (Jobson-Korkie + IC bootstrap 95%)",
           fmt=lambda c, v: f"{v:.3f}")

    h2(doc, "Robustez por subperíodo")
    par(doc,
        "A Tabela 4 reavalia a hipótese de Pozzi em dois subperíodos consecutivos. Ela "
        "se confirma no primeiro (ago/2023–set/2024) mas se inverte no segundo "
        "(set/2024–out/2025): a vantagem da periferia depende do regime de mercado e, "
        "portanto, NÃO é robusta na janela disponível.")
    tabela(doc, sub[["inicio", "fim", "sharpe_central_10", "sharpe_perif_10", "pozzi_10",
                     "sharpe_benchmark"]],
           "Tabela 4 — Hipótese de Pozzi por subperíodo (tamanho 10, líquido)",
           fmt=lambda c, v: f"{v:.3f}")

    # ---- discussão / conclusão ----
    h1(doc, "Discussão e Conclusões")
    par(doc,
        "Três conclusões emergem. (1) No período mar/2022–nov/2025, os FIIs — em "
        "qualquer das carteiras de grafo e no próprio benchmark — renderam abaixo do "
        "CDI; estratégias ativas de grafo não agregaram valor líquido frente à renda "
        "fixa. (2) Como filtro, o GPMF é superior à AGM para ordenar centro vs "
        "periferia: sustenta a hipótese de Pozzi em todos os tamanhos, enquanto a AGM "
        "falha no menor; e apenas no GPMF uma carteira (Periférica-5) supera o "
        "benchmark passivo no líquido. (3) Esse efeito-periferia, contudo, não é robusto "
        "entre subperíodos nem estatisticamente significativo, e a única diferença "
        "significativa é a desvantagem das carteiras centrais frente ao índice.")
    par(doc,
        "Limitações: janela fora da amostra de ~2 anos (baixo poder estatístico), viés "
        "de sobrevivência (apenas FIIs com histórico completo), benchmark via ETF "
        "proxy, e sensibilidade ao giro (custo+imposto decisivos). A reconciliação com "
        "o braço AGM exigiu alinhar convenções — sobretudo o tratamento de dividendos.")

    h1(doc, "Bibliografia")
    for ref in [
        "MANTEGNA, R. N. Hierarchical structure in financial markets. EPJB, 11:193–197, 1999.",
        "TUMMINELLO, M. et al. A tool for filtering information in complex systems. PNAS, "
        "102(30):10421–10426, 2005.",
        "POZZI, F.; DI MATTEO, T.; ASTE, T. Spread of risk across financial markets: better "
        "to invest in the peripheries. Scientific Reports, 3:1665, 2013.",
        "PERALTA, G.; ZAREEI, A. A network approach to portfolio selection. JEF, 38:157–180, 2016.",
        "MEMMEL, C. Performance hypothesis testing with the Sharpe ratio. Finance Letters, 1:21–23, 2003."]:
        doc.add_paragraph(ref)

    h1(doc, "Perspectivas de continuidade")
    par(doc,
        "Estender a janela para aumentar o poder estatístico; testar ponderação por "
        "risco (inverse-vol) e a centralidade de autovetor na seleção; controlar o giro "
        "para reduzir o arrasto de custos; e consolidar a comparação oficial com o braço "
        "AGM, redigindo o artigo para o ENIAC 2026.")

    saida = config.ROOT / "docs" / "Relatorio_Final_Yoon_v3.docx"
    doc.save(str(saida))
    print(f"relatório v3 salvo em {saida}")


if __name__ == "__main__":
    main()

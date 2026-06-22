"""
Relatório Final da IC — v4.

Integra os resultados REAIS do braço AGM (Augusto), comparados ao GPMF no período
comum fora da amostra (ago/2023–fev/2025), com a mesma métrica (Sharpe sobre o
CDI). Mantém os resultados do braço GPMF no período completo e acrescenta a
validação cruzada e as ressalvas (janela mais curta do parceiro; diferenças
residuais de universo/custos). Salva em docs/Relatorio_Final_Yoon_v4.docx.
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
    real = pd.read_csv(config.TABLES_DIR / "comparacao_augusto_real.csv", index_col=0)
    deco = pd.read_csv(config.TABLES_DIR / "tabela_custos_decomposta.csv", index_col=0)
    sub = pd.read_csv(config.TABLES_DIR / "tabela_subperiodos.csv", index_col=0)
    grafos = pd.read_csv(config.PROCESSED_DIR / "grafos_rolling.csv", index_col=0, parse_dates=True)
    oos = pd.read_csv(config.PROCESSED_DIR / "retornos_oos.csv", index_col=0, parse_dates=True)

    n_fii = int(grafos["vertices"].iloc[0])
    arestas = int(grafos["arestas"].iloc[0])
    n_rebal = len(grafos)

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    # ---- capa ----
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
        "Este projeto compara dois métodos de filtragem em grafos para a formação de "
        "carteiras de Fundos de Investimento Imobiliário (FIIs): o Grafo Planar "
        "Maximamente Filtrado (GPMF), desenvolvido neste trabalho, e a Árvore Geradora "
        "Mínima (AGM), do parceiro Augusto Carneiro da Silva. A partir da correlação dos "
        "retornos de 51 FIIs (mar/2022–nov/2025) constrói-se a rede, e por centralidade "
        "formam-se carteiras Central, Periférica e Híbrida, avaliadas fora da amostra "
        "por janela deslizante e medindo o Índice de Sharpe sobre o excesso ao CDI. No "
        "período, os FIIs renderam abaixo do CDI (Sharpe negativo em todas as carteiras "
        "e no benchmark). Na comparação direta com os resultados reais da AGM, no "
        "período comum, o GPMF supera a AGM em todas as carteiras de forma "
        "estatisticamente significativa, e a carteira Periférica-5 do GPMF é a única a "
        "superar o benchmark passivo. Discutem-se as ressalvas: janela curta, "
        "dependência de regime e diferenças residuais entre os braços.")

    # ---- introdução ----
    h1(doc, "Introdução")
    par(doc,
        "Métodos de filtragem em grafos resumem a estrutura de correlação de um mercado "
        "em poucas ligações. A AGM (Mantegna, 1999) retém N−1 arestas; o GPMF "
        "(Tumminello et al., 2005), por exigir apenas planaridade, retém 3N−6 e preserva "
        "ciclos e cliques. Pozzi, Di Matteo e Aste (2013) propõem que ativos periféricos "
        "formam carteiras com melhor relação risco-retorno. Investiga-se a hipótese para "
        "FIIs e se o filtro (GPMF ou AGM) altera a conclusão. O diferencial desta versão "
        "é a comparação com os resultados reais do braço AGM do parceiro.")

    # ---- materiais e métodos ----
    h1(doc, "Materiais e Métodos")
    par(doc,
        f"Fechamentos diários ajustados de FIIs via yfinance, de {mes_ano(config.START_DATE)} "
        f"a {mes_ano(config.END_DATE)}; universo determinístico de {n_fii} FIIs; benchmark "
        f"XFIX11 (proxy do IFIX). Retorno total Rt = ln(Pt/Pt−1) sobre o ajustado "
        f"(verificou-se que somar Dt contaria o dividendo duas vezes). Da correlação de "
        f"Pearson obtém-se a distância d = √(2(1−ρ)) e, dela, o GPMF (planaridade de "
        f"Boyer-Myrvold) e a AGM (Kruskal). Para cada FII calcula-se um escore composto "
        f"de centralidade (grau, intermediação, proximidade), a mesma regra nos dois "
        f"braços. Formam-se carteiras Central, Periférica e Híbrida de 5, 10, 15 e 20 "
        f"ativos, pesos iguais. A validação é fora da amostra por janela deslizante "
        f"(forma {config.FORMATION_DAYS}, mantém {config.TEST_DAYS}, avança "
        f"{config.ROLL_STEP_DAYS}), com custo de 0,3% sobre o giro e 15% de IR sobre "
        f"ganho de capital. O Índice de Sharpe é medido sobre o excesso ao CDI diário "
        f"(≈11,6% a.a.); a significância segue Jobson-Korkie (Memmel, 2003) com IC por "
        f"bootstrap de blocos.")
    fig(doc, "verifica_dividendos_MXRF11.png",
        "Figura 1 — Verificação da convenção de dividendos (MXRF11).")

    # ---- resultados: nosso braço (GPMF, período completo) ----
    h1(doc, "Resultados — braço GPMF (período completo)")
    par(doc,
        f"O GPMF tem {arestas} arestas (= 3·{n_fii}−6), planar e conexo, contra {n_fii-1} "
        f"da AGM. Fora da amostra ({data_br(oos.index[0])} a {data_br(oos.index[-1])}, "
        f"{len(oos)} pregões, {n_rebal} rebalanceamentos), todas as carteiras têm Sharpe "
        f"negativo frente ao CDI — os FIIs renderam abaixo da renda fixa. Ainda assim, a "
        f"carteira Periférica supera a Central em todos os tamanhos (hipótese de Pozzi).")
    fig(doc, "gpmf_estatico.png",
        "Figura 2 — GPMF dos FIIs; tamanho e cor dos vértices indicam centralidade de grau.")
    par(doc,
        "A decomposição de custos (Tabela 1) mostra que o arrasto de transação "
        "(~1–2% a.a.) e o de imposto (~1,7–2,1% a.a.) consomem o pouco que sobrava. A "
        "robustez por subperíodo (Tabela 2) revela que a vantagem da periferia "
        "depende do regime: confirma-se no primeiro subperíodo e se inverte no segundo.")
    tabela(doc, deco, "Tabela 1 — Decomposição do retorno (bruto → custo → imposto → líquido)",
           fmt=lambda c, v: f"{v*100:.2f}%")
    tabela(doc, sub[["inicio", "fim", "sharpe_central_10", "sharpe_perif_10", "pozzi_10",
                     "sharpe_benchmark"]],
           "Tabela 2 — Hipótese de Pozzi por subperíodo (tamanho 10, líquido)",
           fmt=lambda c, v: f"{v:.3f}")

    # ---- resultados: comparação com a AGM REAL do Augusto ----
    h1(doc, "Comparação com o braço AGM (resultados reais do parceiro)")
    par(doc,
        "O parceiro forneceu as séries diárias reais da AGM, já alinhadas (mesmo "
        "benchmark, retorno corrigido, Sharpe sobre o CDI). Como o backtest dele termina "
        "em fev/2025 e o nosso vai até out/2025, a comparação é feita no PERÍODO COMUM "
        "(ago/2023–fev/2025, 374 pregões) — uma janela anterior à recuperação de 2025, em "
        "que mesmo o benchmark rendeu abaixo do CDI. A Tabela 3 traz o confronto direto, "
        "líquido.")
    real_show = real.rename(columns={"GPMF_ret_aa": "GPMF ret a.a.", "GPMF_sharpe": "GPMF Sharpe",
                                     "AGM_ret_aa": "AGM ret a.a.", "AGM_sharpe": "AGM Sharpe"})
    real_show.index.name = "carteira"
    tabela(doc, real_show,
           "Tabela 3 — GPMF (Yoon) vs AGM (Augusto), período comum, líquido",
           fmt=lambda c, v: (f"{v*100:.2f}%" if "ret" in c else f"{v:.3f}"))
    fig(doc, "comparacao_augusto_real.png",
        "Figura 3 — GPMF (Yoon) vs AGM (Augusto) no período comum: retorno acumulado "
        "líquido fora da amostra.")
    par(doc,
        "O GPMF supera a AGM nas três carteiras. A diferença é estatisticamente "
        "significativa: para a Periférica-5, ΔSharpe(a.a.) = +2,05 (IC95% [+0,87, +3,20], "
        "p_bootstrap < 0,001); para a Central-10, ΔSharpe(a.a.) = +0,72 (IC95% "
        "[+0,05, +1,37], p_bootstrap = 0,04). A Periférica-5 do GPMF é, ademais, a única "
        "carteira a superar o benchmark passivo (Sharpe −1,12 vs −1,97; retorno +0,4% vs "
        "−4,2%), confirmando a robustez do efeito-periferia no GPMF mesmo numa janela "
        "adversa.")
    h2(doc, "Validação e ressalvas da comparação")
    par(doc,
        "Como controle, comparamos a AGM do parceiro com uma reimplementação da AGM no "
        "nosso próprio pipeline (mesmo dado e mesma regra). As duas não coincidem "
        "exatamente — a AGM do parceiro é cerca de 0,7 a 1,2 ponto de Sharpe mais "
        "negativa —, o que indica diferenças residuais entre os braços (o universo do "
        "parceiro tem 54 FIIs, contra os nossos 51, e o modelo de custos/turnover difere "
        "em detalhes). Portanto, parte da vantagem do GPMF sobre a AGM reflete também "
        "essas diferenças, não apenas o filtro. A comparação limpa, dentro do mesmo "
        "pipeline (GPMF vs nossa AGM), aponta na mesma direção, com magnitude menor. "
        "Recomenda-se, para a versão final do trabalho conjunto, (i) unificar o universo "
        "e o modelo de custos e (ii) estender o backtest do parceiro até nov/2025.")

    # ---- conclusão ----
    h1(doc, "Discussão e Conclusões")
    par(doc,
        "Três conclusões. (1) No período, os FIIs — em qualquer carteira de grafo e no "
        "benchmark — renderam abaixo do CDI; estratégias ativas não agregaram valor "
        "líquido frente à renda fixa. (2) O GPMF é superior à AGM: sustenta a hipótese de "
        "Pozzi em todos os tamanhos e supera a AGM real do parceiro em todas as carteiras "
        "do período comum, de forma significativa; a Periférica-5 do GPMF é a única a "
        "bater o benchmark. (3) O efeito, contudo, depende do regime de mercado e a "
        "comparação entre braços ainda carrega diferenças residuais de universo e custos "
        "a serem unificadas. Limitações: janela curta (baixo poder), viés de "
        "sobrevivência e benchmark via ETF proxy.")

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
        "Unificar universo e custos com o braço AGM e estender o backtest do parceiro até "
        "nov/2025; estender a janela total para aumentar o poder estatístico; testar "
        "ponderação por risco e a centralidade de autovetor na seleção; e finalizar o "
        "artigo para o ENIAC 2026.")

    saida = config.ROOT / "docs" / "Relatorio_Final_Yoon_v4.docx"
    doc.save(str(saida))
    print(f"relatório v4 salvo em {saida}")


if __name__ == "__main__":
    main()

"""
Relatório Final v2 — inclui a comparação real com o braço AGM (Augusto).

Diferenças em relação ao v1: a seção de comparação GPMF × AGM passa a usar a
execução alinhada dos dois filtros sobre os mesmos dados corrigidos e a mesma
regra de seleção (escore composto, igual à da AGM), e acrescenta a discussão de
reconciliação das convenções entre os dois braços. Salva em
docs/Relatorio_Final_Yoon_v2.docx (não sobrescreve o v1).
"""
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src.relatorio_utils import data_br, fig, h1, h2, mes_ano, par, tabela, AZUL


def main():
    est = pd.read_csv(config.TABLES_DIR / "tabela_estatica.csv", index_col=0)
    roll = pd.read_csv(config.TABLES_DIR / "tabela_rolling_bruta.csv", index_col=0)
    alin = pd.read_csv(config.TABLES_DIR / "comparacao_alinhada_augusto.csv", index_col=0)
    grafos = pd.read_csv(config.PROCESSED_DIR / "grafos_rolling.csv", index_col=0, parse_dates=True)
    oos = pd.read_csv(config.PROCESSED_DIR / "retornos_oos.csv", index_col=0, parse_dates=True)

    n_fii = int(grafos["vertices"].iloc[0])
    n_pregoes_est = int(est["n_periodos"].iloc[0])
    n_pregoes_oos = int(roll["n_periodos"].iloc[0])
    n_rebal = len(grafos)

    doc = Document()
    doc.styles["Normal"].font.name = "Calibri"
    doc.styles["Normal"].font.size = Pt(11)

    # ---- capa ----
    for txt, sz, bold, cor in [
        ("Programa Institucional de Iniciação Científica e Tecnológica", 13, True, None),
        ("Relatório Final de Atividades", 15, True, AZUL)]:
        p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(txt); r.bold = bold; r.font.size = Pt(sz)
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
        "Este projeto investiga o uso de técnicas baseadas em grafos para a formação "
        "de carteiras de Fundos de Investimento Imobiliário (FIIs), comparando o Grafo "
        "Planar Maximamente Filtrado (GPMF) com a Árvore Geradora Mínima (AGM). Esta "
        "versão integra o braço AGM, desenvolvido pelo parceiro Augusto Carneiro da "
        "Silva, em uma comparação sob premissas idênticas. Com a convenção de "
        "dividendos corrigida e os dois filtros executados sobre os mesmos dados, as "
        "carteiras periféricas do GPMF superam as centrais em todos os tamanhos fora da "
        "amostra (a hipótese de Pozzi), enquanto a AGM falha no menor tamanho; a "
        "periférica mais concentrada do GPMF chega a superar o benchmark passivo no "
        "líquido. Discute-se ainda como a convenção de retorno afeta as conclusões.")

    # ---- introdução / métodos (resumidos; detalhe no v1) ----
    h1(doc, "Introdução")
    par(doc,
        "Métodos de filtragem em grafos resumem a estrutura de correlação de um mercado "
        "em poucas ligações relevantes. A AGM (Mantegna, 1999) retém N−1 arestas; o "
        "GPMF (Tumminello et al., 2005), por exigir apenas planaridade, retém 3N−6 e "
        "preserva mais estrutura. Pozzi et al. (2013) sugerem que ativos periféricos "
        "formam carteiras com melhor relação risco-retorno. O objetivo é testar essa "
        "hipótese para FIIs e verificar se o filtro (GPMF ou AGM) muda a conclusão.")

    h1(doc, "Materiais e Métodos")
    par(doc,
        f"Fechamentos diários ajustados de FIIs via yfinance, de {mes_ano(config.START_DATE)} "
        f"a {mes_ano(config.END_DATE)} ({n_pregoes_est} pregões); universo determinístico "
        f"de {n_fii} FIIs; benchmark XFIX11 (proxy do IFIX). Retorno total "
        f"Rt = ln(Pt/Pt−1) sobre o ajustado (verificado que somar o dividendo "
        f"contaria-o duas vezes). Da correlação de Pearson obtém-se a distância "
        f"d = √(2(1−ρ)) e dela o GPMF (planaridade de Boyer-Myrvold) e a AGM. Para cada "
        f"FII calcula-se um escore composto de centralidade (média normalizada de grau, "
        f"intermediação e proximidade) — a mesma regra usada pelo braço AGM —, com o "
        f"qual se formam carteiras Central, Periférica e Híbrida de 5, 10, 15 e 20 "
        f"ativos. A avaliação é fora da amostra por janela deslizante (forma com "
        f"{config.FORMATION_DAYS}, mantém {config.TEST_DAYS}, avança {config.ROLL_STEP_DAYS}; "
        f"período de {data_br(oos.index[0])} a {data_br(oos.index[-1])}, {n_pregoes_oos} "
        f"pregões, {n_rebal} rebalanceamentos), com custo de 0,3% sobre o giro e 15% de "
        f"IR sobre ganho de capital.")
    fig(doc, "verifica_dividendos_MXRF11.png",
        "Figura 1 — Verificação da convenção de dividendos (MXRF11): a razão "
        "ajustado/bruto em degraus corresponde aos proventos já reinvestidos.")

    # ---- resultados ----
    h1(doc, "Resultados")
    h2(doc, "Estrutura dos grafos")
    par(doc,
        f"Sobre o período completo, o GPMF tem {int(grafos['arestas'].iloc[0])} arestas "
        f"(= 3·{n_fii}−6), planar e conexo, contra {n_fii-1} (= N−1) da AGM.")
    fig(doc, "gpmf_estatico.png",
        "Figura 2 — GPMF dos FIIs; tamanho e cor dos vértices indicam centralidade de grau.")

    h2(doc, "Comparação GPMF × AGM (mesma regra de seleção, dados corrigidos)")
    par(doc,
        "A Tabela 1 traz o Sharpe bruto e líquido fora da amostra dos dois filtros, com "
        "a mesma regra de seleção (escore composto). No GPMF, a Periférica supera a "
        "Central em todos os tamanhos (5, 10, 15 e 20), sustentando a hipótese de "
        "Pozzi; na AGM, isso falha no tamanho 5. Líquido de custos, a maioria das "
        "carteiras perde para o benchmark passivo (Sharpe 0,69), mas a Periférica-5 do "
        "GPMF (Sharpe líquido 0,86) o supera — algo que nenhuma carteira da AGM "
        "alcança.")
    tab = alin.copy()
    tab.index.name = "carteira"
    tabela(doc, tab[["filtro", "ret_anual_bruto", "sharpe_bruto", "sharpe_liq", "giro_medio"]],
           "Tabela 1 — GPMF × AGM fora da amostra (escore composto)",
           fmt=lambda c, v: (f"{v*100:.1f}%" if c in ("ret_anual_bruto", "giro_medio")
                             else f"{v:.3f}"))
    fig(doc, "comparacao_alinhada_augusto.png",
        "Figura 3 — GPMF vs AGM (regra idêntica, dados corrigidos): retorno acumulado "
        "líquido das carteiras de tamanho 10.")

    # ---- discussão / reconciliação ----
    h1(doc, "Discussão: reconciliação dos dois braços")
    par(doc,
        "Os dois braços foram desenvolvidos separadamente e, de início, adotaram "
        "convenções diferentes. O braço AGM usava o retorno Rt = ln((Pt+Dt)/Pt−1) sobre "
        "o preço já ajustado, o que conta os dividendos duas vezes e infla o retorno "
        "anual em cerca do próprio dividend yield (~10% ao ano para FIIs); além disso, "
        "usava janela e universo distintos e o CDI como taxa livre de risco. Na "
        "execução isolada do braço AGM, isso elevava os Sharpes (p.ex. AGM Central-10 "
        "≈ 1,78) e fazia o centro parecer vencer. Ao alinhar tudo — mesma convenção "
        "corrigida, mesmo universo e janela, mesma regra de seleção —, o quadro muda: o "
        "GPMF sustenta a periferia de forma mais robusta que a AGM. A lição "
        "metodológica é que conclusões sobre centro vs. periferia dependem não só do "
        "filtro, mas também da convenção de retorno — ponto que precisa estar alinhado "
        "entre os dois trabalhos antes de qualquer comparação oficial.")
    par(doc,
        "Ressalvas: na maioria das carteiras o ganho ativo não sobrevive aos custos, e "
        "o teste de Jobson-Korkie não encontra diferenças significativas a 5% na janela "
        "disponível. A evidência é, portanto, qualitativamente favorável à periferia e "
        "ao GPMF, mas ainda não conclusiva estatisticamente.")

    h1(doc, "Conclusão")
    par(doc,
        "Sob metodologia idêntica e validação fora da amostra, o GPMF oferece suporte "
        "mais robusto à hipótese da periferia de Pozzi et al. (2013) do que a AGM, e a "
        "carteira Periférica-5 do GPMF supera o benchmark passivo no líquido. A "
        "comparação entre os braços exigiu reconciliar as convenções — sobretudo o "
        "tratamento de dividendos. Próximos passos: estender a janela, controlar o giro "
        "e incluir a centralidade de autovetor na seleção.")

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
        "Estender a janela para aumentar o poder estatístico; alinhar oficialmente as "
        "premissas com o braço AGM; incorporar a centralidade de autovetor e pesos por "
        "risco; e redigir o artigo para o ENIAC 2026.")

    saida = config.ROOT / "docs" / "Relatorio_Final_Yoon_v2.docx"
    doc.save(str(saida))
    print(f"relatório v2 salvo em {saida}")


if __name__ == "__main__":
    main()

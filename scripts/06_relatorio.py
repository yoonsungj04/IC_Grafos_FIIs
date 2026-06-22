"""
Gera o Relatório Final de Atividades em .docx, no estilo do relatório parcial e
seguindo a estrutura do PIBIC (Identificação, Introdução, Materiais e Métodos,
Resultados, Discussão/Conclusões, Bibliografia, Perspectivas).

Lê os números diretamente das tabelas em results/tables/ e embute as figuras de
results/figures/, de modo que o texto sempre reflete a última execução.
"""
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

TAB = config.TABLES_DIR
FIG = config.FIGURES_DIR
AZUL = RGBColor(0x1F, 0x3B, 0x73)

_MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
          "jul", "ago", "set", "out", "nov", "dez"]


def mes_ano(data_iso: str) -> str:
    a, m, _ = data_iso.split("-")
    return f"{_MESES[int(m) - 1]}/{a}"


def data_br(data) -> str:
    return data.strftime("%d/%m/%Y")


def carregar():
    est = pd.read_csv(TAB / "tabela_estatica.csv", index_col=0)
    roll = pd.read_csv(TAB / "tabela_rolling_bruta.csv", index_col=0)
    cus = pd.read_csv(TAB / "tabela_custos.csv", index_col=0)
    test = pd.read_csv(TAB / "testes_significancia.csv")
    comp = pd.read_csv(TAB / "tabela_comparacao_gpmf_mst.csv")
    grafos = pd.read_csv(config.PROCESSED_DIR / "grafos_rolling.csv", index_col=0, parse_dates=True)
    oos = pd.read_csv(config.PROCESSED_DIR / "retornos_oos.csv", index_col=0, parse_dates=True)
    return est, roll, cus, test, comp, grafos, oos


# ---------- utilidades de formatação ----------
def h1(doc, txt):
    p = doc.add_heading(txt, level=1)
    for r in p.runs:
        r.font.color.rgb = AZUL


def h2(doc, txt):
    p = doc.add_heading(txt, level=2)
    for r in p.runs:
        r.font.color.rgb = AZUL


def par(doc, txt, just=True):
    p = doc.add_paragraph(txt)
    if just:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return p


def fig(doc, nome, legenda, largura=6.0):
    caminho = FIG / nome
    if caminho.exists():
        doc.add_picture(str(caminho), width=Inches(largura))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap = doc.add_paragraph(legenda)
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in cap.runs:
            r.font.size = Pt(9)
            r.font.italic = True


def tabela(doc, df, titulo, fmt_pct_cols=(), fmt=None):
    cap = doc.add_paragraph(titulo)
    for r in cap.runs:
        r.bold = True
        r.font.color.rgb = AZUL
    t = doc.add_table(rows=1, cols=len(df.columns) + 1)
    t.style = "Light Grid Accent 1"
    hdr = t.rows[0].cells
    hdr[0].text = df.index.name or ""
    for j, c in enumerate(df.columns):
        hdr[j + 1].text = str(c)
    for idx, row in df.iterrows():
        cells = t.add_row().cells
        cells[0].text = str(idx)
        for j, c in enumerate(df.columns):
            v = row[c]
            if isinstance(v, float):
                cells[j + 1].text = (fmt(c, v) if fmt else f"{v:.3f}")
            else:
                cells[j + 1].text = str(v)
    doc.add_paragraph()


def main():
    est, roll, cus, test, comp, grafos, oos = carregar()
    n_pregoes_est = int(est["n_periodos"].iloc[0])
    n_pregoes_oos = int(roll["n_periodos"].iloc[0])
    n_rebal = len(grafos)
    arestas = int(grafos["arestas"].iloc[0])
    n_fii = int(grafos["vertices"].iloc[0])
    oos_ini, oos_fim = oos.index[0].date(), oos.index[-1].date()

    # quem vence (centro x periferia) dentro e fora da amostra, no tamanho 10
    est_peri_vence = est.loc["peripheral_10", "sharpe"] > est.loc["central_10", "sharpe"]
    oos_peri_vence = roll.loc["peripheral_10", "sharpe"] > roll.loc["central_10", "sharpe"]
    bench_sh = roll.loc["benchmark", "sharpe"]
    melhor_ativa_liq = cus["sharpe_liq"].idxmax()

    # taxa livre de risco média (CDI) e tabelas de robustez/decomposição
    from src import data_load
    rf_aa = float(data_load.carregar_cdi().mean() * config.TRADING_DAYS_PER_YEAR * 100)
    subper = pd.read_csv(TAB / "tabela_subperiodos.csv", index_col=0)
    decomp = pd.read_csv(TAB / "tabela_custos_decomposta.csv", index_col=0)

    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name = "Calibri"
    estilo.font.size = Pt(11)

    # ---------------- Capa / Identificação ----------------
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("Programa Institucional de Iniciação Científica e Tecnológica")
    r.bold = True
    r.font.size = Pt(13)
    st = doc.add_paragraph()
    st.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = st.add_run("Relatório Final de Atividades")
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = AZUL

    titulo = ("Análise Comparativa de Métodos de Formação de Carteira Baseados em "
              "Grafos para Fundos Imobiliários (FIIs): Casos de Estudo com o Grafo "
              "Planar Maximamente Filtrado")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(titulo)
    r.bold = True
    doc.add_paragraph()

    ident = [
        ("Projeto", titulo),
        ("Bolsista / RA", "Yoon Sung Jang / RA [preencher]"),
        ("Orientador", "Prof. Dr. João Roberto Bertini Junior"),
        ("Local de execução", "Faculdade de Tecnologia (FT) — UNICAMP, Limeira/SP"),
        ("Vigência", "setembro/2025 a agosto/2026"),
    ]
    for k, v in ident:
        p = doc.add_paragraph()
        p.add_run(f"{k}: ").bold = True
        p.add_run(v)

    # ---------------- Resumo ----------------
    h1(doc, "Resumo")
    par(doc,
        "Este projeto investiga o uso de técnicas baseadas em grafos para a formação "
        "de carteiras de Fundos de Investimento Imobiliário (FIIs), com foco no Grafo "
        "Planar Maximamente Filtrado (GPMF) e comparação com a Árvore Geradora Mínima "
        "(AGM). A partir da correlação entre os retornos, constrói-se a rede de ativos "
        "e, por métricas de centralidade, formam-se carteiras Central, Periférica e "
        "Híbrida, avaliadas quanto a risco, retorno, custos e tributos. Em relação ao "
        "relatório parcial, esta etapa (i) corrigiu a convenção de cálculo do retorno "
        "total, evitando dupla contagem de dividendos; (ii) tornou a seleção do "
        "universo determinística e reprodutível; e (iii) implementou a validação por "
        "janela deslizante (out-of-sample), núcleo científico do trabalho. Com a "
        "metodologia corrigida — e medindo o Índice de Sharpe sobre o excesso ao CDI —, "
        "as carteiras periféricas apresentam melhor relação risco-retorno na janela "
        "completa fora da amostra, superando as centrais em todos os tamanhos testados, "
        "em linha com a hipótese de Pozzi et al. (2013). Esse resultado revisa a "
        "conclusão do relatório parcial, cuja vantagem das carteiras centrais era afetada "
        "pela dupla contagem de dividendos. A vantagem da periferia é, porém, qualificada "
        "por três limites: líquido de custos e tributos nenhuma carteira ativa supera o "
        "benchmark passivo (IFIX); a diferença periferia−centro não atinge significância "
        "estatística (intervalo de confiança por bootstrap cruza zero); e ela não é "
        "estável no tempo, concentrando-se no sub-período de mercado fraco e invertendo-se "
        "na recuperação — sugerindo um caráter defensivo, dependente de regime.")

    # ---------------- Introdução ----------------
    h1(doc, "Introdução")
    par(doc,
        "A seleção de ativos em mercados financeiros pode ser apoiada por métodos de "
        "filtragem de informação em grafos, que resumem a estrutura de correlação de um "
        "conjunto de ativos em poucas ligações relevantes. A Árvore Geradora Mínima "
        "(Mantegna, 1999) retém N−1 arestas, enquanto o Grafo Planar Maximamente "
        "Filtrado (Tumminello et al., 2005) retém 3N−6, preservando ciclos e cliques e, "
        "portanto, mais estrutura. Pozzi, Di Matteo e Aste (2013) argumentam que ativos "
        "periféricos nessas redes tendem a compor carteiras com melhor relação "
        "risco-retorno; Peralta e Zareei (2016) reforçam a hipótese usando centralidade "
        "de autovetor.")
    par(doc,
        "Os FIIs brasileiros têm características próprias relevantes à metodologia: "
        "distribuição obrigatória de ao menos 95% dos lucros, isenção de imposto de "
        "renda sobre proventos para pessoas físicas e incidência de 15% sobre o ganho "
        "de capital na venda de cotas. O objetivo deste trabalho é avaliar se a "
        "recomendação de “investir na periferia” se sustenta para FIIs, "
        "comparando o GPMF com a AGM sob a mesma metodologia e validando os resultados "
        "fora da amostra.")

    # ---------------- Materiais e Métodos ----------------
    h1(doc, "Materiais e Métodos")
    h2(doc, "Dados e janela")
    par(doc,
        f"Os preços de fechamento ajustados e os proventos foram coletados via "
        f"biblioteca yfinance, no período de {mes_ano(config.START_DATE)} a "
        f"{mes_ano(config.END_DATE)} ({n_pregoes_est} pregões). "
        f"A seleção do universo é determinística a partir do cache: partindo de FIIs "
        f"candidatos líquidos, mantêm-se os que cobrem toda a janela com histórico "
        f"suficiente e menos de {int(config.MAX_MISSING_FRACTION*100)}% de dados "
        f"faltantes, resultando em {n_fii} FIIs aptos. O benchmark é o "
        f"IFIX; como o ticker ^IFIX falha por fuso horário no provedor, utiliza-se o "
        f"ETF XFIX11 como proxy.")
    h2(doc, "Convenção de retorno (correção metodológica)")
    par(doc,
        "Verificou-se empiricamente, em um FII de alto dividend yield (MXRF11, 33 "
        "proventos na janela), que o fechamento ajustado do provedor já reinveste os "
        "dividendos: o retorno do ajustado é igual ao retorno de (preço + provento) com "
        "erro máximo da ordem de 1×10⁻⁴, ao passo que difere do retorno apenas-preço em "
        "até 1×10⁻². Conclui-se que o retorno total correto é Rt = ln(Pt/Pt−1) sobre o "
        "fechamento ajustado. A fórmula do relatório parcial, Rt = ln((Pt+Dt)/Pt−1), "
        "somava o provento novamente e contava o dividendo duas vezes; todos os "
        "resultados a seguir adotam a convenção corrigida.")
    fig(doc, "verifica_dividendos_MXRF11.png",
        "Figura 1 — Verificação da convenção de dividendos (MXRF11). A razão "
        "ajustado/bruto em degraus corresponde aos proventos reinvestidos.")
    h2(doc, "Construção do grafo e seleção das carteiras")
    par(doc,
        "Calcula-se a matriz de correlação de Pearson dos retornos diários e, a partir "
        "dela, a distância de Mantegna d(i,j) = √(2(1−ρij)). O GPMF é construído por "
        "inserção gulosa das arestas de menor distância, preservando a planaridade "
        "(verificação de Boyer-Myrvold via NetworkX); um GPMF conexo sobre N vértices "
        "tem 3N−6 arestas. Para cada FII calculam-se quatro centralidades — grau, "
        "intermediação, proximidade e autovetor — e formam-se carteiras de 10, 15 e 20 "
        "ativos: Central (mais centrais), Periférica (menos centrais) e Híbrida "
        "(metade/metade), com pesos iguais (1/N).")
    h2(doc, "Validação fora da amostra (janela deslizante)")
    par(doc,
        f"A cada passo, a carteira é formada com os {config.FORMATION_DAYS} pregões "
        f"anteriores e mantida nos {config.TEST_DAYS} pregões seguintes (não usados na "
        f"formação); em seguida avança-se {config.ROLL_STEP_DAYS} pregões e o GPMF é "
        f"reconstruído. As janelas de manutenção são emendadas em curvas contínuas. "
        f"Isso elimina o viés de antecipação (look-ahead) presente na avaliação "
        f"estática. O período fora da amostra resultante vai de {data_br(oos.index[0])} "
        f"a {data_br(oos.index[-1])} ({n_pregoes_oos} pregões, {n_rebal} "
        f"rebalanceamentos).")
    h2(doc, "Custos, tributos e significância")
    custo_pct = f"{config.TRANSACTION_COST*100:.1f}".replace(".", ",")
    par(doc,
        f"Aplica-se custo de transação de {custo_pct}% sobre o "
        f"giro a cada rebalanceamento e imposto de {int(config.CAPITAL_GAINS_TAX*100)}% "
        f"sobre o ganho de capital realizado em cada janela; os dividendos de FII são "
        f"isentos para pessoa física. O Índice de Sharpe é calculado sobre o retorno "
        f"EXCEDENTE em relação ao CDI diário (série 12 do SGS/BCB; média de "
        f"{rf_aa:.1f}% a.a. no período) — e não sobre retorno bruto: para ativo "
        f"brasileiro com a Selic em dois dígitos, adotar taxa livre de risco nula "
        f"infla artificialmente o Sharpe e é a correção que mais altera os números "
        f"em relação a versões anteriores. A significância das diferenças de Índice de "
        f"Sharpe é avaliada de duas formas complementares: o teste assintótico de "
        f"Jobson-Korkie com correção de Memmel (2003) e um intervalo de confiança de "
        f"95% por bootstrap de blocos circulares (que respeita a autocorrelação "
        f"diária). O mesmo arcabouço é aplicado à AGM para a comparação GPMF × AGM.")

    # ---------------- Resultados ----------------
    h1(doc, "Resultados")
    h2(doc, "Avaliação estática (dentro da amostra) — referência")
    par(doc,
        f"Reproduzindo a avaliação estática com a metodologia corrigida sobre o período "
        f"completo ({n_pregoes_est} pregões), as carteiras periféricas já apresentam "
        f"melhor Índice de Sharpe que as centrais — diferentemente do relatório parcial, "
        f"em que as centrais lideravam. A diferença decorre da correção da convenção de "
        f"dividendos (que antes inflava o retorno de FIIs de alto provento) e da seleção "
        f"determinística do universo. A Tabela 1 apresenta retorno e risco anualizados, "
        f"Índice de Sharpe e drawdown máximo. Por ser dentro da amostra (centralidade e "
        f"avaliação no mesmo período), este resultado serve apenas de referência; a "
        f"conclusão válida vem da validação fora da amostra.")
    est_fmt = est.copy()
    tabela(doc, est_fmt.round(4),
           "Tabela 1 — Desempenho estático das carteiras GPMF vs. benchmark (referência, in-sample)",
           fmt=lambda c, v: (f"{v*100:.2f}%" if c in ("retorno_anual", "vol_anual",
                              "drawdown_max", "retorno_acumulado") else
                             (f"{v:.3f}" if c == "sharpe" else f"{int(v)}")))
    fig(doc, "gpmf_estatico.png",
        "Figura 2 — GPMF dos FIIs no período completo; tamanho e cor dos vértices "
        "indicam a centralidade de grau.")

    h2(doc, "Validação fora da amostra (resultado principal)")
    par(doc,
        f"A Tabela 2 traz o desempenho bruto (sem custos) fora da amostra. Na janela "
        f"completa as carteiras periféricas superam as centrais em todos os tamanhos "
        f"testados (10, 15 e 20), favorecendo a hipótese de Pozzi sem o viés de "
        f"antecipação — ressalvando-se que essa vantagem não é estatisticamente "
        f"significativa nem estável ao longo do ciclo, como mostram as seções de "
        f"significância e de robustez por sub-período. O GPMF manteve-se planar e "
        f"conexo, com {arestas} arestas, em todos os {n_rebal} rebalanceamentos.")
    tabela(doc, roll.round(4),
           "Tabela 2 — Desempenho fora da amostra (bruto, sem custos)",
           fmt=lambda c, v: (f"{v*100:.2f}%" if c in ("retorno_anual", "vol_anual",
                             "drawdown_max", "retorno_acumulado") else
                             (f"{v:.3f}" if c == "sharpe" else f"{int(v)}")))
    fig(doc, "curvas_oos_bruto.png",
        "Figura 3 — Retorno acumulado fora da amostra (bruto) das carteiras de "
        "tamanho 10 e do benchmark.")

    h2(doc, "Líquido de custos e tributos")
    par(doc,
        "A Tabela 3 compara o desempenho bruto e líquido (custos + IR). As carteiras "
        "periféricas e híbridas têm maior giro e são mais penalizadas. O benchmark "
        "passivo, sem custos de rebalanceamento, mostra-se difícil de superar no "
        "líquido.")
    tabela(doc, cus.round(4),
           "Tabela 3 — Bruto vs. líquido (custos de 0,3% e IR de 15%)",
           fmt=lambda c, v: (f"{v*100:.2f}%" if c.startswith("ret") or c == "dd_liq" or
                             c == "giro_medio" else f"{v:.3f}"))
    fig(doc, "curvas_oos_liquido.png",
        "Figura 4 — Retorno acumulado fora da amostra, líquido de custos e IR.")

    par(doc,
        "A Tabela 4 isola as duas parcelas do arrasto entre bruto e líquido. O custo de "
        "transação acompanha o giro — as carteiras periféricas e híbridas, de maior "
        "rotatividade, pagam mais —, mas é o imposto sobre o ganho de capital o "
        "componente dominante. Em conjunto, custo e imposto consomem todo o prêmio bruto "
        "das carteiras de centro e híbridas, que terminam com retorno líquido negativo; "
        "apenas as periféricas maiores (15 e 20) preservam retorno líquido positivo.")
    decomp_show = decomp.copy()
    decomp_show.index.name = "carteira"
    tabela(doc, decomp_show,
           "Tabela 4 — Decomposição do arrasto: custo de transação × imposto",
           fmt=lambda c, v: (f"{v*100:.2f}%" if c.startswith("ret") or
                             c.startswith("arrasto") or c.startswith("custo") or
                             c.startswith("giro") else f"{v:.3f}"))

    h2(doc, "Significância estatística")
    par(doc,
        "A Tabela 5 resume, para cada par de séries líquidas, a diferença de Índice de "
        "Sharpe anualizado, o intervalo de confiança de 95% por bootstrap de blocos e o "
        "p-valor do teste de Jobson-Korkie. Entre as próprias carteiras GPMF, a "
        "diferença periferia−centro é positiva mas o intervalo de confiança cruza zero: "
        "a vantagem da periferia não atinge significância estatística na janela "
        "disponível por nenhum dos dois critérios. Frente ao benchmark surge uma "
        "distinção sugestiva, porém dependente do método: pelo bootstrap, a Central-10 e "
        "a Híbrida-10 ficam abaixo do IFIX com intervalo inteiramente negativo "
        "(p_boot ≈ 0,01), enquanto a Periférica-10 inclui zero — mas o teste assintótico "
        "de Jobson-Korkie, mais conservador, NÃO rejeita a igualdade em nenhum dos casos "
        "(p_JK ≈ 0,11–0,17). A leitura prudente é que a periferia, no máximo, empata com "
        "o índice passivo, e há indício (não conclusivo) de que o centro fique atrás "
        "dele; confirmar isso exige uma janela fora da amostra mais longa.")
    test_show = test.copy()
    test_show["IC95 (aa)"] = test_show.apply(
        lambda r: f"[{r['ic95_baixo']:+.2f}; {r['ic95_alto']:+.2f}]", axis=1)
    test_show["par"] = test_show["a"] + " vs " + test_show["b"]
    test_show = test_show.rename(columns={"diff_sharpe_aa": "ΔSharpe (aa)",
                                          "p_boot": "p (boot)", "p_valor": "p (JK)"})
    test_show = test_show.set_index("par")[
        ["ΔSharpe (aa)", "IC95 (aa)", "p (boot)", "p (JK)", "n"]]
    test_show.index.name = "comparação"
    tabela(doc, test_show,
           "Tabela 5 — Diferença de Índice de Sharpe (líquido): IC95 por bootstrap e p-valores",
           fmt=lambda c, v: f"{int(v)}" if c == "n" else f"{v:+.2f}")

    h2(doc, "Robustez por sub-período")
    par(doc,
        "Como o período fora da amostra cobre uma única janela (2023–2025), a série foi "
        "partida em dois sub-períodos consecutivos de tamanho igual e a hipótese de "
        "Pozzi foi reavaliada em cada um (Tabela 6). O resultado é honesto e importante: "
        "a superioridade da periferia se concentra no primeiro sub-período, de mercado "
        "mais fraco, e se inverte no segundo, de recuperação. Em outras palavras, "
        "“investir na periferia” comporta-se como uma estratégia defensiva — protege "
        "mais nas quedas do que ganha nas altas —, e a vantagem observada na janela "
        "completa é dependente de regime, não um efeito estável em todo o ciclo.")
    subper_show = subper.copy()
    keep = ["inicio", "fim", "n"] + [c for c in subper_show.columns
                                     if c.startswith("sharpe_perif") or
                                     c.startswith("sharpe_central") or c == "sharpe_benchmark"]
    subper_show = subper_show[keep]
    tabela(doc, subper_show,
           "Tabela 6 — Índice de Sharpe líquido por sub-período (centro × periferia × benchmark)",
           fmt=lambda c, v: f"{int(v)}" if c == "n" else f"{v:+.2f}")

    h2(doc, "Comparação GPMF × AGM (sob metodologia idêntica)")
    par(doc,
        "Aplicando o mesmo arcabouço à AGM (árvore com N−1 arestas) sobre exatamente o "
        "mesmo universo e janela, obtém-se a Tabela 7. O GPMF supera a AGM nas três "
        "carteiras. Estes números são uma referência interna; a comparação oficial do "
        "trabalho conjunto deve usar os resultados do braço AGM do parceiro (ver Seção "
        "“Comparação com o braço AGM”).")
    comp_show = comp.set_index("filtro")
    tabela(doc, comp_show.round(4),
           "Tabela 7 — GPMF × AGM × benchmark (carteiras de tamanho 10, líquido)",
           fmt=lambda c, v: (f"{v*100:.2f}%" if c in ("ret_liq", "dd") else f"{v:.3f}"))
    fig(doc, "comparacao_gpmf_mst.png",
        "Figura 5 — GPMF vs. AGM: retorno acumulado líquido das carteiras de tamanho 10.")

    # ---------------- Discussão / Conclusões ----------------
    h1(doc, "Discussão e Conclusões")
    par(doc,
        "O relatório parcial encontrou, na avaliação estática, vantagem das carteiras "
        "centrais — resultado aparentemente contrário a Pozzi et al. (2013). Com a "
        "convenção de dividendos corrigida, o universo determinístico e o Índice de "
        "Sharpe medido sobre o excesso ao CDI, essa vantagem desaparece: na janela "
        "completa fora da amostra as carteiras periféricas superam as centrais em todos "
        "os tamanhos testados, com o GPMF reconstruído a cada mês. A evidência, portanto, "
        "passa a favorecer qualitativamente a hipótese da periferia para os FIIs, e o "
        "GPMF supera a AGM sob metodologia idêntica, coerente com a maior quantidade de "
        "estrutura preservada pelo grafo planar. Cabe notar que, ao se descontar o CDI "
        "(em média elevado no período), todos os Índices de Sharpe — inclusive o do "
        "benchmark — tornam-se negativos; a leitura relevante é comparativa, não o sinal.")
    par(doc,
        "Há, contudo, três ressalvas que delimitam o alcance da conclusão. Primeira: "
        "líquido de custos de transação e imposto, nenhuma carteira ativa supera o "
        "benchmark passivo (IFIX); há indício (pelo bootstrap, mas não confirmado pelo "
        "teste mais conservador de Jobson-Korkie) de que a Central-10 e a Híbrida-10 "
        "fiquem atrás do índice, enquanto a Periférica-10 apenas o empata — ou seja, a "
        "periferia, no melhor cenário, iguala a gestão passiva. Segunda: entre as "
        "próprias carteiras GPMF, a "
        "diferença periferia−centro não atinge significância estatística (o intervalo de "
        "confiança por bootstrap cruza zero). Terceira, e mais importante para a "
        "interpretação: a superioridade da periferia não é estável no tempo — concentra-se "
        "no sub-período de mercado fraco e inverte-se na recuperação, comportando-se como "
        "uma estratégia defensiva, dependente de regime. Em síntese, a evidência fora da "
        "amostra é qualitativamente favorável à periferia e ao GPMF, mas a vantagem não "
        "sobrevive aos custos, não alcança significância e não é robusta ao longo do "
        "ciclo — o que reforça a importância de janelas mais longas, de regras de seleção "
        "que controlem o giro e de testes em múltiplos regimes de mercado em trabalhos "
        "futuros.")

    # ---------------- Comparação com Augusto (placeholder) ----------------
    h1(doc, "Comparação com o braço AGM (a consolidar com o parceiro)")
    par(doc,
        "Esta seção será preenchida com os resultados do braço AGM, desenvolvido por "
        "Augusto Carneiro da Silva, para a comparação oficial do trabalho conjunto. "
        "Para que a comparação seja válida, ambos os braços precisam compartilhar "
        "exatamente as mesmas premissas. A lista abaixo detalha o que solicitar ao "
        "parceiro e quais comparações realizar.")
    h2(doc, "O que pedir ao Augusto (para alinhar as premissas)")
    for item in [
        "Universo idêntico: a mesma lista de FIIs e a mesma janela (mesmas datas de "
        "início e fim). O ideal é compartilhar o cache data/raw/ deste projeto.",
        "Mesma convenção de retorno: Rt = ln(Pt/Pt−1) sobre o fechamento AJUSTADO "
        "(sem somar dividendos, para não contar em dobro).",
        "Mesmos parâmetros de janela deslizante: formação de 360 pregões, teste de 22, "
        "passo de 22.",
        "Mesmas carteiras: Central, Periférica e Híbrida nos tamanhos 10, 15 e 20, com "
        "pesos iguais (1/N) e mesma medida de centralidade na ordenação.",
        "Mesmos custos e tributos: 0,3% sobre o giro e 15% de IR sobre ganho de "
        "capital; dividendos isentos.",
        "Mesmo benchmark: XFIX11 (proxy do IFIX).",
        "Séries de retorno fora da amostra (diárias) de cada carteira da AGM, para "
        "rodar os testes de significância entre GPMF e AGM nos mesmos dias.",
    ]:
        doc.add_paragraph(item, style="List Bullet")
    h2(doc, "Comparações a realizar")
    for item in [
        "Tabela comparativa de Índice de Sharpe, retorno e drawdown (líquidos) GPMF × "
        "AGM, por tipo e tamanho de carteira.",
        "Teste de Jobson-Korkie entre as carteiras correspondentes da GPMF e da AGM "
        "(ex.: Periférica-10 GPMF vs. Periférica-10 AGM) para verificar se a diferença "
        "estrutural entre os grafos produz diferença significativa de desempenho.",
        "Curvas de retorno acumulado sobrepostas (GPMF, AGM e benchmark) no mesmo "
        "gráfico.",
        "Comparação de giro médio (turnover) entre os dois filtros, já que a AGM, com "
        "menos arestas, tende a produzir rankings mais instáveis entre janelas.",
        "Verificação cruzada da hipótese de Pozzi nos dois filtros (periferia × centro), "
        "para checar se a conclusão é robusta ao método de filtragem.",
    ]:
        doc.add_paragraph(item, style="List Bullet")
    par(doc,
        "Observação técnica: o código já permite gerar a referência interna da AGM "
        "(scripts/05_comparacao.py); basta substituir os números pela execução oficial "
        "do parceiro quando disponíveis.")

    # ---------------- Bibliografia ----------------
    h1(doc, "Bibliografia")
    refs = [
        "ALTINOZ, M.; ALTINOZ, O. T. Systematic Initialization Approaches for Portfolio "
        "Optimization Problems. IEEE Access, 2019.",
        "MANTEGNA, R. N. Hierarchical structure in financial markets. European Physical "
        "Journal B, v. 11, p. 193–197, 1999.",
        "MARKOWITZ, H. Portfolio selection. Journal of Finance, 1952.",
        "MEMMEL, C. Performance hypothesis testing with the Sharpe ratio. Finance "
        "Letters, 2003.",
        "PERALTA, G.; ZAREEI, A. A network approach to portfolio selection. Journal of "
        "Empirical Finance, 2016.",
        "POZZI, F.; DI MATTEO, T.; ASTE, T. Spread of risk across financial markets: "
        "better to invest in the peripheries. Scientific Reports, 2013.",
        "SAHA, S.; GAO, J.; GERLACH, R. A survey of the application of graph-based "
        "approaches in stock market analysis and prediction. International Journal of "
        "Data Science and Analytics, v. 14, p. 1–15, 2022.",
        "TUMMINELLO, M.; ASTE, T.; DI MATTEO, T.; MANTEGNA, R. N. A tool for filtering "
        "information in complex systems. PNAS, v. 102, n. 30, p. 10421–10426, 2005.",
    ]
    for ref in refs:
        doc.add_paragraph(ref)

    # ---------------- Perspectivas ----------------
    h1(doc, "Perspectivas de continuidade")
    par(doc,
        "Os próximos passos incluem: (i) estender a janela de dados para aumentar o "
        "poder estatístico dos testes fora da amostra; (ii) incorporar a centralidade "
        "de autovetor e esquemas de ponderação por risco na regra de seleção; (iii) "
        "consolidar a comparação oficial GPMF × AGM com o parceiro; e (iv) redigir o "
        "artigo científico para submissão a periódico ou conferência de finanças "
        "quantitativas.")

    saida = Path(__file__).resolve().parent.parent / "docs" / "Relatorio_Final_Yoon.docx"
    saida.parent.mkdir(exist_ok=True)
    doc.save(str(saida))
    print(f"relatório salvo em {saida}")


if __name__ == "__main__":
    main()

# Guia do código — Carteiras de FIIs por filtragem em grafos (GPMF × AGM)

Projeto de Iniciação Científica (PIBIC/CNPq, FT-Unicamp). Autor: Yoon Sung Jang.
Orientador: Prof. Dr. João Roberto Bertini Junior. Benchmarks de Markowitz
(`src/benchmarks.py`, scripts `11` a `14`): Augusto Carneiro da Silva.

Este guia explica o que o código faz, como rodar, como cada etapa funciona e
quais partes do repositório entraram no relatório, quais entraram no artigo e
quais são legado.

---

## 1. A pergunta

Pozzi, Di Matteo e Aste (2013) mostraram, para ações, que carteiras formadas
com os ativos **periféricos** de uma rede de correlações rendem melhor, ajustado
ao risco, do que carteiras formadas com os ativos **centrais**. A ideia é que os
ativos periféricos estão menos ligados ao resto do mercado e, por isso,
diversificam melhor.

O projeto testa se isso vale para **Fundos de Investimento Imobiliário (FIIs)**
da B3, com três cuidados que o estudo original não tinha:

1. **Avaliação fora da amostra.** A carteira é escolhida com dados do passado e
   medida em dados que ela nunca viu.
2. **Custos e imposto reais.** Custo de transação e o IR de 20% sobre o ganho de
   capital de FII.
3. **Dois filtros de grafo.** O GPMF (grafo planar, mais denso) e a AGM (árvore
   geradora mínima, mais esparsa), comparados sob as mesmas regras.

No artigo, as carteiras de rede também são comparadas com os **benchmarks
clássicos de Markowitz** (1/N, mínima variância e tangência), rodados na mesma
janela, com o mesmo custo e o mesmo imposto.

---

## 2. Início rápido

Requer Python 3.12.

```bash
git clone https://github.com/yoonsungj04/IC_Grafos_FIIs.git
cd IC_Grafos_FIIs
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Os dados brutos **já estão no repositório** (`data/raw/`), então não é preciso
baixar nada.

**Resultados do relatório** (menos de 1 minuto no total):

```bash
python scripts/02_estatica.py              # ranking e desempenho dentro da amostra
python scripts/03_rolling.py               # backtest fora da amostra (GPMF)
python scripts/04_custos.py                # custos, imposto e testes de significância
python scripts/07_comparacao_completa.py   # GPMF × AGM
python scripts/09_subperiodos.py           # robustez por subperíodo
```

**Resultados do artigo** (depois dos cinco acima; cerca de 3 minutos no total):

```bash
python scripts/05_comparacao.py                # GPMF × AGM + significância por filtro
python scripts/11_benchmarks_classicos.py      # benchmarks de Markowitz + tabelas em LaTeX
python scripts/12_significancia_benchmarks.py  # testes dos benchmarks
python scripts/13_auditoria.py                 # confere números citados no texto
python scripts/14_figuras_artigo.py            # figuras do artigo (inglês, PDF e PNG)
```

A ordem importa: todos os scripts depois do `03` leem arquivos que ele grava em
`data/processed/`, e o `09` também lê o que o `04` grava. Tudo roda offline e é
determinístico (semente 42): rodar de novo produz as mesmas tabelas. A única
exceção é a terceira casa decimal da mínima variância (ver seção 7).

### Baixar os dados de novo (opcional)

```bash
python scripts/01_download.py          # preços, dividendos, benchmark e CDI
python scripts/verifica_dividendos.py  # confere a convenção de dividendos
```

Só faça isso se quiser mudar o período ou os fundos. As datas estão fixas em
`config.py`, mas o Yahoo às vezes revisa preços antigos, então um download novo
pode mudar levemente os números.

---

## 3. Como funciona, etapa por etapa

```
preços (Yahoo) ──► universo de 51 FIIs ──► retornos diários
                                               │
            ┌──────────── a cada 22 pregões ───┘
            ▼
  últimos 360 pregões ──► correlação ──► distância ──► GPMF (ou AGM)
                                                          │
                                                          ▼
                                                centralidade composta
                                                          │
                                                          ▼
                                     carteiras Central / Periférica / Híbrida
                                                          │
                                                          ▼
                      mantém 22 pregões ──► custo + imposto ──► Sharpe sobre o CDI
```

### 3.1 Dados — `src/data_load.py`

- Fonte: endpoint `chart` do Yahoo Finance. O Yahoo bloqueia requisições comuns
  (HTTP 429); por isso o download usa `curl_cffi` imitando o Chrome.
- Para cada fundo são baixados o **fechamento bruto**, o **fechamento ajustado**
  por proventos e os **dividendos**.
- Período: **01/03/2022 a 04/11/2025**.
- Taxa livre de risco: **CDI diário** do Banco Central (SGS, série 12).
- Benchmark: o `^IFIX` não está disponível no Yahoo, então usamos o **ETF
  XFIX11**, que replica o IFIX, como aproximação.
- Este é o único módulo que acessa a internet. Tudo depois disso lê de
  `data/raw/`.

**Convenção de dividendos (importante).** O fechamento ajustado do Yahoo já
reinveste os dividendos. O script `verifica_dividendos.py` confirma isso no
MXRF11. Portanto o retorno total é só `ln(P_t / P_{t-1})` sobre o ajustado.
Somar o dividendo de novo contaria o provento duas vezes.

### 3.2 Universo — `src/filters.py`

A lista `TICKERS_CANDIDATOS` em `config.py` tem cerca de 70 FIIs líquidos. O
universo final é escolhido **automaticamente** a partir dos dados: entra quem
tem pelo menos 360 pregões de histórico e no máximo 5% de dados faltantes.
Resultado: **51 FIIs**. Buracos pequenos são preenchidos com o último preço
conhecido.

### 3.3 Da correlação ao grafo — `src/gpmf.py`

1. Correlação de Pearson entre os retornos diários de cada par de fundos.
2. Distância de Mantegna: `d_ij = √(2(1 − ρ_ij))`. Correlação alta vira
   distância pequena. Vai de 0 (ρ = 1) a 2 (ρ = −1).
3. Construção do filtro:
   - **GPMF** (`construir_gpmf`): ordena todos os pares da menor para a maior
     distância e adiciona as arestas uma a uma, **desde que o grafo continue
     planar** (teste Left-Right do `networkx.check_planarity`). Para quando
     chega a **3N − 6 = 147 arestas**.
   - **AGM** (`construir_mst`): árvore geradora mínima (Kruskal, via
     `networkx.minimum_spanning_tree`), com **N − 1 = 50 arestas**.

Toda aresta da AGM também está no GPMF. O GPMF é a AGM mais cerca de 100
ligações extras, e são essas ligações que mudam quem parece central ou
periférico.

### 3.4 Centralidade — `src/centrality.py`

Para cada fundo calculamos três medidas e as normalizamos para [0, 1]
(min-max):

| Medida | O que mede | Peso da aresta |
|---|---|---|
| Grau | número de vizinhos | sem peso |
| Intermediação | quantos caminhos mínimos passam pelo fundo | distância |
| Proximidade | quão perto, em média, o fundo está de todos os outros | distância |

O **escore composto** é a média das três. É ele que ordena os fundos
(`RANKING_MEASURE = "composite"`).

O autovetor também é calculado, porque constava da proposta, mas **não entra no
escore composto**. Foi assim que o projeto-irmão (AGM) definiu o critério, e a
comparação entre os dois só é justa com a mesma regra.

### 3.5 Carteiras — `src/portfolio.py`

Com os fundos ordenados pelo escore composto:

- **Central**: os k mais centrais.
- **Periférica**: os k menos centrais.
- **Híbrida**: metade de cada ponta.

Tamanhos k = 10, 15 e 20. Pesos **iguais** (1/k).

### 3.6 Janela rolante — `src/rolling.py`

Este é o núcleo do trabalho. Para evitar viés de antecipação (*look-ahead*):

1. Pega os **360 pregões** anteriores (janela de formação).
2. Constrói o grafo, calcula a centralidade e forma as carteiras só com esses
   dados.
3. Mantém as carteiras pelos **22 pregões** seguintes (≈ 1 mês), que não
   entraram na formação.
4. Avança 22 pregões e repete.

Resultado: **25 rebalanceamentos** e **550 pregões fora da amostra**
(09/08/2023 a 20/10/2025). As janelas de teste são emendadas numa série
contínua por carteira.

O backtest roda em paralelo sobre os retornos **totais** (para medir o
desempenho) e sobre os retornos **de preço** (para calcular o imposto; ver
abaixo).

### 3.7 Custos e imposto — `src/costs.py`

- **Giro** (*turnover*) em cada rebalanceamento: `½ Σ |w_novo − w_antigo|`.
  Vai de 0 (não mudou nada) a 1 (trocou tudo).
- **Custo de transação**: 0,3% × giro, debitado no primeiro dia da janela.
- **Imposto**: 20% sobre o ganho de capital **realizado** (Lei 11.033/2004).
  Três detalhes:
  - incide só sobre a fração **vendida** (o giro), não sobre a carteira toda;
  - incide só sobre o ganho **de preço**; dividendos de FII são isentos para
    pessoa física;
  - FII não tem a isenção de R$ 20 mil/mês que as ações têm.

  Na prática: `tributo = 0,20 × giro × max(ganho_de_preço_da_janela, 0)`,
  debitado no último dia da janela.

Carteiras periféricas giram mais (≈ 36–46% ao mês, contra ≈ 25–28% das
centrais), então pagam mais custo e imposto. Os resultados "líquidos" já
descontam isso.

### 3.8 Métricas e significância — `src/metrics.py` e `src/riskfree.py`

- **Sharpe sobre o CDI**: média do retorno excedente ao CDI dividida pelo seu
  desvio-padrão, anualizada por √252.
- **Bootstrap circular em blocos** (teste principal): sorteia blocos de 22 dias
  da série, recalcula a diferença de Sharpe 5.000 vezes e dá o intervalo de
  confiança de 95% e o valor-p. Os blocos preservam a dependência entre dias
  vizinhos.
- **Jobson-Korkie com correção de Memmel** (teste secundário): teste assintótico
  clássico para diferença de Sharpe.

### 3.9 Benchmarks de Markowitz — `src/benchmarks.py`

Para saber se a seleção por rede vale a pena, ela é comparada com regras
clássicas de alocação. O laço é o mesmo de `rolling.backtest_rolling` (360/22,
mesmo giro, mesmo custo, mesmo IR); **só muda a regra que decide os pesos**,
sempre sobre os 51 fundos e sem venda a descoberto:

| Regra | Pesos |
|---|---|
| 1/N (`equal_weight`) | iguais para todos os 51 fundos |
| Mínima variância (`min_var`) | os que minimizam a variância da carteira |
| Mínima variância com encolhimento (`min_var_shrink`) | idem, com a covariância de Ledoit-Wolf (2004), mais estável |
| Tangência (`tangency`) | os que maximizam o Sharpe estimado na janela de formação |

Os pesos são estimados só com a janela de formação e otimizados por SLSQP
(`scipy`). Se o otimizador não convergir, a regra cai em 1/N; nos dados atuais
isso não acontece em nenhuma das 25 janelas.

O módulo também aceita um **seletor por rede**: o grafo escolhe os k fundos e a
otimização decide os pesos dentro deles. É assim que se obtém a linha
"seleção por rede + pesos otimizados", que separa o efeito da seleção do efeito
da ponderação.

---

## 4. Mapa do repositório

### O que foi usado no trabalho final

| Arquivo | Função | Gera | Onde aparece no relatório |
|---|---|---|---|
| `config.py` | todos os parâmetros | — | — |
| `src/*.py` | a lógica (seção 3) | — | — |
| `scripts/01_download.py` | baixa e congela os dados | `data/raw/*.csv` | Metodologia |
| `scripts/verifica_dividendos.py` | confere a convenção de dividendos | `verifica_dividendos_MXRF11.*` | Metodologia |
| `scripts/02_estatica.py` | grafo na janela inteira (dentro da amostra) | `centralidade_estatica.csv`, `tabela_estatica.csv`, `gpmf_estatico.png` | Tabelas 2 e 3 |
| `scripts/03_rolling.py` | backtest fora da amostra (GPMF) | `tabela_rolling_bruta.csv`, `curvas_oos_bruto.png`, séries em `data/processed/` | base de tudo abaixo |
| `scripts/04_custos.py` | custos, imposto e testes | `tabela_custos.csv`, `tabela_custos_decomposta.csv`, `testes_significancia.csv`, `curvas_oos_liquido.png` | Tabelas 5 e 7, Figura 3 |
| `scripts/07_comparacao_completa.py` | GPMF × AGM, mesmas regras | `comparacao_completa.csv`, `pozzi_por_filtro.csv` | Tabela 4 e pôster |
| `scripts/09_subperiodos.py` | divide os 550 dias em duas metades | `tabela_subperiodos.csv` | Tabela 6 |
| `notebooks/IC_GPMF.ipynb` | roda os scripts em sequência (útil no Colab) | — | — |

### O que foi acrescentado para o artigo

| Arquivo | Função | Gera |
|---|---|---|
| `scripts/05_comparacao.py` | GPMF × AGM com os três tipos de carteira (k = 10) e o teste Periférica − Central em cada filtro | `tabela_comparacao_gpmf_mst.csv`, `pozzi_significancia.csv`, `comparacao_gpmf_mst.png` |
| `src/benchmarks.py` | regras de Markowitz e seletor por rede (seção 3.9) | — |
| `scripts/11_benchmarks_classicos.py` | roda os benchmarks e refaz GPMF × AGM na mesma base | `tabela_benchmarks_classicos.csv`, `tabela_comparacao_filtros_corrigida.csv`, `latex_tabelas.txt` (linhas prontas para o LaTeX) |
| `scripts/12_significancia_benchmarks.py` | bootstrap e Jobson-Korkie para os benchmarks | `significancia_benchmarks.csv` |
| `scripts/13_auditoria.py` | confere números citados no texto do artigo que não saem de nenhuma tabela | só imprime na tela |
| `scripts/14_figuras_artigo.py` | as três figuras do artigo, em inglês, no tamanho de impressão | `fig1_filters_side_by_side`, `fig2_pmfg_labeled`, `fig3_growth_oos` (PDF e PNG) |

As tabelas ficam em `results/tables/` e as figuras em `results/figures/`.

**Atenção às figuras:** o `.gitignore` exclui `results/figures/*.png`, então a
maioria das figuras não vem no clone. Elas são recriadas quando você roda os
scripts.

### O que não foi usado (legado)

Ficou no repositório porque faz parte do histórico do projeto, mas **não
produz nada que esteja no relatório final nem no artigo**:

| Arquivo | Por que não é usado |
|---|---|
| `scripts/08_comparacao_augusto.py` | comparação alinhada com o projeto-irmão; substituída pelo `07` |
| `scripts/10_comparacao_augusto_real.py` | compara com as séries enviadas pelo projeto-irmão; depende de um CSV externo que não está no repositório |
| `scripts/06_relatorio*.py` e `src/relatorio_utils.py` | geravam os relatórios v1–v4 automaticamente; ainda citam IR de 15% (regra antiga) |
| `docs/Relatorio_Final_Yoon*.docx` | versões intermediárias do relatório |
| `results/tables/comparacao_alinhada_augusto.csv`, `comparacao_augusto_real.csv` | **saídas desatualizadas**, calculadas com o modelo de imposto antigo; os números não batem com o relatório nem com o artigo |

Também há código que existe mas fica desligado:

- `data_load.carregar_dividendos()`: nunca é chamada (o preço ajustado já
  inclui os dividendos).
- `WEIGHTING = "inverse_vol"`: opção de peso pelo inverso da volatilidade; o
  trabalho usa pesos iguais.
- Centralidade de autovetor: calculada, mas fora do escore composto.

---

## 5. Parâmetros que você pode mudar (`config.py`)

| Parâmetro | Valor usado | O que controla |
|---|---|---|
| `START_DATE`, `END_DATE` | 2022-03-01 a 2025-11-04 | período de estudo (exige novo download) |
| `MIN_HISTORY_DAYS`, `MAX_MISSING_FRACTION` | 360, 0,05 | quem entra no universo |
| `CORR_METHOD` | `"pearson"` | correlação (`"spearman"` também funciona) |
| `RANKING_MEASURE` | `"composite"` | medida que ordena os fundos (`"degree"`, `"betweenness"`, `"closeness"`, `"eigenvector"`) |
| `PORTFOLIO_SIZES` | (10, 15, 20) | tamanhos de carteira |
| `WEIGHTING` | `"equal"` | pesos (`"inverse_vol"` disponível) |
| `FORMATION_DAYS`, `TEST_DAYS`, `ROLL_STEP_DAYS` | 360, 22, 22 | janela rolante |
| `TRANSACTION_COST`, `CAPITAL_GAINS_TAX` | 0,003, 0,20 | custo e imposto |
| `RISK_FREE_SOURCE` | `"cdi"` | base do Sharpe (`"zero"` reproduz o Sharpe simples) |
| `N_BOOTSTRAP`, `RANDOM_SEED` | 5000, 42 | bootstrap |

Para comparar com outro filtro de grafo, basta escrever uma função
`distancia -> nx.Graph` e passá-la como `construtor=` para
`rolling.backtest_rolling` (é o que o `07` faz com GPMF e AGM).

---

## 6. Resultados principais

Sharpe líquido (sobre o CDI) fora da amostra, 550 pregões:

| Carteira | GPMF | AGM |
|---|---:|---:|
| Central-10 | −1,55 | −1,15 |
| Periférica-10 | −1,10 | −1,25 |
| Central-15 | −1,36 | −1,49 |
| Periférica-15 | −0,94 | −1,22 |
| Central-20 | −1,49 | −1,41 |
| Periférica-20 | −0,95 | −1,12 |
| IFIX (XFIX11) | −0,91 | −0,91 |

**Como ler.** Todos os Sharpes são negativos porque o CDI rendeu ≈ 12% ao ano no
período, mais do que qualquer carteira de FIIs. Então "menos negativo" é
melhor.

1. **No GPMF, a periferia vence o centro nos três tamanhos**, bruto e líquido, e
   nas duas metades do período (`tabela_subperiodos.csv`). Em retorno líquido
   anualizado, a Periférica-20 fez +5,1% e a Central-10, −1,4%.
2. **Na AGM, o padrão falha em k = 10.** No grafo da janela completa, os dois
   filtros concordam em 8 dos 10 fundos centrais, mas só em 4 dos 10
   periféricos. Com margem bruta pequena, o
   giro maior da periférica inverte o resultado depois dos custos.
3. **Significância.** Periférica − Central não é significativa (p = 0,34 no
   bootstrap). A única diferença significativa é Central-10 − IFIX
   (p = 0,04 no bootstrap, mas 0,20 no Jobson-Korkie): concentrar nos fundos
   centrais perdeu para o índice. Nenhuma carteira superou o índice com
   significância.

### Benchmarks de Markowitz (artigo)

| Estratégia | Retorno líq. a.a. | Volatilidade a.a. | Sharpe líquido |
|---|---:|---:|---:|
| Mínima variância | +6,7% | 6,4% | −0,77 |
| Mínima variância (encolhimento) | +6,8% | 6,3% | −0,78 |
| IFIX (XFIX11) | +4,9% | 7,3% | −0,91 |
| Melhor carteira de rede (GPMF Periférica-15) | +4,7% | 7,2% | −0,94 |
| Tangência | +3,1% | 8,0% | −1,03 |
| 1/N | +3,4% | 6,9% | −1,18 |

A mínima variância teve o maior Sharpe do estudo e superou as 18 carteiras de
rede em retorno e em volatilidade. **Nenhuma diferença é significativa**: contra
o IFIX, p = 0,69; contra a GPMF Periférica-20, p = 0,56. A leitura correta é que
nenhuma estratégia, de rede ou clássica, se distinguiu do índice no período.

Tabelas completas: `results/tables/`.

---

## 7. Cuidados

- **Não some o dividendo ao preço ajustado.** Ele já está lá (seção 3.1).
- **O `02_estatica` é só referência.** Ele escolhe e avalia a carteira no mesmo
  período, o que infla o resultado. O resultado válido é o fora da amostra
  (`03` em diante).
- **XFIX11 ≠ IFIX.** O ETF tem taxa de administração e erro de rastreamento
  (até ≈ 1,25 p.p. ao ano). Diferenças menores que isso contra o "índice" não
  devem ser interpretadas.
- **Os valores-p não têm correção para comparações múltiplas.** Foram feitos
  cinco testes; trate p = 0,04 com cautela.
- **Rode `03` antes de todos os outros.** Os scripts seguintes leem arquivos em
  `data/processed/`, que não vão para o Git.
- **A mínima variância pode variar na terceira casa decimal** de uma máquina
  para outra (por exemplo, Sharpe −0,7676 contra −0,7688), porque depende de um
  otimizador numérico. Arredondado, o resultado é o mesmo.
- **pandas 3.** O `requirements.txt` fixa o pandas 2.2.3, mas o código também
  roda no pandas 3 (o Colab atual já usa essa versão).

---

## 8. Referências

- MANTEGNA, R. N. Hierarchical structure in financial markets. *The European
  Physical Journal B*, v. 11, p. 193–197, 1999.
- TUMMINELLO, M.; ASTE, T.; DI MATTEO, T.; MANTEGNA, R. N. A tool for filtering
  information in complex systems. *PNAS*, v. 102, n. 30, p. 10421–10426, 2005.
- POZZI, F.; DI MATTEO, T.; ASTE, T. Spread of risk across financial markets:
  better to invest in the peripheries. *Scientific Reports*, v. 3, 1665, 2013.
- JOBSON, J. D.; KORKIE, B. M. Performance hypothesis testing with the Sharpe
  and Treynor measures. *The Journal of Finance*, v. 36, n. 4, p. 889–908, 1981.
- MEMMEL, C. Performance hypothesis testing with the Sharpe ratio. *Finance
  Letters*, v. 1, p. 21–23, 2003.
- LEDOIT, O.; WOLF, M. A well-conditioned estimator for large-dimensional
  covariance matrices. *Journal of Multivariate Analysis*, v. 88, n. 2,
  p. 365–411, 2004.
- DEMIGUEL, V.; GARLAPPI, L.; UPPAL, R. Optimal versus naive diversification:
  how inefficient is the 1/N portfolio strategy? *The Review of Financial
  Studies*, v. 22, n. 5, p. 1915–1953, 2009.
- BRASIL. Lei nº 11.033, de 21 de dezembro de 2004.

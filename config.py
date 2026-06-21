"""
Parâmetros do projeto, todos centralizados aqui.

A ideia é não deixar nenhum número "mágico" nem chamada de rede espalhada pelo
código: tudo que é configurável (janela de estudo, custos, parâmetros do grafo,
janela rolante) fica neste arquivo para garantir reprodutibilidade. Os caminhos
são resolvidos em relação a este arquivo, então o pacote funciona igual rodando
localmente ou no Colab.
"""
from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------- #
# Caminhos
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
TABLES_DIR = RESULTS_DIR / "tables"

for _d in (RAW_DIR, PROCESSED_DIR, FIGURES_DIR, TABLES_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------- #
# Janela de estudo (fixa, sem datetime.now())
# Período mar/2022 a nov/2025, alinhado ao projeto original (início em mar/2022).
# A janela longa é necessária para a validação rolante ter período de teste
# suficiente fora da amostra. As datas ficam fixas para a análise ser reprodutível.
# --------------------------------------------------------------------------- #
START_DATE = "2022-03-01"
END_DATE = "2025-11-04"

# --------------------------------------------------------------------------- #
# Convenção de download / dividendos
# Verificado empiricamente (ver scripts/verifica_dividendos.py): o Yahoo com
# auto_adjust=True já reinveste os dividendos no fechamento ajustado, ou seja,
# o retorno do ajustado equivale a (preço + provento). Portanto NÃO se soma o
# dividendo de novo: o retorno correto é Rt = ln(Pt/Pt-1) sobre o fechamento
# ajustado. Somar Dt outra vez (Rt = ln((Pt+Dt)/Pt-1)) contaria duas vezes.
# --------------------------------------------------------------------------- #
AUTO_ADJUST = True               # baixa o fechamento ajustado por proventos
ADD_DIVIDENDS_IN_RETURN = False  # não somar Dt: já está embutido no ajustado
RETURN_TYPE = "log"              # "log" -> ln(Pt/Pt-1);  "simple" -> Pt/Pt-1 - 1

# --------------------------------------------------------------------------- #
# Seleção do universo de FIIs
# A lista abaixo é apenas o conjunto candidato (FIIs líquidos da B3). O universo
# final é decidido de forma determinística a partir dos dados em cache, exigindo
# histórico mínimo e poucos dados faltantes — nada de lista colada na mão.
# --------------------------------------------------------------------------- #
YF_SUFFIX = ".SA"                  # sufixo dos tickers da B3 no Yahoo Finance
MIN_HISTORY_DAYS = 360             # pregões mínimos para entrar no universo
MAX_MISSING_FRACTION = 0.05        # descarta ticker com >5% de fechamentos faltando

# FII usado na verificação da convenção de dividendos (alto dividend yield).
DIVIDEND_VERIFY_TICKER = "MXRF11"

# Conjunto candidato: FIIs de tijolo, papel e fundos de fundos com liquidez.
TICKERS_CANDIDATOS = [
    "MXRF11", "KNRI11", "HGLG11", "XPML11", "VISC11", "HGBS11", "KNCR11",
    "BCFF11", "HFOF11", "RECR11", "IRDM11", "XPLG11", "BTLG11", "VILG11",
    "HGRE11", "KNIP11", "MCCI11", "RBRR11", "RBRF11", "VGIP11", "HSML11",
    "MALL11", "RBRP11", "GGRC11", "HGRU11", "BRCO11", "TRXF11", "VINO11",
    "JSRE11", "BRCR11", "RCRB11", "ALZR11", "PVBI11", "HGCR11", "DEVA11",
    "CPTS11", "VRTA11", "MGFF11", "KFOF11", "RBVA11", "VGHF11", "HCTR11",
    "RZTR11", "TGAR11", "MFII11", "FEXC11", "BPFF11", "RBRY11", "RECT11",
    "SDIL11", "LVBI11", "HGFF11", "VCJR11", "KNSC11", "VGIR11", "BTRA11",
    "RVBI11", "MORE11", "BLMG11", "VTLT11", "OUJP11", "AFHI11", "PORD11",
    "HGPO11", "BRCR11", "NEWL11", "XPCI11", "VSLH11", "GARE11", "BTLG11",
]

# Benchmark de mercado: IFIX, com XFIX11 como alternativa (o ^IFIX costuma
# falhar por fuso horário; o XFIX11 é um ETF que replica o índice).
BENCHMARK_TICKER = "^IFIX"
BENCHMARK_FALLBACK = "XFIX11"

# --------------------------------------------------------------------------- #
# Construção do grafo (GPMF)
#   distância d_ij = sqrt(2 * (1 - rho_ij))
#   o GPMF é planar e, quando conexo sobre N vértices, tem 3N - 6 arestas;
#   é construído adicionando as arestas de menor distância enquanto a
#   planaridade é preservada (Boyer-Myrvold via networkx.check_planarity).
# --------------------------------------------------------------------------- #
CORR_METHOD = "pearson"            # "pearson" | "spearman"


def limite_arestas_planar(n: int) -> int:
    """Cota máxima de arestas de um grafo planar conexo com n vértices."""
    return 3 * n - 6


# Medidas de centralidade usadas para ordenar os vértices.
CENTRALITY_MEASURES = ("degree", "betweenness", "closeness", "eigenvector")

# --------------------------------------------------------------------------- #
# Formação das carteiras
#   Central   = k vértices mais centrais
#   Periférica = k vértices menos centrais (a hipótese de Pozzi et al., 2013)
#   Híbrida   = metade central, metade periférica
# --------------------------------------------------------------------------- #
PORTFOLIO_SIZES = (10, 15, 20)
PORTFOLIO_TYPES = ("central", "peripheral", "hybrid")
WEIGHTING = "equal"                # "equal" | "inverse_vol"
RANKING_MEASURE = "degree"         # medida usada na ordenação para formar carteiras

# --------------------------------------------------------------------------- #
# Engine de janela rolante (validação fora da amostra)
#   forma a carteira com FORMATION_DAYS, mantém por TEST_DAYS e avança.
# --------------------------------------------------------------------------- #
FORMATION_DAYS = 360
TEST_DAYS = 22
ROLL_STEP_DAYS = 22

# --------------------------------------------------------------------------- #
# Custos e tributos
#   Pessoa física: dividendos isentos de IR; ganho de capital tributado em 15%;
#   custo de transação de 0,3% sobre o giro (round-trip).
# --------------------------------------------------------------------------- #
TRANSACTION_COST = 0.003           # 0,3% por giro
CAPITAL_GAINS_TAX = 0.15           # 15% sobre o ganho de capital realizado
DIVIDENDS_TAX = 0.0                # FIIs: dividendos isentos para PF

# --------------------------------------------------------------------------- #
# Avaliação
# --------------------------------------------------------------------------- #
RISK_FREE_ANNUAL = 0.0             # ajustar para proxy do CDI/SELIC se necessário
TRADING_DAYS_PER_YEAR = 252
RANDOM_SEED = 42                   # bootstrap e qualquer etapa estocástica

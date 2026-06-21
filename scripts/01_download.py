"""
Baixa e congela os dados brutos dos FIIs candidatos e do benchmark.

Roda uma única vez; depois disso toda a análise é offline sobre o cache em
data/raw/. Inclui o IFIX (ou XFIX11 como alternativa).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from src import data_load


def main() -> None:
    print(f"janela: {config.START_DATE} -> {config.END_DATE}\n")
    data_load.baixar_universo()

    # benchmark: tenta IFIX, cai para o ETF XFIX11
    print("\nbaixando benchmark...")
    for bench in (config.BENCHMARK_TICKER, config.BENCHMARK_FALLBACK):
        symbol = bench if bench.startswith("^") else f"{bench}{config.YF_SUFFIX}"
        try:
            df = data_load.baixar_serie(symbol)
            if df["ajustado"].dropna().empty:
                raise ValueError("série vazia")
            df["ajustado"].rename("benchmark").to_csv(config.RAW_DIR / "benchmark.csv")
            print(f"benchmark = {bench} ({df['ajustado'].dropna().shape[0]} pregões)")
            break
        except Exception as e:
            print(f"benchmark {bench} falhou ({e})")


if __name__ == "__main__":
    main()

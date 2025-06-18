import pandas as pd
import numpy as np
from datetime import datetime
from enum import Enum
from pybit.unified_trading import HTTP
from results_manager import ResultsManager
from itertools import product

# Constantes de configuração
cripto = 'BTCUSDT'
tempo_grafico = '1'
data_inicio = '2024-01-01'
data_fim = '2024-08-01'
taxa_corretora = 0.055
alavancagem = 10
saldo_inicial = 1000
setup = 'otimizacao de parametros'

class EstadoDeTrade(Enum):
    DE_FORA = 'de fora'
    COMPRADO = 'comprado'
    VENDIDO = 'vendido'

def calcular_atr(df, periodo=14):
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['ATR'] = df['tr'].rolling(window=periodo).mean()
    return df

def buscar_dados_historicos():
    print("Carregando dados históricos...")
    cliente = HTTP()
    start_timestamp = int(pd.to_datetime(data_inicio).timestamp()) * 1000
    end_timestamp = int(pd.to_datetime(data_fim).timestamp()) * 1000
    velas_sem_estrutura = []
    tentativas = 0

    while start_timestamp < end_timestamp:
        resposta = cliente.get_kline(symbol=cripto, interval=tempo_grafico, limit=1000, start=start_timestamp)
        dados = resposta['result']['list']
        if not dados:
            print("Sem dados retornados. Encerrando busca.")
            break
        velas_sem_estrutura += dados[::-1]
        start_timestamp = int(dados[-1][0]) + 1000
        tentativas += 1
        print(f"Lote {tentativas}: {len(velas_sem_estrutura)} velas carregadas...")
        if tentativas > 100:
            print("Limite de tentativas atingido. Parando busca para evitar loop infinito.")
            break

    colunas = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover']
    df = pd.DataFrame(velas_sem_estrutura, columns=colunas)
    df['open_time'] = pd.to_datetime(df['open_time'].astype(np.int64), unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    print("Dados históricos carregados com sucesso.")
    return df

def calcular_indicadores(df, ema_rapida, ema_lenta):
    df[f'EMA_{ema_rapida}'] = df['close'].ewm(span=ema_rapida, adjust=False).mean()
    df[f'EMA_{ema_lenta}'] = df['close'].ewm(span=ema_lenta, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs)).fillna(100)
    df['Volume_EMA_20'] = df['volume'].ewm(span=20, adjust=False).mean()
    return df

def contar_candles_consecutivos(df, index, ema_periodo):
    if index < 1:
        return 0, 0
    start = max(0, index - 30)
    janela = df.iloc[start:index]
    acima = (janela['close'] > janela[f'EMA_{ema_periodo}']).astype(int)
    abaixo = (janela['close'] < janela[f'EMA_{ema_periodo}']).astype(int)
    count_acima = acima[::-1].cumprod().sum()
    count_abaixo = abaixo[::-1].cumprod().sum()
    return int(count_acima), int(count_abaixo)

def executar_backtest(df, ema_rapida, ema_lenta, risco_por_trade, risco_retorno, qntd_velas_stop, rsi_min, rsi_max):
    saldo = saldo_inicial
    estado = EstadoDeTrade.DE_FORA
    preco_stop = preco_alvo = preco_entrada = 0
    resultados = ResultsManager(saldo, taxa_corretora, setup)
    df = calcular_indicadores(df.copy(), ema_rapida, ema_lenta)
    df = calcular_atr(df)

    slippage_percent = 0.0005  # 0.05%
    max_trades_per_day = 10
    trade_count_today = 0
    current_day = None
    tamanho_posicao = saldo_inicial * 0.01  # Exemplo: operar sempre com 1% do saldo inicial

    for i in range(max(200, qntd_velas_stop) + 1, len(df)):
        data_atual = df['open_time'].iloc[i].date()

        # Limite de trades por dia
        if data_atual != current_day:
            current_day = data_atual
            trade_count_today = 0

        ano = df['open_time'].iloc[i].year
        mes = df['open_time'].iloc[i].month
        resultados.initialize_month(ano, mes)

        count_acima, count_abaixo = contar_candles_consecutivos(df, i, ema_rapida)
        tendencia_alta = df[f'EMA_{ema_rapida}'].iloc[i-1] > df[f'EMA_{ema_lenta}'].iloc[i-1] > df['EMA_200'].iloc[i-1]
        tendencia_baixa = df[f'EMA_{ema_rapida}'].iloc[i-1] < df[f'EMA_{ema_lenta}'].iloc[i-1] < df['EMA_200'].iloc[i-1]

        atr_atual = df['ATR'].iloc[i-1]

        if estado == EstadoDeTrade.COMPRADO:
            if df['high'].iloc[i] >= preco_alvo:
                lucro_pct = ((preco_alvo - preco_entrada) / preco_entrada) * 100 * alavancagem - (taxa_corretora * 2)
                lucro = tamanho_posicao * (lucro_pct / 100)
                saldo += lucro
                estado = EstadoDeTrade.DE_FORA
                resultados.update_on_gain(ano, mes, lucro)
            elif df['low'].iloc[i] <= preco_stop:
                perda_pct = ((preco_entrada - preco_stop) / preco_entrada) * 100 * alavancagem + (taxa_corretora * 2)
                perda = tamanho_posicao * (perda_pct / 100)
                saldo -= perda
                estado = EstadoDeTrade.DE_FORA
                resultados.update_on_loss(ano, mes, perda_pct)

        elif estado == EstadoDeTrade.VENDIDO:
            if df['low'].iloc[i] <= preco_alvo:
                lucro_pct = ((preco_entrada - preco_alvo) / preco_entrada) * 100 * alavancagem - (taxa_corretora * 2)
                lucro = tamanho_posicao * (lucro_pct / 100)
                saldo += lucro
                estado = EstadoDeTrade.DE_FORA
                resultados.update_on_gain(ano, mes, lucro)
            elif df['high'].iloc[i] >= preco_stop:
                perda_pct = ((preco_stop - preco_entrada) / preco_entrada) * 100 * alavancagem + (taxa_corretora * 2)
                perda = tamanho_posicao * (perda_pct / 100)
                saldo -= perda
                estado = EstadoDeTrade.DE_FORA
                resultados.update_on_loss(ano, mes, perda)

        elif estado == EstadoDeTrade.DE_FORA and trade_count_today < max_trades_per_day:
            # ===== COMPRA AGRESSIVA =====
            if (
                df['RSI'].iloc[i-1] < 30 and
                df['volume'].iloc[i] > df['Volume_EMA_20'].iloc[i] and
                df['high'].iloc[i] > df['high'].iloc[i-1]
            ):
                preco_entrada = df['high'].iloc[i-1] * (1 + slippage_percent)
                preco_stop = preco_entrada - (atr_atual * 2)
                preco_alvo = preco_entrada + (preco_entrada - preco_stop) * risco_retorno
                estado = EstadoDeTrade.COMPRADO
                resultados.update_on_trade_open(ano, mes)
                trade_count_today += 1

            # ===== VENDA AGRESSIVA =====
            elif (
                df['RSI'].iloc[i-1] > 70 and
                df['volume'].iloc[i] > df['Volume_EMA_20'].iloc[i] and
                df['low'].iloc[i] < df['low'].iloc[i-1]
            ):
                preco_entrada = df['low'].iloc[i-1] * (1 - slippage_percent)
                preco_stop = preco_entrada + (atr_atual * 2)
                preco_alvo = preco_entrada - (preco_stop - preco_entrada) * risco_retorno
                estado = EstadoDeTrade.VENDIDO
                resultados.update_on_trade_open(ano, mes)
                trade_count_today += 1

    resultados.get_results()
    return saldo




def otimizar_estrategia(df):
    combinacoes = list(product(
        [5, 8, 9, 13],    # EMA rápida
        [13, 21, 34],     # EMA lenta
        [0.01, 0.05, 0.1, 0.2],  # Risco por trade
        [2.0, 3.0, 5.0, 6.0],    # Risco retorno
        [10, 14, 17],     # Velas stop
        [30, 35, 40],     # RSI min
        [60, 65, 70]      # RSI max
    ))
    resultados = []
    for c in combinacoes:
        if c[0] >= c[1] or c[5] >= c[6]:
            continue
        try:
            final = executar_backtest(df.copy(), *c)
            resultados.append((*c, round(final, 2)))
        except Exception:
            continue
    df_res = pd.DataFrame(resultados, columns=[
        'EMA_rapida', 'EMA_lenta', 'risco_por_trade', 'risco_retorno', 'qntd_velas_stop', 'RSI_min', 'RSI_max', 'saldo_final'
    ])
    print("Top 10 configurações:")
    print(df_res.sort_values(by='saldo_final', ascending=False).head(10))

if __name__ == "__main__":
    df = buscar_dados_historicos()
    otimizar_estrategia(df)

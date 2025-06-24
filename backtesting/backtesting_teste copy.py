import pandas as pd
import numpy as np
from datetime import datetime
from enum import Enum
from pybit.unified_trading import HTTP
from results_manager import ResultsManager

# ===== CONFIGURAÇÕES =====
cripto = 'SOLUSDT'
tempo_grafico = '60'
data_inicio = '2024-01-01'
data_fim = '2024-01-29'
taxa_corretora = 0.055
alavancagem = 2
saldo_inicial = 1000
setup = 'estrategia_real_adaptada_backtest'

class EstadoDeTrade(Enum):
    DE_FORA = 'de fora'
    COMPRADO = 'comprado'
    VENDIDO = 'vendido'

def calcular_atr(df, periodo=40):
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
    velas = []
    tentativas = 0  

    while start_timestamp < end_timestamp:
        resposta = cliente.get_kline(symbol=cripto, interval=tempo_grafico, limit=1000, start=start_timestamp)
        dados = resposta['result']['list']
        if not dados:
            print("Sem dados retornados. Encerrando busca.")
            break
        velas += dados[::-1]
        start_timestamp = int(dados[-1][0]) + 1000
        tentativas += 1
        print(f"Lote {tentativas}: {len(velas)} velas carregadas...")
        if tentativas > 100:
            print("Limite de tentativas atingido. Parando busca para evitar loop infinito.")
            break
    ...

    colunas = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover']
    df = pd.DataFrame(velas, columns=colunas)
    df['open_time'] = pd.to_datetime(df['open_time'].astype(np.int64), unit='ms')
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = df[col].astype(float)
    print(f"Total de velas carregadas: {len(df)}")
    return df

def calcular_indicadores(df):
    print("Calculando indicadores (EMA, RSI, ATR)...")
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['Volume_EMA_20'] = df['volume'].ewm(span=20, adjust=False).mean()
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=14).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs)).fillna(100)
    return df

def executar_backtest(df):
    print("Iniciando backtest...")
    saldo = saldo_inicial
    estado = EstadoDeTrade.DE_FORA
    preco_stop = preco_alvo = preco_entrada = 0
    resultados = ResultsManager(saldo, taxa_corretora, setup, leverage=alavancagem)
    df = calcular_indicadores(df.copy())
    df = calcular_atr(df)

    tamanho_posicao = saldo_inicial * 0.01

    for i in range(60, len(df)):
        ano = df['open_time'].iloc[i].year
        mes = df['open_time'].iloc[i].month
        resultados.initialize_month(ano, mes)
        atr_atual = df['ATR'].iloc[i-1]
        preco_atual = df['close'].iloc[i]

        print(f"\nVela: {df['open_time'].iloc[i]} | Close: {preco_atual:.2f} | Estado: {estado.name}")

        if estado == EstadoDeTrade.COMPRADO:
            print(f"Monitorando posição COMPRADA | Entrada: {preco_entrada:.2f} | Alvo: {preco_alvo:.2f} | Stop: {preco_stop:.2f}")
            if df['high'].iloc[i] >= preco_alvo:
                lucro = tamanho_posicao * ((preco_alvo - preco_entrada) / preco_entrada) * alavancagem
                saldo += lucro
                estado = EstadoDeTrade.DE_FORA
                resultados.update_on_gain(ano, mes, lucro)
                print(f">>> Alvo atingido! Lucro: {lucro:.2f}")
            elif df['low'].iloc[i] <= preco_stop:
                perda = tamanho_posicao * ((preco_entrada - preco_stop) / preco_entrada) * alavancagem
                saldo -= perda
                estado = EstadoDeTrade.DE_FORA
                resultados.update_on_loss(ano, mes, perda)
                print(f">>> Stop Loss atingido! Perda: {perda:.2f}")

        elif estado == EstadoDeTrade.VENDIDO:
            print(f"Monitorando posição VENDIDA | Entrada: {preco_entrada:.2f} | Alvo: {preco_alvo:.2f} | Stop: {preco_stop:.2f}")
            if df['low'].iloc[i] <= preco_alvo:
                lucro = tamanho_posicao * ((preco_entrada - preco_alvo) / preco_entrada) * alavancagem
                saldo += lucro
                estado = EstadoDeTrade.DE_FORA
                resultados.update_on_gain(ano, mes, lucro)
                print(f">>> Alvo atingido! Lucro: {lucro:.2f}")
            elif df['high'].iloc[i] >= preco_stop:
                perda = tamanho_posicao * ((preco_stop - preco_entrada) / preco_entrada) * alavancagem
                saldo -= perda
                estado = EstadoDeTrade.DE_FORA
                resultados.update_on_loss(ano, mes, perda)
                print(f">>> Stop Loss atingido! Perda: {perda:.2f}")

        elif estado == EstadoDeTrade.DE_FORA:
            # COMPRA AGRESSIVA
            if df['RSI'].iloc[i-1] < 30 and df['volume'].iloc[i] > df['Volume_EMA_20'].iloc[i] and df['high'].iloc[i] > df['high'].iloc[i-1]:
                preco_entrada = df['high'].iloc[i-1]
                preco_stop = preco_entrada - (atr_atual * 4)
                preco_alvo = preco_entrada + (preco_entrada - preco_stop) * 5
                if (preco_entrada - preco_stop) >= atr_atual:
                    estado = EstadoDeTrade.COMPRADO
                    resultados.update_on_trade_open(ano, mes)
                    print(f">>> Entrou na COMPRA | Entrada: {preco_entrada:.2f} | Stop: {preco_stop:.2f} | Alvo: {preco_alvo:.2f}")

            # VENDA AGRESSIVA
            elif df['RSI'].iloc[i-1] > 70 and df['volume'].iloc[i] > df['Volume_EMA_20'].iloc[i] and df['low'].iloc[i] < df['low'].iloc[i-1]:
                preco_entrada = df['low'].iloc[i-1]
                preco_stop = preco_entrada + (atr_atual * 4)
                preco_alvo = preco_entrada - (preco_stop - preco_entrada) * 5
                if (preco_stop - preco_entrada) >= atr_atual:
                    estado = EstadoDeTrade.VENDIDO
                    resultados.update_on_trade_open(ano, mes)
                    print(f">>> Entrou na VENDA | Entrada: {preco_entrada:.2f} | Stop: {preco_stop:.2f} | Alvo: {preco_alvo:.2f}")

    print("\n===== Resultado Final =====")
    resultados.get_results()
    return saldo

df = buscar_dados_historicos()
saldo_final = executar_backtest(df)
print(f"\nSaldo final do backtest: {saldo_final:.2f}")

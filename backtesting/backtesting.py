from pybit.unified_trading import HTTP
import pandas as pd
import numpy as np
from datetime import datetime
from enum import Enum
from results_manager import ResultsManager

cliente = HTTP()

# Corrigir data de início para passado
start = '2024-01-01'
end = datetime.now().strftime('%Y-%m-%d')

start_timestamp = int(pd.to_datetime(start).timestamp()) * 1000
end_timestamp = int(pd.to_datetime(end).timestamp()) * 1000

velas_sem_estrutura = []

# Variáveis para o trade
cripto = 'BTCUSDT'
tempo_grafico = '60'
saldo = 1000
risco_retorno = 5.1
qntd_velas_stop = 17
taxa_corretora = 0.055
setup = 'trade estruturado de risco/retorno com duas emas e técnica 9.1 de Larry Williams'
emas = [9, 21]
ema_rapida = emas[0]
ema_lenta = emas[1]
alavancagem = 2
risco_por_trade = 0.01  # 1% do saldo por trade

# Carregar dados históricos
while start_timestamp < end_timestamp:
    resposta = cliente.get_kline(symbol=cripto, interval=tempo_grafico, limit=1000, start=start_timestamp)
    velas_sem_estrutura += resposta['result']['list'][::-1]
    start_timestamp = int(velas_sem_estrutura[-1][0]) + 1000

colunas = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover']
df = pd.DataFrame(velas_sem_estrutura, columns=colunas)

# Função para calcular RSI
def compute_rsi(data, periods=14):
    delta = data.diff()
    gain = delta.where(delta > 0, 0).rolling(window=periods).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=periods).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(100)

# Converter tipos e calcular indicadores
df['open_time'] = pd.to_datetime(df['open_time'].astype(np.int64), unit='ms')
df['open'] = df['open'].astype(float)
df['high'] = df['high'].astype(float)
df['low'] = df['low'].astype(float)
df['close'] = df['close'].astype(float)
df['volume'] = df['volume'].astype(float)

df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
df['RSI'] = compute_rsi(df['close'], 14)
df['Volume_EMA_20'] = df['volume'].ewm(span=20, adjust=False).mean()

# Função ajustada para contar candles consecutivos
def contar_candles_consecutivos(df, index, ema_periodo):
    count_acima = 0
    count_abaixo = 0
    for i in range(index - 1, -1, -1):
        if df['close'].iloc[i] > df[f'EMA_{ema_periodo}'].iloc[i]:
            count_acima += 1
            count_abaixo = 0
        elif df['close'].iloc[i] < df[f'EMA_{ema_periodo}'].iloc[i]:
            count_abaixo += 1
            count_acima = 0
        else:
            break
    return count_acima, count_abaixo

class EstadoDeTrade(Enum):
    DE_FORA = 'de fora'
    COMPRADO = 'comprado'
    VENDIDO = 'vendido'

estado_de_trade = EstadoDeTrade.DE_FORA
preco_stop = 0
preco_alvo = 0
preco_entrada = 0

resultados = ResultsManager(saldo, taxa_corretora, setup)

# Loop de backtesting
for i in range(max(200, qntd_velas_stop) + 1, len(df)):
    ano = df['open_time'].iloc[i].year
    mes = df['open_time'].iloc[i].month
    resultados.initialize_month(ano, mes)

    # Verificar trades abertos
    if estado_de_trade == EstadoDeTrade.COMPRADO:
        if df['high'].iloc[i] >= preco_alvo:
            profit_pct = ((preco_alvo - preco_entrada) / preco_entrada) * 100 * alavancagem - (taxa_corretora * 2)
            saldo += saldo * (profit_pct / 100)
            print(f"Bateu alvo na vela que abriu {df['open_time'].iloc[i]}, Preço: {preco_alvo}, Saldo: {saldo:.2f}")
            estado_de_trade = EstadoDeTrade.DE_FORA
            resultados.update_on_gain(ano, mes, profit_pct)  # Método hipotético para lucro
        elif df['low'].iloc[i] <= preco_stop:
            loss_pct = ((preco_entrada - preco_stop) / preco_entrada) * 100 * alavancagem + (taxa_corretora * 2)
            saldo -= saldo * (loss_pct / 100)
            print(f"Bateu stop na vela que abriu {df['open_time'].iloc[i]}, Preço: {preco_stop}, Saldo: {saldo:.2f}")
            estado_de_trade = EstadoDeTrade.DE_FORA
            resultados.update_on_loss(ano, mes, loss_pct)

    elif estado_de_trade == EstadoDeTrade.VENDIDO:
        if df['low'].iloc[i] <= preco_alvo:
            profit_pct = ((preco_entrada - preco_alvo) / preco_entrada) * 100 * alavancagem - (taxa_corretora * 2)
            saldo += saldo * (profit_pct / 100)
            print(f"Bateu alvo na vela que abriu {df['open_time'].iloc[i]}, Preço: {preco_alvo}, Saldo: {saldo:.2f}")
            estado_de_trade = EstadoDeTrade.DE_FORA
            resultados.update_on_gain(ano, mes, profit_pct)
        elif df['high'].iloc[i] >= preco_stop:
            loss_pct = ((preco_stop - preco_entrada) / preco_entrada) * 100 * alavancagem + (taxa_corretora * 2)
            saldo -= saldo * (loss_pct / 100)
            print(f"Bateu stop na vela que abriu {df['open_time'].iloc[i]}, Preço: {preco_stop}, Saldo: {saldo:.2f}")
            estado_de_trade = EstadoDeTrade.DE_FORA
            resultados.update_on_loss(ano, mes, loss_pct)

    # Verificar novas entradas
    elif estado_de_trade == EstadoDeTrade.DE_FORA:
        count_acima, count_abaixo = contar_candles_consecutivos(df, i, ema_rapida)
        
        # Compra
        if (count_acima >= 9 and
            df['close'].iloc[i-1] > df['EMA_9'].iloc[i-1] and
            df['close'].iloc[i-1] > df['EMA_21'].iloc[i-1] and
            df['close'].iloc[i-1] > df['EMA_200'].iloc[i-1] and
            df['RSI'].iloc[i] < 70 and
            df['volume'].iloc[i] > df['Volume_EMA_20'].iloc[i] and
            df['high'].iloc[i] > df['high'].iloc[i-1]):
            preco_entrada = df['high'].iloc[i-1]
            preco_stop = df['low'].iloc[i - qntd_velas_stop:i].min()
            risco = (preco_entrada - preco_stop) / preco_entrada
            tamanho_posicao = (saldo * risco_por_trade) / (risco * alavancagem)
            preco_alvo = preco_entrada + (preco_entrada - preco_stop) * risco_retorno
            estado_de_trade = EstadoDeTrade.COMPRADO
            print(f"Compra na vela que abriu {df['open_time'].iloc[i]}, Entrada: {preco_entrada}, Stop: {preco_stop}, Alvo: {preco_alvo}, Tamanho: {tamanho_posicao:.2f}")
            resultados.update_on_trade_open(ano, mes)

        # Venda
        elif (count_abaixo >= 9 and
              df['close'].iloc[i-1] < df['EMA_9'].iloc[i-1] and
              df['close'].iloc[i-1] < df['EMA_21'].iloc[i-1] and
              df['close'].iloc[i-1] < df['EMA_200'].iloc[i-1] and
              df['RSI'].iloc[i] > 30 and
              df['volume'].iloc[i] > df['Volume_EMA_20'].iloc[i] and
              df['low'].iloc[i] < df['low'].iloc[i-1]):
            preco_entrada = df['low'].iloc[i-1]
            preco_stop = df['high'].iloc[i - qntd_velas_stop:i].max()
            risco = (preco_stop - preco_entrada) / preco_entrada
            tamanho_posicao = (saldo * risco_por_trade) / (risco * alavancagem)
            preco_alvo = preco_entrada - (preco_stop - preco_entrada) * risco_retorno
            estado_de_trade = EstadoDeTrade.VENDIDO
            print(f"Venda na vela que abriu {df['open_time'].iloc[i]}, Entrada: {preco_entrada}, Stop: {preco_stop}, Alvo: {preco_alvo}, Tamanho: {tamanho_posicao:.2f}")
            resultados.update_on_trade_open(ano, mes)
            
            #testando

resultados.get_results()
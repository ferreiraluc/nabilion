from pybit.unified_trading import HTTP
import pandas as pd
import numpy as np
from datetime import datetime
from enum import Enum
from results_manager import ResultsManager

cliente = HTTP()

start = '2025-03-01'
#end = '2024-12-31'
end = datetime.now().strftime('%Y-%m-%d')

start_timestamp = int(pd.to_datetime(start).timestamp()) * 1000
end_timestamp = int(pd.to_datetime(end).timestamp()) * 1000

velas_sem_estrutura = []

# variaveis para o trade
cripto = 'SOLUSDT'
tempo_grafico = '1'
saldo = 1000
risco_retorno = 1.3
qntd_velas_stop = 34
taxa_corretora = 0.055
setup = 'trade estruturado de risco/retorno com duas emas'


while start_timestamp < end_timestamp:
    resposta = cliente.get_kline(symbol=cripto, interval=tempo_grafico, limit=1000, start=start_timestamp)
    velas_sem_estrutura += resposta['result']['list'][::-1]
    start_timestamp = int(velas_sem_estrutura[-1][0]) + 1000

colunas = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover']

df = pd.DataFrame(velas_sem_estrutura, columns=colunas)

df['open_time'] = pd.to_datetime(df['open_time'].astype(np.int64), unit='ms')
df['open'] = df['open'].astype(float)
df['high'] = df['high'].astype(float)
df['low'] = df['low'].astype(float)
df['close'] = df['close'].astype(float)
df['volume'] = df['volume'].astype(float)


df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()

print(df) 


def calcula_percentual_perda_na_compra(preco_compra, preco_stop):
    return ((preco_compra - preco_stop) / preco_compra) * 100 

def calcula_percentual_lucro_na_compra(preco_compra, preco_alvo):
    return ((preco_alvo - preco_compra) / preco_compra) * 100

class EstadoDeTrade(Enum):
    DE_FORA = 'de fora'
    COMPRADO = 'comprado'
    VENDIDO = 'vendido'

estado_de_trade = EstadoDeTrade.DE_FORA

preco_stop = 0
preco_alvo = 0
preco_entrada = 0

resultados = ResultsManager(saldo, taxa_corretora, setup)


for i in range(999, len(df)):
    ano = df['open_time'].iloc[i].year
    mes = df['open_time'].iloc[i].month
    
    resultados.initialize_month(ano, mes)
        
    # if estado_de_trade == EstadoDeTrade.VENDIDO:
    #    if df['low'].iloc[i] <= preco_alvo:
    #        print('vendeu no preco: ', preco_alvo)
    #    elif df['high'].iloc[i] >= preco_stop:
    #        print('vendeu no preco: ', preco_stop)
    # elif estado_de_trade == EstadoDeTrade.COMPRADO:
    if estado_de_trade == EstadoDeTrade.COMPRADO:
        if df['high'].iloc[i] >= preco_alvo:
            estado_de_trade = EstadoDeTrade.DE_FORA
            percentual_ganho = calcula_percentual_lucro_na_compra(preco_entrada, preco_alvo)
            saldo = saldo + (saldo*(percentual_ganho / 100))
            print("vendeu no preco: ", preco_alvo)
            print("fechou no alvo em: ", df['open_time'].iloc[i])
            print("saldo:", saldo )
            print('--------------------------------------')
            
        elif df['low'].iloc[i] <= preco_stop: 
            estado_de_trade = EstadoDeTrade.DE_FORA
            percentual_perda = calcula_percentual_perda_na_compra(preco_entrada, preco_stop)
            saldo = saldo - (saldo*(percentual_perda / 100))
            print("vendeu no preco: ", preco_stop)
            print("fechou no stop em: ", df['open_time'].iloc[i])
            print("saldo:", saldo )
            print('--------------------------------------')
            resultados.update_on_loss(ano, mes, percentual_perda)
            
    # logica para buscar compras:    
    elif estado_de_trade == EstadoDeTrade.DE_FORA:
        print('Procurando trades de compra...')
        # Logica para buscar compras
        if df['close'].iloc[i-1] > df['EMA_200'].iloc[i-1]:
            
            # Logica para buscar a vela referencia 
            if df['close'].iloc[i-1] > df['EMA_9'].iloc[i-1] and df['close'].iloc[i-1] > df['EMA_21'].iloc[i-1]:
            # Logica para buscar o gatilho de compra
                if df['high'].iloc[i] > df['high'].iloc[i-1]:
                    preco_entrada = df['high'].iloc[i-1]
                    print("preco de compra: ", preco_entrada)
                    print("comprou na vela que abriu em: ", df['open_time'].iloc[i])
                    estado_de_trade = EstadoDeTrade.COMPRADO
                    preco_stop = df['low'].iloc[i - qntd_velas_stop : i].min()
                    print("preco stop: ", preco_stop)
                    preco_alvo = ((preco_entrada - preco_stop) * risco_retorno) + preco_entrada
                    print("preco alvo: ", preco_alvo)
                    print('--------------------------------------')
                    resultados.update_on_trade_open(ano, mes)
        # Logica para buscar vendas
        # elif df['close'].iloc[i-1] < df['EMA_200'].iloc[i-1]:

resultados.get_results()

        #     if df['close'].iloc[i-1] < df['EMA_9'].iloc[i-1] and df['close'].iloc[i-1] < df['EMA_21'].iloc[i-1]:
        #         if df['low'].iloc[i] < df['low'].iloc[i-1]:
        #             preco_entrada = df['low'].iloc[i-1]
        #             print("preco de venda: ", preco_entrada)
        #             print("vendeu na vela que abriu em: ", df['open_time'].iloc[i])
        #             estado_de_trade = EstadoDeTrade.VENDIDO
        #             preco_stop = df['high'].iloc[i - qntd_velas_stop : i].max()
        #             print("preco stop: ", preco_stop)
        #             preco_alvo = preco_entrada - ((preco_stop - preco_entrada) * risco_retorno)
        #             print("preco alvo: ", preco_alvo)
        #             print('--------------------------------------')
            
                
                
                
    

        
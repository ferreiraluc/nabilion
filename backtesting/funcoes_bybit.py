from pybit.unified_trading import HTTP
import pandas as pd 
import numpy as np 
from estado_trade import EstadoDeTrade
from dotenv import load_dotenv
import os   


load_dotenv()

API_KEY = os.getenv('BYBIT_API_KEY')
SECRET_KEY = os.getenv('BYBIT_API_SECRET')

cliente = HTTP(api_key=API_KEY, api_secret=SECRET_KEY)

def busca_velas(cripto, tempo_grafico, emas):
    resposta = cliente.get_kline(symbol=cripto, interval=tempo_grafico, limit=1000) 
    velas_sem_estrutura = resposta['result']['list'][::-1]  
    
    colunas = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover']
    df = pd.DataFrame(velas_sem_estrutura, columns=colunas)
    
    df['open_time'] = pd.to_datetime(df['open_time'].astype(np.int64), unit='ms')
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    
    ema_rapida = emas[0]
    ema_lenta = emas[1]
    df[f'EMA_{ema_rapida}'] = df['close'].ewm(span=ema_rapida, adjust=False).mean()
    df[f'EMA_{ema_lenta}'] = df['close'].ewm(span=ema_lenta, adjust=False).mean()
    df['EMA_200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    #Calcular RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(span=14).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(span=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    df['Volume_EMA_20'] = df['volume'].ewm(span=20, adjust=False).mean()
    
    return df

def tem_trade_aberto(cripto):
    resposta = cliente.get_positions(category='linear', symbol=cripto, recv_window=50000)
    dados = resposta['result']['list'][0]

    preco_entrada = dados['avgPrice']
    if preco_entrada == '':
        preco_entrada = 0
    else:
        preco_entrada = float(preco_entrada)
    
    preco_stop = dados['stopLoss']
    if preco_stop == '':
        preco_stop = 0
    else:
        preco_stop = float(preco_stop)

    preco_alvo = dados['takeProfit']
    if preco_alvo == '':
        preco_alvo = 0
    else:
        preco_alvo = float(preco_alvo)

    estado_de_trade = dados['side']
    if estado_de_trade == '':
        estado_de_trade = EstadoDeTrade.DE_FORA
    elif estado_de_trade == 'Buy':
        estado_de_trade = EstadoDeTrade.COMPRADO
    elif estado_de_trade == 'Sell':
        estado_de_trade = EstadoDeTrade.VENDIDO

    return estado_de_trade, preco_entrada, preco_stop, preco_alvo

def saldo_da_conta():
    resposta = cliente.get_wallet_balance(accountType='UNIFIED', coin='USDT')
    saldo_em_usdt = resposta['result']['list'][0]['coin'][0]['walletBalance']
    return float(saldo_em_usdt)

def quantidade_minima_para_operar(cripto):
    resposta = cliente.get_instruments_info(category='linear', symbol=cripto)
    quantidade_minima_para_operar = resposta['result']['list'][0]['lotSizeFilter']['minOrderQty']
    return float(quantidade_minima_para_operar)


def abre_compra(cripto, qtd_cripto_para_operar, preco_stop, preco_alvo):
    cliente.place_order(
        category='linear',
        symbol=cripto,  
        side='Buy',
        orderType='Market',
        qty=qtd_cripto_para_operar,
        stopLoss=preco_stop,
        takeProfit=preco_alvo
    )
    
# def abre_compra_spot(cripto):
#     cliente.place_order(
#         category='spot',
#         symbol=cripto,  
#         side='Buy',
#         orderType='Market',
#         qty=10
#     )
    
def abre_venda(cripto, qtd_cripto_para_operar, preco_stop, preco_alvo):
    cliente.place_order(
        category='linear',
        symbol=cripto,
        side='Sell',
        orderType='Market',
        qty=qtd_cripto_para_operar,
        stopLoss=preco_stop,
        takeProfit=preco_alvo
    )
    
def set_leverage(cliente):
    try:
        resposta = cliente.set_leverage(
            category='linear',  # Para contratos perpétuos USDT
            symbol='BTCUSDT',
            buyLeverage=10,  # Alavancagem para compra
            sellLeverage=10  # Alavancagem para venda
        )
        print(f"Alavancagem configurada para 10x no símbolo BTCUSDT", flush=True)
        return resposta
    except Exception as e:
        print(f"Erro ao configurar a alavancagem: {e}", flush=True)
        return None
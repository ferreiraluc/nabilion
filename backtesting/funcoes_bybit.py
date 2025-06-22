from pybit.unified_trading import HTTP
import pandas as pd 
import numpy as np 
from estado_trade import EstadoDeTrade
from dotenv import load_dotenv
import os   
from utilidades import ajusta_start_time
from data_loader import obter_caminho_velas, carregar_velas_json, salvar_velas_json



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
    
def carregar_dados_historicos(cripto, tempo_grafico, emas, start, end, pular_velas=999):
    start_ajustado = ajusta_start_time(start, tempo_grafico, pular_velas)
    start_timestamp = int(pd.to_datetime(start_ajustado).timestamp() * 1000)
    end_timestamp =  int(pd.to_datetime(end).timestamp() * 1000)

    caminho_arquivo = obter_caminho_velas(cripto, tempo_grafico, start, end)
    velas_sem_estrutura = carregar_velas_json(caminho_arquivo)

    if velas_sem_estrutura is None:
        velas_sem_estrutura = []

        while start_timestamp < end_timestamp:
            resposta = cliente.get_kline(symbol=cripto, interval=tempo_grafico, limit=1000, start=start_timestamp)
            velas_sem_estrutura += resposta['result']['list'][::-1]
            start_timestamp = int(velas_sem_estrutura[-1][0]) + 1000

        salvar_velas_json(caminho_arquivo, velas_sem_estrutura)

    colunas = ['tempo_abertura', 'abertura', 'maxima', 'minima', 'fechamento', 'volume', 'turnover']

    df = pd.DataFrame(velas_sem_estrutura, columns=colunas)

    df['tempo_abertura'] = pd.to_datetime(df['tempo_abertura'].astype(np.int64), unit='ms')
    df['abertura'] = df['abertura'].astype(float)
    df['maxima'] = df['maxima'].astype(float)
    df['minima'] = df['minima'].astype(float)
    df['fechamento'] = df['fechamento'].astype(float)
    df['volume'] = df['volume'].astype(float)

    ema_rapida = emas[0]
    ema_lenta = emas[1]
    df[f'EMA_{ema_rapida}'] = df['fechamento'].ewm(span=ema_rapida, adjust=False).mean()
    df[f'EMA_{ema_lenta}'] = df['fechamento'].ewm(span=ema_lenta, adjust=False).mean()
    return df

def reduzir_posicao(cripto, percentual):
    try:
        posicoes = cliente.get_positions(category="linear", symbol=cripto)['result']['list']
        for pos in posicoes:
            if float(pos['size']) > 0:
                tamanho_atual = float(pos['size'])
                quantidade_para_fechar = tamanho_atual * percentual
                lado = 'Sell' if pos['side'] == 'Buy' else 'Buy'

                cliente.place_order(
                    category="linear",
                    symbol=cripto,
                    side=lado,
                    order_type="Market",
                    qty=round(quantidade_para_fechar, 3),
                    reduce_only=True
                )

                print(f"Reduziu {percentual * 100}% da posição de {cripto} via mercado.")
    except Exception as e:
        print(f"Erro ao tentar reduzir posição: {e}")


def abre_parcial_compra(cripto, quantidade_total, preco_entrada):
    try:
        # Calcular preço de 5% acima do preço de entrada
        preco_parcial = preco_entrada * 1.05

        # Calculando 50% da posição
        quantidade_parcial = round(quantidade_total * 0.5, 3)  # Ajusta para 3 casas decimais por segurança

        # Cria a ordem de Take Profit para os 50% da mão
        print(f'Criando ordem de take profit para 50% da mão em {preco_parcial}', flush=True)
        cliente.place_order(
            category="linear",
            symbol=cripto,
            side="Sell",
            orderType="Limit",
            qty=quantidade_parcial,
            price=round(preco_parcial, 4),
            timeInForce="GTC",
            reduceOnly=True
        )

    except Exception as e:
        print(f'Erro ao configurar ordem parcial ou stop break even: {e}', flush=True)


def abre_parcial_venda(cripto, quantidade_total, preco_entrada):
    try:
        # Calcular preço 5% abaixo do preço de entrada
        preco_parcial = preco_entrada * 0.95

        # Calculando 50% da posição
        quantidade_parcial = round(quantidade_total * 0.5, 3)  # Ajuste para 3 casas decimais

        # Criar ordem de Take Profit para os 50% da mão
        print(f'Criando ordem de take profit para 50% da mão em {preco_parcial}', flush=True)
        cliente.place_order(
            category="linear",
            symbol=cripto,
            side="Buy",  # Estamos vendidos, então a saída parcial é uma COMPRA
            orderType="Limit",
            qty=quantidade_parcial,
            price=round(preco_parcial, 4),
            timeInForce="GTC",
            reduceOnly=True
        )

    except Exception as e:
        print(f'Erro ao configurar ordem parcial ou stop break even na venda: {e}', flush=True)

def stop_breakeven_compra(cripto, preco_entrada, preco_parcial, estado_trade, preco_atual):
    try:
        if estado_trade == EstadoDeTrade.COMPRADO:
            if preco_atual >= preco_parcial:
                print(f'Preço atual {preco_atual} já atingiu a parcial de 5%. Movendo stop para break even: {preco_entrada}', flush=True)
                cliente.set_trading_stop(
                    category="linear",
                    symbol=cripto,
                    stopLoss=round(preco_entrada, 4)
                )
                return True
    except Exception as e:
        print(f'Erro ao verificar e subir stop para break even: {e}', flush=True)

    return False


def stop_breakeven_venda(cripto, preco_entrada, preco_parcial, estado_trade, preco_atual):
    try:
        if estado_trade == EstadoDeTrade.VENDIDO:
            if preco_atual <= preco_parcial:
                print(f'Preço atual {preco_atual} já atingiu a parcial de -5%. Movendo stop para break even: {preco_entrada}', flush=True)
                cliente.set_trading_stop(
                    category="linear",
                    symbol=cripto,
                    stopLoss=round(preco_entrada, 4)
                )
                return True
    except Exception as e:
        print(f'Erro ao verificar e subir stop para break even na venda: {e}', flush=True)

    return False



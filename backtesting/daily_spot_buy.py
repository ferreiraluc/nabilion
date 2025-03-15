from pybit.unified_trading import HTTP
from datetime import datetime
import time
from dotenv import load_dotenv
import os
from funcoes_bybit import saldo_da_conta, abre_compra_spot  # Funções usadas

# Carregar variáveis de ambiente
load_dotenv()
API_KEY = os.getenv('BYBIT_API_KEY')
SECRET_KEY = os.getenv('BYBIT_API_SECRET')
cliente = HTTP(api_key=API_KEY, api_secret=SECRET_KEY)

# Configurações
cripto = 'BTCUSDT'
VALOR_COMPRA = 10  # Valor fixo em USDT para a compra diária

# Função para obter o preço atual usando o orderbook
def get_current_price(cripto):
    try:
        orderbook = cliente.get_orderbook(category='spot', symbol=cripto)
        bid_price = float(orderbook['result']['b'][0][0])  # Melhor preço de compra
        ask_price = float(orderbook['result']['a'][0][0])  # Melhor preço de venda
        last_price = (bid_price + ask_price) / 2  # Média para o preço atual
        print(f"Preço atual:{last_price} ",flush=True)
        return last_price
    except Exception as e:
        print(f"Erro ao obter o preço atual: {e}", flush=True)
        return None

# Função principal
def main():
    ultimo_dia_compra = None
    print("Robo de compra diaria na spot iniciado...", flush=True)
    
    while True:
        agora = datetime.now()
        dia_atual = agora.date()
        
        # Verifica se já comprou hoje
        if ultimo_dia_compra != dia_atual:
            try:
                # Obtém o preço atual
                preco_atual = get_current_price(cripto)
                if preco_atual is None:
                    print("Não conseguiu obter o preço atual. Tentando novamente em 1 hora...", flush=True)
                    time.sleep(3600)
                    continue
                
                # Verifica o saldo
                saldo = saldo_da_conta()
                if saldo < VALOR_COMPRA:
                    print(f"Saldo insuficiente: {saldo} USDT < {VALOR_COMPRA} USDT", flush=True)
                    time.sleep(3600)
                    continue
                
                # Calcula a quantidade a comprar
                qtd_cripto = VALOR_COMPRA / preco_atual
                qtd_cripto_str = f"{qtd_cripto:.8f}"
                
                # Executa a compra
                abre_compra_spot(cripto)  # Note que qty=10 está fixo na função, ajustaremos isso
                print(f"Compra realizada em {agora}: {qtd_cripto_str} {cripto} por {VALOR_COMPRA} USDT", flush=True)
                ultimo_dia_compra = dia_atual  # Marca o dia como comprado
                
            except Exception as e:
                erro_str = str(e).encode('cp1252', errors='replace').decode('cp1252')
                print(f"Erro ao realizar compra: {erro_str}", flush=True)
        
        # Aguarda 1 hora antes da próxima verificação
        time.sleep(3600)

if __name__ == "__main__":
    main()
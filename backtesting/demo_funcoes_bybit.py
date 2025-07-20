# demo_funcoes_bybit.py - Funções adaptadas para demo Bybit
from pybit.unified_trading import HTTP
import pandas as pd
import numpy as np
from estado_trade import EstadoDeTrade
import logging
from dotenv import load_dotenv
import os

load_dotenv()

class DemoBybitFunctions:
    def __init__(self):
        # Credenciais demo
        self.API_KEY = os.getenv('BYBIT_DEMO_KEY')
        self.SECRET_KEY = os.getenv('BYBIT_DEMO_SECRET')
        
        # Cliente demo
        self.cliente = HTTP(
            testnet=True,
            demo=True,
            api_key=self.API_KEY,
            api_secret=self.SECRET_KEY
        )
    
    def busca_velas(self, cripto, tempo_grafico, emas):
        """Busca velas da API demo"""
        try:
            resposta = self.cliente.get_kline(
                category="linear",
                symbol=cripto,
                interval=tempo_grafico,
                limit=200
            )
            
            # Processar dados
            velas = []
            for kline in reversed(resposta['result']['list']):
                velas.append([
                    kline[0],  # timestamp
                    kline[1],  # open
                    kline[2],  # high
                    kline[3],  # low
                    kline[4],  # close
                    kline[5],  # volume
                    kline[6]   # turnover
                ])
            
            colunas = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover']
            df = pd.DataFrame(velas, columns=colunas)
            
            # Converter tipos
            df['open_time'] = pd.to_datetime(df['open_time'].astype(np.int64), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # Calcular EMAs
            ema_rapida, ema_lenta = emas
            df[f'EMA_{ema_rapida}'] = df['close'].ewm(span=ema_rapida).mean()
            df[f'EMA_{ema_lenta}'] = df['close'].ewm(span=ema_lenta).mean()
            df['EMA_200'] = df['close'].ewm(span=200).mean()
            
            # RSI
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = -delta.where(delta < 0, 0).rolling(14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))
            
            # Volume EMA
            df['Volume_EMA_20'] = df['volume'].ewm(span=20).mean()
            
            return df
            
        except Exception as e:
            logging.error(f"Erro ao buscar velas: {e}")
            return pd.DataFrame()
    
    def tem_trade_aberto(self, cripto):
        """Verifica se há trade aberto na demo"""
        try:
            positions = self.cliente.get_positions(
                category="linear",
                symbol=cripto
            )
            
            for pos in positions['result']['list']:
                size = float(pos['size'])
                if size != 0:
                    side = pos['side']
                    avg_price = float(pos['avgPrice'])
                    stop_loss = float(pos['stopLoss']) if pos['stopLoss'] else 0
                    take_profit = float(pos['takeProfit']) if pos['takeProfit'] else 0
                    
                    if side == 'Buy':
                        estado = EstadoDeTrade.COMPRADO
                    else:
                        estado = EstadoDeTrade.VENDIDO
                    
                    return estado, avg_price, stop_loss, take_profit
            
            return EstadoDeTrade.DE_FORA, 0, 0, 0
            
        except Exception as e:
            logging.error(f"Erro ao verificar trade: {e}")
            return EstadoDeTrade.DE_FORA, 0, 0, 0
    
    def saldo_da_conta(self):
        """Retorna saldo da conta demo"""
        try:
            balance = self.cliente.get_wallet_balance(accountType="UNIFIED")
            saldo = float(balance['result']['list'][0]['totalWalletBalance'])
            return saldo
        except Exception as e:
            logging.error(f"Erro ao obter saldo: {e}")
            return 0
    
    def quantidade_minima_para_operar(self, cripto):
        """Retorna quantidade mínima para operar"""
        try:
            instruments = self.cliente.get_instruments_info(
                category="linear",
                symbol=cripto
            )
            
            min_qty = float(instruments['result']['list'][0]['lotSizeFilter']['minOrderQty'])
            return min_qty
            
        except Exception as e:
            logging.error(f"Erro ao obter quantidade mínima: {e}")
            # Fallback para criptos comuns
            if 'BTC' in cripto:
                return 0.001
            elif 'ETH' in cripto:
                return 0.01
            elif 'XRP' in cripto:
                return 0.1
            else:
                return 1.0
    
    def abre_compra(self, cripto, quantidade, preco_stop, preco_alvo):
        """Abre posição de compra na demo"""
        try:
            order = self.cliente.place_order(
                category="linear",
                symbol=cripto,
                side="Buy",
                orderType="Market",
                qty=str(quantidade),
                stopLoss=str(preco_stop),
                takeProfit=str(preco_alvo)
            )
            
            logging.info(f"✅ Compra executada: {quantidade} {cripto}")
            return order
            
        except Exception as e:
            logging.error(f"❌ Erro ao abrir compra: {e}")
            return None
    
    def abre_venda(self, cripto, quantidade, preco_stop, preco_alvo):
        """Abre posição de venda na demo"""
        try:
            order = self.cliente.place_order(
                category="linear",
                symbol=cripto,
                side="Sell",
                orderType="Market",
                qty=str(quantidade),
                stopLoss=str(preco_stop),
                takeProfit=str(preco_alvo)
            )
            
            logging.info(f"✅ Venda executada: {quantidade} {cripto}")
            return order
            
        except Exception as e:
            logging.error(f"❌ Erro ao abrir venda: {e}")
            return None
    
    def abre_parcial_compra(self, cripto, quantidade_total, preco_entrada):
        """Configura take profit parcial para compra"""
        try:
            quantidade_parcial = quantidade_total * 0.5
            preco_parcial = preco_entrada * 1.01  # 1% de lucro
            
            order = self.cliente.place_order(
                category="linear",
                symbol=cripto,
                side="Sell",
                orderType="Limit",
                qty=str(quantidade_parcial),
                price=str(preco_parcial),
                timeInForce="GTC",
                reduceOnly=True
            )
            
            logging.info(f"✅ Take profit parcial configurado: 50% @ ${preco_parcial:.4f}")
            return order
            
        except Exception as e:
            logging.error(f"❌ Erro ao configurar take profit parcial: {e}")
            return None
    
    def abre_parcial_venda(self, cripto, quantidade_total, preco_entrada):
        """Configura take profit parcial para venda"""
        try:
            quantidade_parcial = quantidade_total * 0.5
            preco_parcial = preco_entrada * 0.99  # 1% de lucro
            
            order = self.cliente.place_order(
                category="linear",
                symbol=cripto,
                side="Buy",
                orderType="Limit",
                qty=str(quantidade_parcial),
                price=str(preco_parcial),
                timeInForce="GTC",
                reduceOnly=True
            )
            
            logging.info(f"✅ Take profit parcial configurado: 50% @ ${preco_parcial:.4f}")
            return order
            
        except Exception as e:
            logging.error(f"❌ Erro ao configurar take profit parcial: {e}")
            return None
    
    def stop_breakeven_compra(self, cripto, preco_entrada, preco_parcial, estado_trade, preco_atual):
        """Move stop para breakeven em compra"""
        try:
            if estado_trade == EstadoDeTrade.COMPRADO and preco_atual >= preco_parcial:
                
                response = self.cliente.set_trading_stop(
                    category="linear",
                    symbol=cripto,
                    stopLoss=str(preco_entrada)
                )
                
                if response['retCode'] == 0:
                    logging.info(f"✅ Stop movido para breakeven: ${preco_entrada:.4f}")
                    return True
                elif response['retCode'] == 34040:
                    logging.info("ℹ️ Stop já estava no breakeven")
                    return True
                else:
                    logging.warning(f"⚠️ Erro ao mover stop: {response}")
                    
            return False
            
        except Exception as e:
            logging.error(f"❌ Erro no stop breakeven: {e}")
            return False
    
    def stop_breakeven_venda(self, cripto, preco_entrada, preco_parcial, estado_trade, preco_atual):
        """Move stop para breakeven em venda"""
        try:
            if estado_trade == EstadoDeTrade.VENDIDO and preco_atual <= preco_parcial:
                
                response = self.cliente.set_trading_stop(
                    category="linear",
                    symbol=cripto,
                    stopLoss=str(preco_entrada)
                )
                
                if response['retCode'] == 0:
                    logging.info(f"✅ Stop movido para breakeven: ${preco_entrada:.4f}")
                    return True
                elif response['retCode'] == 34040:
                    logging.info("ℹ️ Stop já estava no breakeven")
                    return True
                else:
                    logging.warning(f"⚠️ Erro ao mover stop: {response}")
                    
            return False
            
        except Exception as e:
            logging.error(f"❌ Erro no stop breakeven: {e}")
            return False

# Instância global para compatibilidade
demo_funcoes = DemoBybitFunctions()

# Funções wrapper para compatibilidade com código existente
def busca_velas(cripto, tempo_grafico, emas):
    return demo_funcoes.busca_velas(cripto, tempo_grafico, emas)

def tem_trade_aberto(cripto):
    return demo_funcoes.tem_trade_aberto(cripto)

def saldo_da_conta():
    return demo_funcoes.saldo_da_conta()

def quantidade_minima_para_operar(cripto):
    return demo_funcoes.quantidade_minima_para_operar(cripto)

def abre_compra(cripto, quantidade, preco_stop, preco_alvo):
    return demo_funcoes.abre_compra(cripto, quantidade, preco_stop, preco_alvo)

def abre_venda(cripto, quantidade, preco_stop, preco_alvo):
    return demo_funcoes.abre_venda(cripto, quantidade, preco_stop, preco_alvo)

def abre_parcial_compra(cripto, quantidade_total, preco_entrada):
    return demo_funcoes.abre_parcial_compra(cripto, quantidade_total, preco_entrada)

def abre_parcial_venda(cripto, quantidade_total, preco_entrada):
    return demo_funcoes.abre_parcial_venda(cripto, quantidade_total, preco_entrada)

def stop_breakeven_compra(cripto, preco_entrada, preco_parcial, estado_trade, preco_atual):
    return demo_funcoes.stop_breakeven_compra(cripto, preco_entrada, preco_parcial, estado_trade, preco_atual)

def stop_breakeven_venda(cripto, preco_entrada, preco_parcial, estado_trade, preco_atual):
    return demo_funcoes.stop_breakeven_venda(cripto, preco_entrada, preco_parcial, estado_trade, preco_atual)
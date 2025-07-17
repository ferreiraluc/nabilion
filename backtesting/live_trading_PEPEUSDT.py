from pybit.unified_trading import HTTP
from estado_trade import EstadoDeTrade
from funcoes_bybit import busca_velas, tem_trade_aberto, saldo_da_conta, quantidade_minima_para_operar, abre_compra, abre_venda, abre_parcial_venda, abre_parcial_compra, stop_breakeven_compra, stop_breakeven_venda
from utilidades import quantidade_cripto_para_operar
import time
from dotenv import load_dotenv
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

load_dotenv()

API_KEY = os.getenv('BYBIT_API_KEY')
SECRET_KEY = os.getenv('BYBIT_API_SECRET')

cliente = HTTP(api_key=API_KEY, api_secret=SECRET_KEY)

# ===== CONFIGURAÇÕES APRIMORADAS =====
cripto = '1000PEPEUSDT'
tempo_grafico = '15'
qtd_velas_stop = 17
risco_retorno = 2.5
emas = [9, 21]
ema_rapida = emas[0]
ema_lenta = emas[1]
alavancagem = 2

# ===== PARÂMETROS QUANTITATIVOS PARA REVERSÕES =====
# Períodos para análise multi-timeframe
tf_principal = '15'  # Timeframe principal
tf_confirmacao = '60'  # Timeframe de confirmação (1h)

# Configurações de filtros para reversões - OTIMIZADAS
rsi_periodo = 14
adx_periodo = 14
volume_ma_periodo = 20

# Thresholds para detecção de reversões - MAIS PERMISSIVOS
rsi_oversold_reversao = 45  # Muito mais permissivo (era 30)
rsi_overbought_reversao = 55  # Muito mais permissivo (era 70)
adx_forte = 25
volume_threshold = 0.8  # MUITO permissivo: aceita volume 80% da média (era 1.5x)

# Configurações do contador de velas para reversões - MAIS FLEXÍVEL
min_velas_consecutivas = 2  # Reduzido para 2 velas (era 4)
max_velas_consecutivas = 15  # Aumentado (era 10)

# Configurações de Score System para reversões - MAIS PERMISSIVO
score_minimo_entrada = 4  # Reduzido para 4 (era 6)
score_maximo = 10  # Score máximo possível

print('🔧 Bot Quantitativo de Reversões - OTIMIZADO', flush=True)
print(f'Cripto: {cripto}', flush=True)
print(f'Timeframe Principal: {tf_principal}', flush=True)
print(f'Timeframe Confirmação: {tf_confirmacao}', flush=True)
print(f'Score Mínimo para Entrada: {score_minimo_entrada}/{score_maximo}', flush=True)
print(f'RSI Oversold: < {rsi_oversold_reversao}', flush=True)
print(f'RSI Overbought: > {rsi_overbought_reversao}', flush=True)
print(f'Volume Threshold: {volume_threshold}x', flush=True)
print(f'Detecção de Reversões: {min_velas_consecutivas}-{max_velas_consecutivas} velas consecutivas', flush=True)

# ===== INDICADORES QUANTITATIVOS PARA REVERSÕES =====
def calcular_atr(df, periodo=14):
    """Calcula Average True Range otimizado"""
    df['high_low'] = df['high'] - df['low']
    df['high_close'] = abs(df['high'] - df['close'].shift())
    df['low_close'] = abs(df['low'] - df['close'].shift())
    df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
    df['ATR'] = df['tr'].rolling(window=periodo).mean()
    return df

def calcular_adx(df, periodo=14):
    """Calcula Average Directional Index - força da tendência"""
    df['high_diff'] = df['high'].diff()
    df['low_diff'] = df['low'].diff()
    
    df['plus_dm'] = np.where((df['high_diff'] > df['low_diff']) & (df['high_diff'] > 0), df['high_diff'], 0)
    df['minus_dm'] = np.where((df['low_diff'] > df['high_diff']) & (df['low_diff'] > 0), df['low_diff'], 0)
    
    df['plus_di'] = 100 * (df['plus_dm'].rolling(window=periodo).sum() / df['ATR'].rolling(window=periodo).sum())
    df['minus_di'] = 100 * (df['minus_dm'].rolling(window=periodo).sum() / df['ATR'].rolling(window=periodo).sum())
    
    df['dx'] = 100 * abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])
    df['ADX'] = df['dx'].rolling(window=periodo).mean()
    
    return df

def contar_velas_consecutivas(df):
    """Conta velas consecutivas verdes (compra) ou vermelhas (venda) para reversões"""
    if len(df) < 10:
        return 0, 0
    
    velas_verdes_consecutivas = 0
    velas_vermelhas_consecutivas = 0
    
    # Conta velas verdes consecutivas (close > open)
    for i in range(len(df) - 1, -1, -1):
        if df['close'].iloc[i] > df['open'].iloc[i]:
            velas_verdes_consecutivas += 1
        else:
            break
    
    # Conta velas vermelhas consecutivas (close < open)
    for i in range(len(df) - 1, -1, -1):
        if df['close'].iloc[i] < df['open'].iloc[i]:
            velas_vermelhas_consecutivas += 1
        else:
            break
    
    return velas_verdes_consecutivas, velas_vermelhas_consecutivas

def buscar_dados_multi_timeframe(cripto, tf_principal, tf_confirmacao, emas):
    """Busca dados em múltiplos timeframes para análise confirmatória"""
    try:
        # Dados do timeframe principal
        df_principal = busca_velas(cripto, tf_principal, emas)
        
        # Dados do timeframe de confirmação
        resposta_confirmacao = cliente.get_kline(symbol=cripto, interval=tf_confirmacao, limit=100)
        velas_confirmacao = resposta_confirmacao['result']['list'][::-1]
        
        colunas = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'turnover']
        df_confirmacao = pd.DataFrame(velas_confirmacao, columns=colunas)
        
        # Converter tipos
        df_confirmacao['open_time'] = pd.to_datetime(df_confirmacao['open_time'].astype(np.int64), unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df_confirmacao[col] = df_confirmacao[col].astype(float)
        
        # Adicionar EMAs ao timeframe de confirmação
        df_confirmacao[f'EMA_{emas[0]}'] = df_confirmacao['close'].ewm(span=emas[0], adjust=False).mean()
        df_confirmacao[f'EMA_{emas[1]}'] = df_confirmacao['close'].ewm(span=emas[1], adjust=False).mean()
        df_confirmacao['EMA_200'] = df_confirmacao['close'].ewm(span=200, adjust=False).mean()
        
        return df_principal, df_confirmacao
        
    except Exception as e:
        print(f'Erro ao buscar dados multi-timeframe: {e}', flush=True)
        return None, None

def calcular_indicadores_quantitativos(df):
    """Calcula todos os indicadores quantitativos para reversões"""
    try:
        # Indicadores básicos (já existentes)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=rsi_periodo).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_periodo).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['Volume_EMA_20'] = df['volume'].ewm(span=volume_ma_periodo, adjust=False).mean()
        
        # Indicadores para detecção de reversões
        df = calcular_atr(df, 14)
        df = calcular_adx(df, adx_periodo)
        
        return df
        
    except Exception as e:
        print(f'Erro ao calcular indicadores: {e}', flush=True)
        return df

def sistema_score_reversoes(df_principal, df_confirmacao, velas_consecutivas, direcao='compra'):
    """Sistema de pontuação quantitativa específico para reversões - OTIMIZADO"""
    score = 0
    detalhes_score = []
    
    if len(df_principal) < 50 or len(df_confirmacao) < 20:
        return 0, ["Dados insuficientes"]
    
    try:
        # Dados da última vela
        ultima_vela = df_principal.iloc[-1]
        penultima_vela = df_principal.iloc[-2]
        ultima_vela_conf = df_confirmacao.iloc[-1]
        
        if direcao == 'compra':
            # ESTRATÉGIA ORIGINAL: Detectar FUNDO após velas vermelhas
            
            # 1. RSI em zona de reversão (sua condição original) - 3 pontos
            if penultima_vela['RSI'] < rsi_oversold_reversao:
                score += 3
                detalhes_score.append(f"✓ RSI sobrevendido: {penultima_vela['RSI']:.1f}")
            
            # 2. Volume (mais permissivo) - 2 pontos
            volume_ratio = ultima_vela['volume'] / ultima_vela['Volume_EMA_20']
            if volume_ratio > volume_threshold:
                score += 2
                detalhes_score.append(f"✓ Volume adequado: {volume_ratio:.2f}x")
            elif volume_ratio > 0.5:
                score += 1
                detalhes_score.append(f"⚠️ Volume moderado: {volume_ratio:.2f}x")
            
            # 3. Rompimento da máxima anterior (sua condição original) - 2 pontos
            if ultima_vela['high'] > penultima_vela['high']:
                score += 2
                detalhes_score.append("✓ Rompimento de máxima anterior")
            
            # 4. Contador de velas vermelhas (nova adição) - 2 pontos
            if min_velas_consecutivas <= velas_consecutivas <= max_velas_consecutivas:
                score += 2
                detalhes_score.append(f"✓ {velas_consecutivas} velas vermelhas consecutivas")
            
            # 5. Confirmação do timeframe maior (contra tendência controlada) - 1 ponto
            if ultima_vela_conf['close'] > ultima_vela_conf['EMA_200']:
                score += 1
                detalhes_score.append("✓ TF maior não em queda forte")
            
        else:  # venda
            # ESTRATÉGIA ORIGINAL: Detectar TOPO após velas verdes
            
            # 1. RSI em zona de reversão (sua condição original) - 3 pontos
            if penultima_vela['RSI'] > rsi_overbought_reversao:
                score += 3
                detalhes_score.append(f"✓ RSI sobrecomprado: {penultima_vela['RSI']:.1f}")
            
            # 2. Volume (mais permissivo) - 2 pontos
            volume_ratio = ultima_vela['volume'] / ultima_vela['Volume_EMA_20']
            if volume_ratio > volume_threshold:
                score += 2
                detalhes_score.append(f"✓ Volume adequado: {volume_ratio:.2f}x")
            elif volume_ratio > 0.5:
                score += 1
                detalhes_score.append(f"⚠️ Volume moderado: {volume_ratio:.2f}x")
            
            # 3. Rompimento da mínima anterior (sua condição original adaptada) - 2 pontos
            if ultima_vela['low'] < penultima_vela['low']:
                score += 2
                detalhes_score.append("✓ Rompimento de mínima anterior")
            
            # 4. Contador de velas verdes (nova adição) - 2 pontos
            if min_velas_consecutivas <= velas_consecutivas <= max_velas_consecutivas:
                score += 2
                detalhes_score.append(f"✓ {velas_consecutivas} velas verdes consecutivas")
            
            # 5. Confirmação do timeframe maior (contra tendência controlada) - 1 ponto
            if ultima_vela_conf['close'] < ultima_vela_conf['EMA_200']:
                score += 1
                detalhes_score.append("✓ TF maior não em alta forte")
        
        return score, detalhes_score
        
    except Exception as e:
        print(f'Erro no sistema de score: {e}', flush=True)
        return 0, [f"Erro: {str(e)}"]

def calcular_stop_dinamico(df, direcao, preco_entrada, atr_atual):
    """Calcula stop loss dinâmico baseado em múltiplos fatores"""
    try:
        # Stop baseado em ATR
        stop_atr = atr_atual * 2.5
        
        # Stop baseado em suporte/resistência recente
        if direcao == 'compra':
            low_recente = df['low'].tail(qtd_velas_stop).min()
            stop_sr = preco_entrada - low_recente
        else:
            high_recente = df['high'].tail(qtd_velas_stop).max()
            stop_sr = high_recente - preco_entrada
        
        # Usar o menor dos stops (mais conservador)
        stop_final = min(stop_atr, stop_sr)
        
        # Não permitir stop menor que 0.5% do preço
        stop_minimo = preco_entrada * 0.005
        stop_final = max(stop_final, stop_minimo)
        
        return stop_final
        
    except Exception as e:
        print(f'Erro ao calcular stop dinâmico: {e}', flush=True)
        return atr_atual * 2  # Fallback

def verificar_trade_aberto():
    """Verifica se há trade aberto com tratamento de erro"""
    for tentativa in range(3):
        try:
            return tem_trade_aberto(cripto)
        except Exception as e:
            print(f'Erro ao verificar trade aberto (tentativa {tentativa + 1}): {e}', flush=True)
            if tentativa < 2:
                time.sleep(2)
    return EstadoDeTrade.DE_FORA, 0, 0, 0

# ===== LOOP PRINCIPAL =====
def main():
    # Inicialização
    estado_de_trade, preco_entrada, preco_stop, preco_alvo = verificar_trade_aberto()
    print(f'Estado inicial: {estado_de_trade}', flush=True)
    
    vela_fechou_trade = None
    contador_analise = 0
    
    while True:
        try:
            contador_analise += 1
            print(f"\n{'='*60}")
            print(f"🔄 ANÁLISE #{contador_analise} - {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*60}")
            
            # Buscar dados multi-timeframe
            df_principal, df_confirmacao = buscar_dados_multi_timeframe(cripto, tf_principal, tf_confirmacao, emas)
            
            if df_principal is None or df_confirmacao is None:
                print('Erro ao buscar dados. Aguardando...', flush=True)
                time.sleep(30)
                continue
            
            # Calcular indicadores quantitativos
            df_principal = calcular_indicadores_quantitativos(df_principal)
            
            # Verificar se há dados suficientes
            if len(df_principal) < 50:
                print('Dados insuficientes. Aguardando...', flush=True)
                time.sleep(30)
                continue
            
            # Logs de debug para render
            print(f"📊 RSI Atual: {df_principal['RSI'].iloc[-1]:.2f}")
            print(f"📊 RSI Anterior: {df_principal['RSI'].iloc[-2]:.2f}")
            print(f"📊 Volume Atual: {df_principal['volume'].iloc[-1]:.0f}")
            print(f"📊 Volume EMA: {df_principal['Volume_EMA_20'].iloc[-1]:.0f}")
            print(f"📊 Volume Ratio: {df_principal['volume'].iloc[-1]/df_principal['Volume_EMA_20'].iloc[-1]:.2f}x")
            
            # ===== GESTÃO DE POSIÇÕES ABERTAS =====
            if estado_de_trade == EstadoDeTrade.COMPRADO:
                print('Posição COMPRADA - Monitorando saída...', flush=True)
                
                _, _, preco_stop_atual, preco_alvo_atual = verificar_trade_aberto()
                preco_atual = df_principal['close'].iloc[-1]
                
                # Breakeven management
                preco_parcial_compra = preco_entrada * 1.005  # 0.5% de lucro
                stop_breakeven_compra(cripto, preco_entrada, preco_parcial_compra, estado_de_trade, preco_atual)
                
                # Verificar saída
                if df_principal['high'].iloc[-1] >= preco_alvo_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🎯 ALVO ATINGIDO! Preço: {preco_alvo_atual:.2f}", flush=True)
                    print('-' * 50, flush=True)
                elif df_principal['low'].iloc[-1] <= preco_stop_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🛑 STOP LOSS! Preço: {preco_stop_atual:.2f}", flush=True)
                    print('-' * 50, flush=True)
                elif verificar_trade_aberto()[0] == EstadoDeTrade.DE_FORA:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print('Trade fechado manualmente', flush=True)
                    print('-' * 50, flush=True)
            
            elif estado_de_trade == EstadoDeTrade.VENDIDO:
                print('Posição VENDIDA - Monitorando saída...', flush=True)
                
                _, _, preco_stop_atual, preco_alvo_atual = verificar_trade_aberto()
                preco_atual = df_principal['close'].iloc[-1]
                
                # Breakeven management
                preco_parcial_venda = preco_entrada * 0.995  # 0.5% de lucro
                stop_breakeven_venda(cripto, preco_entrada, preco_parcial_venda, estado_de_trade, preco_atual)
                
                # Verificar saída
                if df_principal['low'].iloc[-1] <= preco_alvo_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🎯 ALVO ATINGIDO! Preço: {preco_alvo_atual:.2f}", flush=True)
                    print('-' * 50, flush=True)
                elif df_principal['high'].iloc[-1] >= preco_stop_atual:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print(f"🛑 STOP LOSS! Preço: {preco_stop_atual:.2f}", flush=True)
                    print('-' * 50, flush=True)
                elif verificar_trade_aberto()[0] == EstadoDeTrade.DE_FORA:
                    estado_de_trade = EstadoDeTrade.DE_FORA
                    vela_fechou_trade = df_principal['open_time'].iloc[-1]
                    print('Trade fechado manualmente', flush=True)
                    print('-' * 50, flush=True)
            
            # ===== BUSCA POR NOVAS ENTRADAS (REVERSÕES) =====
            elif estado_de_trade == EstadoDeTrade.DE_FORA and df_principal['open_time'].iloc[-1] != vela_fechou_trade:
                print('🔍 PROCURANDO REVERSÕES...', flush=True)
                
                # Contar velas consecutivas
                velas_verdes, velas_vermelhas = contar_velas_consecutivas(df_principal)
                print(f"📊 Velas Verdes Consecutivas: {velas_verdes}")
                print(f"📊 Velas Vermelhas Consecutivas: {velas_vermelhas}")
                
                # Obter dados para cálculos
                saldo = saldo_da_conta() * alavancagem
                qtidade_minima = quantidade_minima_para_operar(cripto)
                qtd_cripto = quantidade_cripto_para_operar(saldo, qtidade_minima, df_principal['close'].iloc[-1])
                atr_atual = df_principal['ATR'].iloc[-1]
                
                # ===== ANÁLISE PARA COMPRA (FUNDO APÓS VELAS VERMELHAS) =====
                score_compra, detalhes_compra = sistema_score_reversoes(df_principal, df_confirmacao, velas_vermelhas, 'compra')
                
                # ===== ANÁLISE PARA VENDA (TOPO APÓS VELAS VERDES) =====
                score_venda, detalhes_venda = sistema_score_reversoes(df_principal, df_confirmacao, velas_verdes, 'venda')
                
                print(f"\n📊 RESULTADOS:")
                print(f"   Score Compra: {score_compra}/{score_maximo}")
                print(f"   Score Venda: {score_venda}/{score_maximo}")
                print(f"   Score Mínimo: {score_minimo_entrada}")
                
                # ===== ENTRADA EM COMPRA (SUA ESTRATÉGIA ORIGINAL APRIMORADA) =====
                if (score_compra >= score_minimo_entrada and 
                    score_compra > score_venda and
                    df_principal['RSI'].iloc[-2] < rsi_oversold_reversao and
                    df_principal['volume'].iloc[-1] > df_principal['Volume_EMA_20'].iloc[-1] and
                    df_principal['high'].iloc[-1] > df_principal['high'].iloc[-2] and
                    velas_vermelhas >= min_velas_consecutivas):
                    
                    preco_entrada = df_principal['high'].iloc[-2]  # Sua estratégia original
                    
                    # Stop loss dinâmico
                    stop_distance = calcular_stop_dinamico(df_principal, 'compra', preco_entrada, atr_atual)
                    preco_stop = preco_entrada - stop_distance
                    
                    # Take profit baseado no R:R
                    preco_alvo = preco_entrada + (stop_distance * risco_retorno)
                    
                    # Executar ordem
                    try:
                        abre_compra(cripto, qtd_cripto, preco_stop, preco_alvo)
                        estado_de_trade = EstadoDeTrade.COMPRADO
                        
                        print(f"\n🚀 COMPRA DE REVERSÃO EXECUTADA!", flush=True)
                        print(f"📈 Preço Entrada: {preco_entrada:.5f}", flush=True)
                        print(f"🛑 Stop Loss: {preco_stop:.5f}", flush=True)
                        print(f"🎯 Take Profit: {preco_alvo:.5f}", flush=True)
                        print(f"📊 Score Final: {score_compra}/{score_maximo}", flush=True)
                        print(f"🔴 Velas Vermelhas: {velas_vermelhas}", flush=True)
                        print("✅ Critérios atendidos:", flush=True)
                        for detalhe in detalhes_compra:
                            print(f"   {detalhe}", flush=True)
                        print('-' * 50, flush=True)
                        
                        # Configurar ordem parcial
                        abre_parcial_compra(cripto, qtd_cripto, preco_entrada)
                        
                    except Exception as e:
                        print(f'Erro ao executar compra: {e}', flush=True)
                
                # ===== ENTRADA EM VENDA (SUA ESTRATÉGIA ORIGINAL ADAPTADA) =====
                elif (score_venda >= score_minimo_entrada and 
                      score_venda > score_compra and
                      df_principal['RSI'].iloc[-2] > rsi_overbought_reversao and
                      df_principal['volume'].iloc[-1] > df_principal['Volume_EMA_20'].iloc[-1] and
                      df_principal['low'].iloc[-1] < df_principal['low'].iloc[-2] and
                      velas_verdes >= min_velas_consecutivas):
                    
                    preco_entrada = df_principal['low'].iloc[-2]  # Adaptação da sua estratégia
                    
                    # Stop loss dinâmico
                    stop_distance = calcular_stop_dinamico(df_principal, 'venda', preco_entrada, atr_atual)
                    preco_stop = preco_entrada + stop_distance
                    
                    # Take profit baseado no R:R
                    preco_alvo = preco_entrada - (stop_distance * risco_retorno)
                    
                    # Executar ordem
                    try:
                        abre_venda(cripto, qtd_cripto, preco_stop, preco_alvo)
                        estado_de_trade = EstadoDeTrade.VENDIDO
                        
                        print(f"\n🔻 VENDA DE REVERSÃO EXECUTADA!", flush=True)
                        print(f"📉 Preço Entrada: {preco_entrada:.5f}", flush=True)
                        print(f"🛑 Stop Loss: {preco_stop:.5f}", flush=True)
                        print(f"🎯 Take Profit: {preco_alvo:.5f}", flush=True)
                        print(f"📊 Score Final: {score_venda}/{score_maximo}", flush=True)
                        print(f"🟢 Velas Verdes: {velas_verdes}", flush=True)
                        print("✅ Critérios atendidos:", flush=True)
                        for detalhe in detalhes_venda:
                            print(f"   {detalhe}", flush=True)
                        print('-' * 50, flush=True)
                        
                        # Configurar ordem parcial
                        abre_parcial_venda(cripto, qtd_cripto, preco_entrada)
                        
                    except Exception as e:
                        print(f'Erro ao executar venda: {e}', flush=True)
                
                else:
                    print(f"❌ Critérios de reversão não atendidos", flush=True)
                    print(f"   Score compra: {score_compra} | Score venda: {score_venda}", flush=True)
                    print(f"   Velas verdes: {velas_verdes} | Velas vermelhas: {velas_vermelhas}", flush=True)
                    if score_compra > 0:
                        print("✅ Critérios compra atendidos:", flush=True)
                        for detalhe in detalhes_compra:
                            print(f"   {detalhe}", flush=True)
                    if score_venda > 0:
                        print("✅ Critérios venda atendidos:", flush=True)
                        for detalhe in detalhes_venda:
                            print(f"   {detalhe}", flush=True)
        
        except Exception as e:
            print(f'Erro no loop principal: {e}', flush=True)
        
        # Aguardar próxima análise
        print(f"\n⏰ Próxima análise em 15 segundos...")
        time.sleep(15)  # Análise a cada 15 segundos

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Bot interrompido pelo usuário", flush=True)
    except Exception as e:
        print(f"\n❌ Erro crítico: {e}", flush=True)
        print("Reiniciando em 60 segundos...", flush=True)
        time.sleep(60)
        main()
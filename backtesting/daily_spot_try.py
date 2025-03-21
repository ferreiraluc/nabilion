#!/usr/bin/env python3
from pybit.unified_trading import HTTP
from datetime import datetime
import time
from dotenv import load_dotenv
import os
import json
from fpdf import FPDF
from funcoes_bybit import saldo_da_conta
from utilidades import enviar_relatorio_por_email
from decimal import Decimal, ROUND_DOWN

load_dotenv()
API_KEY = os.getenv('BYBIT_API_KEY')
SECRET_KEY = os.getenv('BYBIT_API_SECRET')
cliente = HTTP(api_key=API_KEY, api_secret=SECRET_KEY)

CRIPTOMOEDA = 'BTCUSDT'
VALOR_COMPRA = 10  
ARQUIVO_HISTORICO = 'historico_compras.json'
ARQUIVO_RELATORIO = 'relatorio_compras.pdf'

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Relatório de Compras Diárias - BTC/USDT', 0, 1, 'C')

    def compra_table(self, compras):
        self.set_font('Arial', 'B', 10)
        headers = ['Data', 'Qtd (BTC)', 'Qtd (USDT)', 'Preço BTC (USDT)']
        col_widths = [50, 40, 40, 50]
        
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 10, header, 1)
        self.ln()
        
        self.set_font('Arial', '', 10)
        for compra in compras:
            self.cell(col_widths[0], 10, compra['data'], 1)
            self.cell(col_widths[1], 10, f"{compra['qtd_btc']:.8f}", 1)
            self.cell(col_widths[2], 10, f"{compra['qtd_usdt']:.2f}", 1)
            self.cell(col_widths[3], 10, f"{compra['preco_btc']:.2f}", 1)
            self.ln()
    
    def resumo_geral(self, saldo_atual, valor_investido, preco_medio, lucro_prejuizo, preco_atual):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Resumo Geral', 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 10, f"Saldo Atual: {saldo_atual:.2f} USDT", 0, 1)
        self.cell(0, 10, f"Valor Total Investido: {valor_investido:.2f} USDT", 0, 1)
        self.cell(0, 10, f"Preço Médio da Carteira: {preco_medio:.2f} USDT", 0, 1)
        self.cell(0, 10, f"Preço Atual do BTC: {preco_atual:.2f} USDT", 0, 1)
        self.cell(0, 10, f"Lucro/Prejuízo Potencial: {lucro_prejuizo:.2f} USDT", 0, 1)

def salvar_historico(historico):
    with open(ARQUIVO_HISTORICO, 'w') as f:
        json.dump(historico, f, indent=4)
    print(f"Histórico salvo em {ARQUIVO_HISTORICO}", flush=True)

def get_current_price(criptomoeda):
    try:
        orderbook = cliente.get_orderbook(category='spot', symbol=criptomoeda)
        bid_price = float(orderbook['result']['b'][0][0])
        ask_price = float(orderbook['result']['a'][0][0])
        return (bid_price + ask_price) / 2
    except Exception as e:
        print(f"Erro ao obter preço: {e}", flush=True)
        return None

def obter_quantidade_minima(criptomoeda):
    try:
        resposta = cliente.get_instruments_info(category='spot', symbol=criptomoeda)
        min_order_qty = float(resposta['result']['list'][0]['lotSizeFilter']['minOrderQty'])
        return min_order_qty
    except Exception as e:
        print(f"Erro ao obter quantidade mínima: {e}", flush=True)
        return None

def ajustar_quantidade(qtd_btc, min_order_qty):
    qtd_btc_decimal = Decimal(str(qtd_btc))
    min_order_qty_decimal = Decimal(str(min_order_qty))
    qtd_ajustada = max(qtd_btc_decimal, min_order_qty_decimal)
    qtd_ajustada = (qtd_ajustada / min_order_qty_decimal).to_integral() * min_order_qty_decimal
    return str(qtd_ajustada.quantize(min_order_qty_decimal, rounding=ROUND_DOWN))

def obter_historico_compras_api():
    try:
        historico = cliente.get_order_history(category='spot', symbol=CRIPTOMOEDA, side='Buy', limit=100)
        compras = []
        ultima_data = None
        
        for ordem in historico['result']['list']:
            if ordem['orderStatus'] == 'Filled':  
                data_compra = datetime.fromtimestamp(int(ordem['createdTime']) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                qtd_btc = float(ordem['qty'])
                qtd_usdt = float(ordem['cumExecValue'])
                preco_btc = qtd_usdt / qtd_btc if qtd_btc > 0 else 0
                
                compras.append({
                    'data': data_compra,
                    'qtd_btc': qtd_btc,
                    'qtd_usdt': qtd_usdt,
                    'preco_btc': preco_btc
                })
                if not ultima_data or datetime.strptime(data_compra, '%Y-%m-%d %H:%M:%S') > datetime.strptime(ultima_data, '%Y-%m-%d %H:%M:%S'):
                    ultima_data = data_compra

        ultima_compra_date = datetime.strptime(ultima_data, '%Y-%m-%d %H:%M:%S').date() if ultima_data else None
        return {
            'ultima_compra': ultima_compra_date.strftime('%Y-%m-%d') if ultima_compra_date else None,
            'compras': compras[::-1] 
        }
    except Exception as e:
        print(f"Erro ao obter histórico da API: {e}", flush=True)
        return None

def calcular_preco_medio(compras):
    total_btc = sum(compra['qtd_btc'] for compra in compras)
    total_usdt = sum(compra['qtd_usdt'] for compra in compras)
    return total_usdt / total_btc if total_btc > 0 else 0

def gerar_relatorio_pdf(historico, saldo_atual, preco_atual):
    pdf = PDF()
    pdf.add_page()
    pdf.compra_table(historico['compras'])
    
    valor_investido = sum(compra['qtd_usdt'] for compra in historico['compras'])
    preco_medio = calcular_preco_medio(historico['compras'])
    total_btc = sum(compra['qtd_btc'] for compra in historico['compras'])
    valor_atual_carteira = total_btc * preco_atual
    lucro_prejuizo = valor_atual_carteira - valor_investido
    
    pdf.ln(10)
    pdf.resumo_geral(saldo_atual, valor_investido, preco_medio, lucro_prejuizo, preco_atual)
    pdf.output(ARQUIVO_RELATORIO)
    print(f"Relatório PDF gerado: {ARQUIVO_RELATORIO}", flush=True)

def main():
    print("Robô de compra diária iniciado...", flush=True)
    
    historico = obter_historico_compras_api()
    if historico:
        salvar_historico(historico)
        print(f"Histórico carregado da API. Última compra: {historico['ultima_compra']}", flush=True)
    else:
        print("Erro ao carregar histórico da API. Não será possível continuar.", flush=True)
        return 

    ultima_data_relatorio = None

    while True:
        agora = datetime.now()
        dia_atual = agora.date()
        ultima_compra = (datetime.strptime(historico['ultima_compra'], '%Y-%m-%d').date() 
                        if historico['ultima_compra'] else None)
        print(f"Verificando: Dia atual = {dia_atual}, Última compra = {ultima_compra}", flush=True)

        if ultima_compra is None or ultima_compra < dia_atual:
            try:
                preco_btc = get_current_price(CRIPTOMOEDA)
                if preco_btc is None:
                    print("Falha ao obter preço. Tentando novamente em 1 hora...", flush=True)
                    time.sleep(3600)
                    continue

                saldo = saldo_da_conta()
                print(f"Saldo atual: {saldo} USDT", flush=True)
                if saldo < VALOR_COMPRA:
                    print(f"Saldo insuficiente: {saldo} USDT < {VALOR_COMPRA} USDT", flush=True)
                    time.sleep(3600)
                    continue

                qtd_btc = VALOR_COMPRA / preco_btc
                min_order_qty = obter_quantidade_minima(CRIPTOMOEDA)
                if min_order_qty is None:
                    print("Falha ao obter quantidade mínima. Tentando novamente em 1 hora...", flush=True)
                    time.sleep(3600)
                    continue

                qtd_btc_str = ajustar_quantidade(qtd_btc, min_order_qty)
                valor_ajustado = float(qtd_btc_str) * preco_btc

                if valor_ajustado < VALOR_COMPRA:
                    print(f"Quantidade ajustada ({qtd_btc_str} BTC) resulta em valor ({valor_ajustado:.2f} USDT) menor que o mínimo desejado ({VALOR_COMPRA} USDT). Aumentando quantidade...", flush=True)
                    qtd_btc = (VALOR_COMPRA / preco_btc) * 1.1
                    qtd_btc_str = ajustar_quantidade(qtd_btc, min_order_qty)

                # Realizar a compra e obter os dados reais da transação
                resposta = cliente.place_order(
                    category='spot',
                    symbol=CRIPTOMOEDA,
                    side='Buy',
                    orderType='Market',
                    qty=10
                )
                
                # Buscar os detalhes da ordem para obter os valores reais
                order_id = resposta['result']['orderId']
                ordem = cliente.get_order_history(category='spot', symbol=CRIPTOMOEDA, orderId=order_id)
                ordem_detalhes = ordem['result']['list'][0]
                
                qtd_btc_real = float(ordem_detalhes['qty'])
                qtd_usdt_real = float(ordem_detalhes['cumExecValue'])
                preco_btc_real = qtd_usdt_real / qtd_btc_real if qtd_btc_real > 0 else preco_btc

                data_compra = agora.strftime('%Y-%m-%d %H:%M:%S')
                nova_compra = {
                    'data': data_compra,
                    'qtd_btc': qtd_btc_real,
                    'qtd_usdt': qtd_usdt_real,
                    'preco_btc': preco_btc_real
                }
                historico['compras'].append(nova_compra)
                historico['ultima_compra'] = dia_atual.strftime('%Y-%m-%d')
                salvar_historico(historico)
                
                print(f"Compra realizada:", flush=True)
                print(f"Valor da compra: {qtd_usdt_real:.2f} USDT", flush=True)
                print(f"Quantidade da compra: {qtd_btc_real:.8f} BTC", flush=True)
                print(f"Data da compra: {data_compra}", flush=True)
                print(f"Valor do Bitcoin: {preco_btc_real:.2f} USDT", flush=True)
                print("-" * 50, flush=True)

            except Exception as e:
                print(f"Erro ao realizar compra: {e}", flush=True)
                time.sleep(3600) 
                continue

        else:
            print(f"Já comprou hoje ({ultima_compra}). Aguardando próximo dia...", flush=True)

        try:
            preco_btc = get_current_price(CRIPTOMOEDA)
            if preco_btc is None:
                print("Falha ao obter preço para o relatório. Tentando novamente em 1 hora...", flush=True)
                time.sleep(3600)
                continue

            saldo = saldo_da_conta()
            if ultima_data_relatorio is None or ultima_data_relatorio < dia_atual:
                gerar_relatorio_pdf(historico, saldo, preco_btc)
                enviar_relatorio_por_email()
                ultima_data_relatorio = dia_atual
                print(f"Relatório gerado e enviado para o dia {dia_atual}", flush=True)

        except Exception as e:
            print(f"Erro ao gerar/enviar relatório: {e}", flush=True)

        time.sleep(3600)

if __name__ == "__main__":
    main()
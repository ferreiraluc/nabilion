from decimal import Decimal, ROUND_DOWN
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import smtplib

load_dotenv()
# Configurações de e-mail
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_RECEIVER = os.getenv('EMAIL_RECEIVER')

ARQUIVO_RELATORIO = 'relatorio_compras.pdf'

def quantidade_cripto_para_operar(saldo, minimo_para_operar, preco_atual):
    poderia_operar = saldo / preco_atual
    quantidade_cripto_para_operar = int(poderia_operar / minimo_para_operar) * minimo_para_operar
    quantidade_cripto_para_operar = Decimal(quantidade_cripto_para_operar)
    return quantidade_cripto_para_operar.quantize(Decimal(f'{minimo_para_operar}'), rounding=ROUND_DOWN)


def enviar_relatorio_por_email():
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_SENDER
        msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = f"Relatório de Compras Diárias - {datetime.now().strftime('%Y-%m-%d')}"

        body = "Segue em anexo o relatório de compras diárias de BTC/USDT."
        msg.attach(MIMEText(body, 'plain'))

        with open(ARQUIVO_RELATORIO, 'rb') as f:
            anexo = MIMEApplication(f.read(), _subtype='pdf')
            anexo.add_header('Content-Disposition', 'attachment', filename=ARQUIVO_RELATORIO)
            msg.attach(anexo)

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        
        print("Relatório enviado por e-mail com sucesso!", flush=True)
    except Exception as e:
        print(f"Erro ao enviar e-mail: {e}", flush=True)
        
def ajusta_start_time(start_time, tempo_grafico, pular_velas=999):
    start_datetime = datetime.strptime(start_time, '%Y-%m-%d')
    minutos_para_subtrair = pular_velas * int(tempo_grafico)
    novo_datetime = start_datetime - timedelta(minutes=minutos_para_subtrair)
    return novo_datetime.strftime('%Y-%m-%d %H:%M')

def calcula_percentual_perda_na_compra(preco_compra, preco_stop):
    return ((preco_compra - preco_stop) / preco_compra) * 100

def calcula_percentual_lucro_na_compra(preco_compra, preco_alvo):
    return ((preco_alvo - preco_compra) / preco_compra) * 100

def calcula_percentual_perda_na_venda(preco_venda, preco_stop):
    return ((preco_stop - preco_venda) / preco_venda) * 100

def calcula_percentual_lucro_na_venda(preco_venda, preco_alvo):
    return ((preco_venda - preco_alvo) / preco_venda) * 100
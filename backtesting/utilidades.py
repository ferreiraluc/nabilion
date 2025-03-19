from decimal import Decimal, ROUND_DOWN
import os
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import smtplib

# Configurações de e-mail
EMAIL_SENDER = os.getenv('l.adrianobf@gmail.com')
EMAIL_PASSWORD = os.getenv('anad rded ovdq upsl')
EMAIL_RECEIVER = os.getenv('lucasadrianof@hotmail.com')

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
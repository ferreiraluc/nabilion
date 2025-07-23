#!/usr/bin/env python3
"""
Sistema de Dashboard de Mercado Cripto
Monitora top 10 altas/baixas/volumes e gera gráficos com resistências
Envia relatórios por email a cada 6 horas
"""

import os
import time
import schedule
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns
from pybit.unified_trading import HTTP
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
import io
import base64
from jinja2 import Template
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import warnings
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crypto_dashboard.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

load_dotenv()

class CryptoMarketAnalyzer:
    """Analisador de mercado de criptomoedas com dashboard automatizado"""
    
    def __init__(self):
        self.client = HTTP()
        self.email_sender = os.getenv('EMAIL_SENDER')
        self.email_password = os.getenv('EMAIL_PASSWORD') 
        self.email_receiver = os.getenv('EMAIL_RECEIVER')
        
        # Configurações
        self.top_count = 10
        self.resistance_days = 30  # Dias para análise de resistência
        self.support_resistance_threshold = 0.02  # 2% de tolerância
        
        # Garantir que as pastas existam
        os.makedirs('reports', exist_ok=True)
        os.makedirs('charts', exist_ok=True)
        
        logging.info("CryptoMarketAnalyzer inicializado com sucesso")

    def get_market_data(self) -> List[Dict]:
        """Busca dados de mercado de todas as moedas"""
        try:
            response = self.client.get_tickers(category='spot')
            tickers = response['result']['list']
            
            market_data = []
            for ticker in tickers:
                if ticker['symbol'].endswith('USDT'):
                    try:
                        data = {
                            'symbol': ticker['symbol'],
                            'price': float(ticker['lastPrice']),
                            'change_24h': float(ticker['price24hPcnt']) * 100,
                            'volume_24h': float(ticker['volume24h']),
                            'volume_usdt_24h': float(ticker['turnover24h']),
                            'high_24h': float(ticker['highPrice24h']),
                            'low_24h': float(ticker['lowPrice24h'])
                        }
                        market_data.append(data)
                    except (ValueError, TypeError, KeyError):
                        continue
            
            logging.info(f"Coletados dados de {len(market_data)} pares de trading")
            return market_data
            
        except Exception as e:
            logging.error(f"Erro ao buscar dados de mercado: {e}")
            return []

    def get_top_movers(self, market_data: List[Dict]) -> Dict[str, List[Dict]]:
        """Identifica top 10 altas, baixas e volumes"""
        df = pd.DataFrame(market_data)
        
        # Filtrar moedas com volume mínimo (evitar pump/dump de baixo volume)
        min_volume = df['volume_usdt_24h'].quantile(0.7)  # Top 30% por volume
        df_filtered = df[df['volume_usdt_24h'] >= min_volume].copy()
        
        top_gainers = df_filtered.nlargest(self.top_count, 'change_24h').to_dict('records')
        top_losers = df_filtered.nsmallest(self.top_count, 'change_24h').to_dict('records')
        top_volume = df.nlargest(self.top_count, 'volume_usdt_24h').to_dict('records')
        
        return {
            'gainers': top_gainers,
            'losers': top_losers,
            'volume': top_volume
        }

    def get_historical_data(self, symbol: str, days: int = 30) -> pd.DataFrame:
        """Busca dados históricos para análise de resistência"""
        try:
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
            
            response = self.client.get_kline(
                category='spot',
                symbol=symbol,
                interval='60',  # 1 hora
                start=start_time,
                end=end_time,
                limit=1000
            )
            
            data = response['result']['list']
            df = pd.DataFrame(data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
            ])
            
            # Converter tipos
            df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            return df
            
        except Exception as e:
            logging.error(f"Erro ao buscar dados históricos para {symbol}: {e}")
            return pd.DataFrame()

    def find_support_resistance(self, df: pd.DataFrame) -> Dict[str, List[float]]:
        """Identifica níveis de suporte e resistência"""
        if df.empty:
            return {'support': [], 'resistance': []}
        
        # Encontrar máximos e mínimos locais
        highs = df['high'].values
        lows = df['low'].values
        
        # Identificar picos (resistências)
        resistance_levels = []
        for i in range(2, len(highs) - 2):
            if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and
                highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                resistance_levels.append(highs[i])
        
        # Identificar vales (suportes)
        support_levels = []
        for i in range(2, len(lows) - 2):
            if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and
                lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                support_levels.append(lows[i])
        
        # Agrupar níveis próximos
        def group_levels(levels):
            if not levels:
                return []
            
            levels = sorted(levels)
            grouped = []
            current_group = [levels[0]]
            
            for level in levels[1:]:
                if abs(level - current_group[-1]) / current_group[-1] <= self.support_resistance_threshold:
                    current_group.append(level)
                else:
                    grouped.append(np.mean(current_group))
                    current_group = [level]
            
            grouped.append(np.mean(current_group))
            return grouped
        
        # Filtrar níveis mais significativos
        resistance_grouped = group_levels(resistance_levels)
        support_grouped = group_levels(support_levels)
        
        # Manter apenas os 3 níveis mais relevantes de cada
        current_price = df['close'].iloc[-1]
        
        resistance_final = sorted([r for r in resistance_grouped if r > current_price])[:3]
        support_final = sorted([s for s in support_grouped if s < current_price], reverse=True)[:3]
        
        return {
            'resistance': resistance_final,
            'support': support_final
        }

    def create_price_chart(self, symbol: str, df: pd.DataFrame, levels: Dict) -> str:
        """Cria gráfico de preço com suporte e resistência"""
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plotar candlesticks simplificados
        dates = df['timestamp']
        opens = df['open']
        highs = df['high']
        lows = df['low']
        closes = df['close']
        
        # Cores para velas
        colors = ['#00ff88' if close >= open else '#ff4444' 
                 for open, close in zip(opens, closes)]
        
        # Plotar as velas
        for i, (date, open_price, high, low, close, color) in enumerate(
            zip(dates, opens, highs, lows, closes, colors)):
            
            # Linha da vela (high-low)
            ax.plot([date, date], [low, high], color='white', linewidth=0.8, alpha=0.7)
            
            # Corpo da vela
            height = abs(close - open_price)
            bottom = min(open_price, close)
            
            rect = Rectangle((mdates.date2num(date) - 0.01, bottom), 0.02, height, 
                           facecolor=color, alpha=0.8)
            ax.add_patch(rect)
        
        # Adicionar níveis de resistência
        for resistance in levels['resistance']:
            ax.axhline(y=resistance, color='#ff6b6b', linestyle='--', 
                      linewidth=2, alpha=0.8, label=f'Resistência: ${resistance:.4f}')
        
        # Adicionar níveis de suporte  
        for support in levels['support']:
            ax.axhline(y=support, color='#4ecdc4', linestyle='--', 
                      linewidth=2, alpha=0.8, label=f'Suporte: ${support:.4f}')
        
        # Formatação
        ax.set_title(f'{symbol} - Análise de Suporte e Resistência (30 dias)', 
                    fontsize=16, fontweight='bold', color='white')
        ax.set_xlabel('Data', fontsize=12, color='white')
        ax.set_ylabel('Preço (USDT)', fontsize=12, color='white')
        
        # Formatação do eixo X
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
        
        # Grid
        ax.grid(True, alpha=0.3, color='white')
        
        # Legenda
        if levels['resistance'] or levels['support']:
            ax.legend(loc='upper left', fontsize=10)
        
        # Layout
        plt.tight_layout()
        
        # Salvar
        filename = f'charts/{symbol}_chart.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight', 
                   facecolor='#1e1e1e', edgecolor='none')
        plt.close()
        
        logging.info(f"Gráfico criado para {symbol}: {filename}")
        return filename

    def generate_pdf_report(self, market_data: Dict, chart_files: List[str]) -> str:
        """Gera relatório PDF completo"""
        
        # Criar documento PDF
        current_time = datetime.now().strftime('%Y%m%d_%H%M')
        pdf_filename = f"reports/crypto_report_{current_time}.pdf"
        
        doc = SimpleDocTemplate(pdf_filename, pagesize=A4)
        story = []
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#2a5298')
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.HexColor('#4ecdc4')
        )
        
        # Título
        story.append(Paragraph("🚀 Dashboard Cripto", title_style))
        story.append(Paragraph(f"Análise de Mercado - {datetime.now().strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Funções auxiliares
        def format_volume(volume):
            if volume >= 1e9:
                return f"{volume/1e9:.2f}B"
            elif volume >= 1e6:
                return f"{volume/1e6:.2f}M"
            elif volume >= 1e3:
                return f"{volume/1e3:.2f}K"
            return f"{volume:.2f}"

        def format_price(price):
            if price >= 1000:
                return f"{price:,.2f}"
            elif price >= 1:
                return f"{price:.4f}"
            else:
                return f"{price:.8f}"

        # Calcular estatísticas
        total_volume = sum([c['volume_usdt_24h'] for c in market_data['volume']])
        avg_change = np.mean([c['change_24h'] for c in market_data['gainers']])
        positive_count = len([c for c in market_data['gainers'] if c['change_24h'] > 0])
        sentiment = "🟢 Otimista" if positive_count >= 7 else "🔴 Pessimista" if positive_count <= 3 else "🟡 Neutro"

        # Estatísticas resumo
        stats_data = [
            ['Volume Total 24h', format_volume(total_volume)],
            ['Variação Média Top 10', f"{avg_change:+.2f}%"],
            ['Sentimento do Mercado', sentiment]
        ]
        
        stats_table = Table(stats_data, colWidths=[3*inch, 2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f8ff')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(stats_table)
        story.append(Spacer(1, 30))
        
        # Top 10 Maiores Altas
        story.append(Paragraph("📈 Top 10 Maiores Altas (24h)", heading_style))
        gainers_data = [['Símbolo', 'Preço', 'Variação 24h', 'Volume']]
        for crypto in market_data['gainers']:
            gainers_data.append([
                crypto['symbol'],
                f"${format_price(crypto['price'])}",
                f"{crypto['change_24h']:+.2f}%",
                format_volume(crypto['volume_usdt_24h'])
            ])
        
        gainers_table = Table(gainers_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        gainers_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4ecdc4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(gainers_table)
        story.append(Spacer(1, 20))
        
        # Top 10 Maiores Baixas
        story.append(Paragraph("📉 Top 10 Maiores Baixas (24h)", heading_style))
        losers_data = [['Símbolo', 'Preço', 'Variação 24h', 'Volume']]
        for crypto in market_data['losers']:
            losers_data.append([
                crypto['symbol'],
                f"${format_price(crypto['price'])}",
                f"{crypto['change_24h']:+.2f}%",
                format_volume(crypto['volume_usdt_24h'])
            ])
        
        losers_table = Table(losers_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        losers_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ff6b6b')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(losers_table)
        story.append(PageBreak())
        
        # Top 10 Volume
        story.append(Paragraph("💎 Top 10 Maior Volume (24h)", heading_style))
        volume_data = [['Símbolo', 'Preço', 'Variação 24h', 'Volume']]
        for crypto in market_data['volume']:
            volume_data.append([
                crypto['symbol'],
                f"${format_price(crypto['price'])}",
                f"{crypto['change_24h']:+.2f}%",
                format_volume(crypto['volume_usdt_24h'])
            ])
        
        volume_table = Table(volume_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        volume_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(volume_table)
        story.append(Spacer(1, 30))
        
        # Gráficos
        story.append(Paragraph("📊 Análise Técnica - Top 3 Volume", heading_style))
        
        for chart_file in chart_files:
            if os.path.exists(chart_file):
                symbol = os.path.basename(chart_file).replace('_chart.png', '')
                story.append(Paragraph(f"{symbol} - Suporte e Resistência", styles['Normal']))
                story.append(Spacer(1, 10))
                
                img = Image(chart_file, width=6*inch, height=4*inch)
                story.append(img)
                story.append(Spacer(1, 20))
        
        # Rodapé
        story.append(Spacer(1, 30))
        story.append(Paragraph("Dashboard gerado automaticamente • Dados via Bybit API", styles['Normal']))
        story.append(Paragraph(f"Próximo relatório: {(datetime.now() + timedelta(hours=6)).strftime('%d/%m/%Y às %H:%M')}", styles['Normal']))
        
        # Construir PDF
        doc.build(story)
        
        return pdf_filename

    def send_email_report(self, pdf_file: str) -> bool:
        """Envia relatório PDF por email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = self.email_receiver
            msg['Subject'] = f"🚀 Dashboard Cripto - {datetime.now().strftime('%d/%m/%Y %H:%M')}"

            # Corpo do email simples
            body = f"""
            Olá!
            
            Segue em anexo o relatório de análise do mercado cripto de {datetime.now().strftime('%d/%m/%Y às %H:%M')}.
            
            O relatório contém:
            • Top 10 maiores altas das últimas 24h
            • Top 10 maiores baixas das últimas 24h  
            • Top 10 moedas por volume de negociação
            • Análise técnica com gráficos de suporte e resistência
            
            Próximo relatório será enviado em 6 horas.
            
            Atenciosamente,
            Sistema Automatizado Nabilion
            """
            
            msg.attach(MIMEText(body, 'plain'))

            # Anexar PDF
            if os.path.exists(pdf_file):
                with open(pdf_file, 'rb') as f:
                    pdf_attachment = MIMEApplication(f.read(), _subtype='pdf')
                    pdf_attachment.add_header('Content-Disposition', 'attachment', 
                                           filename=os.path.basename(pdf_file))
                    msg.attach(pdf_attachment)

            # Enviar email
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(self.email_sender, self.email_password)
                server.send_message(msg)

            logging.info("Relatório PDF enviado por email com sucesso")
            return True

        except Exception as e:
            logging.error(f"Erro ao enviar email: {e}")
            return False

    def generate_and_send_report(self):
        """Função principal que gera e envia o relatório completo"""
        try:
            logging.info("Iniciando geração do relatório...")
            
            # 1. Buscar dados de mercado
            market_data = self.get_market_data()
            if not market_data:
                logging.error("Falha ao obter dados de mercado")
                return

            # 2. Identificar top movers
            top_movers = self.get_top_movers(market_data)
            logging.info(f"Top movers identificados: {len(top_movers['gainers'])} gainers, {len(top_movers['losers'])} losers, {len(top_movers['volume'])} por volume")
            
            # 3. Gerar gráficos para top 3 volume
            chart_files = []
            top_3_volume = top_movers['volume'][:3]
            
            for crypto in top_3_volume:
                symbol = crypto['symbol']
                logging.info(f"Gerando gráfico para {symbol}")
                
                try:
                    df = self.get_historical_data(symbol, self.resistance_days)
                    if not df.empty:
                        levels = self.find_support_resistance(df)
                        chart_file = self.create_price_chart(symbol, df, levels)
                        chart_files.append(chart_file)
                        logging.info(f"Gráfico gerado com sucesso para {symbol}")
                    else:
                        logging.warning(f"Dados históricos vazios para {symbol}")
                except Exception as e:
                    logging.error(f"Erro ao gerar gráfico para {symbol}: {e}")
                    continue
                    
                # Pequena pausa entre requisições
                time.sleep(1)

            # 4. Gerar PDF
            logging.info("Gerando relatório PDF...")
            pdf_filename = self.generate_pdf_report(top_movers, chart_files)
            logging.info(f"Relatório PDF salvo: {pdf_filename}")
            
            # 5. Enviar por email
            logging.info("Enviando relatório PDF por email...")
            success = self.send_email_report(pdf_filename)
            
            if success:
                logging.info("Relatório completo gerado e enviado com sucesso!")
            else:
                logging.error("Falha no envio do email")

        except Exception as e:
            logging.error(f"Erro crítico na geração do relatório: {e}")
            import traceback
            logging.error(f"Traceback: {traceback.format_exc()}")

def main():
    """Função principal do sistema"""
    logging.info("Iniciando Sistema de Dashboard Cripto")
    
    analyzer = CryptoMarketAnalyzer()
    
    # Verificar configurações de email
    if not all([analyzer.email_sender, analyzer.email_password, analyzer.email_receiver]):
        logging.error("Configurações de email não encontradas no .env")
        return
    
    # Configurar agendamento para cada 6 horas
    schedule.every(6).hours.do(analyzer.generate_and_send_report)
    
    # Executar imediatamente na primeira vez
    logging.info("Executando primeira geração do relatório...")
    analyzer.generate_and_send_report()
    
    # Loop principal
    logging.info("Sistema em execução. Próximo relatório em 6 horas...")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar a cada minuto

if __name__ == "__main__":
    main()
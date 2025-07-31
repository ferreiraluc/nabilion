#!/usr/bin/env python3
"""
Chart Predictor - Visualização de Predições ML
Sistema de gráficos avançados para análise quantitativa de trading
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.figure_factory as ff
from ml_predictor import MLPredictor
from feature_engineering import FeatureEngineer
from funcoes_bybit import busca_velas
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

class ChartPredictor:
    """Sistema de visualização para predições ML"""
    
    def __init__(self):
        self.ml_predictor = MLPredictor()
        self.colors = {
            'bullish': '#00ff88',
            'bearish': '#ff4444', 
            'neutral': '#ffa500',
            'background': '#1e1e1e',
            'grid': '#333333',
            'text': '#ffffff'
        }
    
    def create_candlestick_with_predictions(self, df: pd.DataFrame, 
                                          predictions: Optional[pd.Series] = None,
                                          title: str = "Trading Chart with ML Predictions") -> go.Figure:
        """Cria gráfico de candlestick com predições ML"""
        
        fig = make_subplots(
            rows=4, cols=1,
            subplot_titles=['Price Action & Predictions', 'Volume', 'RSI', 'Prediction Confidence'],
            vertical_spacing=0.05,
            row_heights=[0.5, 0.2, 0.15, 0.15]
        )
        
        # Candlestick principal
        fig.add_trace(
            go.Candlestick(
                x=df['open_time'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price',
                increasing_line_color=self.colors['bullish'],
                decreasing_line_color=self.colors['bearish']
            ),
            row=1, col=1
        )
        
        # EMAs
        ema_cols = [col for col in df.columns if col.startswith('EMA_')]
        colors_ema = ['#ff6b6b', '#4ecdc4', '#45b7d1']
        
        for i, ema_col in enumerate(ema_cols[:3]):
            fig.add_trace(
                go.Scatter(
                    x=df['open_time'],
                    y=df[ema_col],
                    name=ema_col,
                    line=dict(color=colors_ema[i % len(colors_ema)], width=2)
                ),
                row=1, col=1
            )
        
        # Predições (se fornecidas)
        if predictions is not None:
            pred_prices = df['close'].iloc[-len(predictions):] * (1 + predictions)
            pred_dates = df['open_time'].iloc[-len(predictions):]
            
            fig.add_trace(
                go.Scatter(
                    x=pred_dates,
                    y=pred_prices,
                    name='ML Predictions',
                    line=dict(color='yellow', width=3, dash='dash'),
                    mode='lines+markers'
                ),
                row=1, col=1
            )
        
        # Volume
        colors_volume = [self.colors['bullish'] if df['close'].iloc[i] >= df['open'].iloc[i] 
                        else self.colors['bearish'] for i in range(len(df))]
        
        fig.add_trace(
            go.Bar(
                x=df['open_time'],
                y=df['volume'],
                name='Volume',
                marker_color=colors_volume,
                opacity=0.7
            ),
            row=2, col=1
        )
        
        # Volume EMA
        if 'Volume_EMA_20' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['open_time'],
                    y=df['Volume_EMA_20'],
                    name='Volume EMA',
                    line=dict(color='orange', width=2)
                ),
                row=2, col=1
            )
        
        # RSI
        fig.add_trace(
            go.Scatter(
                x=df['open_time'],
                y=df['RSI'],
                name='RSI',
                line=dict(color='purple', width=2)
            ),
            row=3, col=1
        )
        
        # Níveis RSI
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="white", row=3, col=1)
        
        # Confiança das predições (mock data se não tiver)
        if predictions is not None:
            confidence = np.abs(predictions) * 100
            confidence_dates = df['open_time'].iloc[-len(predictions):]
            
            fig.add_trace(
                go.Scatter(
                    x=confidence_dates,
                    y=confidence,
                    name='Prediction Confidence',
                    fill='tozeroy',
                    line=dict(color='cyan', width=2)
                ),
                row=4, col=1
            )
        
        # Layout
        fig.update_layout(
            title=title,
            template='plotly_dark',
            height=1000,
            showlegend=True,
            xaxis_rangeslider_visible=False
        )
        
        # Configurar eixos Y
        fig.update_yaxes(title_text="Price (USDT)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_yaxes(title_text="RSI", row=3, col=1, range=[0, 100])
        fig.update_yaxes(title_text="Confidence %", row=4, col=1, range=[0, 100])
        
        return fig
    
    def create_feature_importance_chart(self, importance_df: pd.DataFrame, 
                                      top_n: int = 20) -> go.Figure:
        """Cria gráfico de importância das features"""
        
        top_features = importance_df.head(top_n)
        
        fig = go.Figure(data=[
            go.Bar(
                y=top_features['feature'],
                x=top_features['importance'],
                orientation='h',
                marker_color='skyblue',
                text=top_features['importance'].round(4),
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            title=f'Top {top_n} Most Important Features',
            template='plotly_dark',
            height=600,
            xaxis_title='Importance Score',
            yaxis_title='Features'
        )
        
        return fig
    
    def create_model_comparison_chart(self, evaluation_results: Dict) -> go.Figure:
        """Cria gráfico comparando performance dos modelos"""
        
        models = list(evaluation_results.keys())
        r2_scores = [evaluation_results[model]['r2'] for model in models]
        mae_scores = [evaluation_results[model]['mae'] for model in models]
        direction_acc = [evaluation_results[model]['direction_accuracy'] for model in models]
        
        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=['R² Score', 'Mean Absolute Error', 'Direction Accuracy'],
            specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # R² Score
        fig.add_trace(
            go.Bar(x=models, y=r2_scores, name='R²', marker_color='lightblue'),
            row=1, col=1
        )
        
        # MAE
        fig.add_trace(
            go.Bar(x=models, y=mae_scores, name='MAE', marker_color='lightcoral'),
            row=1, col=2
        )
        
        # Direction Accuracy
        fig.add_trace(
            go.Bar(x=models, y=direction_acc, name='Direction Acc', marker_color='lightgreen'),
            row=1, col=3
        )
        
        fig.update_layout(
            title='Model Performance Comparison',
            template='plotly_dark',
            height=500,
            showlegend=False
        )
        
        return fig
    
    def create_prediction_distribution(self, predictions: pd.Series, 
                                     actual: pd.Series) -> go.Figure:
        """Cria gráfico de distribuição das predições"""
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=['Prediction Distribution', 'Actual Distribution', 
                          'Prediction vs Actual', 'Residuals Distribution']
        )
        
        # Distribuição das predições
        fig.add_trace(
            go.Histogram(x=predictions, name='Predictions', nbinsx=30, 
                        marker_color='skyblue', opacity=0.7),
            row=1, col=1
        )
        
        # Distribuição dos valores reais
        fig.add_trace(
            go.Histogram(x=actual, name='Actual', nbinsx=30, 
                        marker_color='lightcoral', opacity=0.7),
            row=1, col=2
        )
        
        # Scatter: Predito vs Real
        fig.add_trace(
            go.Scatter(x=actual, y=predictions, mode='markers', 
                      name='Pred vs Actual', marker_color='green'),
            row=2, col=1
        )
        
        # Linha de referência perfeita
        min_val = min(actual.min(), predictions.min())
        max_val = max(actual.max(), predictions.max())
        fig.add_trace(
            go.Scatter(x=[min_val, max_val], y=[min_val, max_val], 
                      mode='lines', name='Perfect Prediction', 
                      line=dict(color='red', dash='dash')),
            row=2, col=1
        )
        
        # Distribuição dos resíduos
        residuals = actual - predictions
        fig.add_trace(
            go.Histogram(x=residuals, name='Residuals', nbinsx=30, 
                        marker_color='orange', opacity=0.7),
            row=2, col=2
        )
        
        fig.update_layout(
            title='Prediction Analysis Dashboard',
            template='plotly_dark',
            height=800,
            showlegend=True
        )
        
        return fig
    
    def create_signal_strength_heatmap(self, df: pd.DataFrame, 
                                     predictions: pd.Series) -> go.Figure:
        """Cria heatmap de força dos sinais por horário"""
        
        # Preparar dados
        df_signals = df.iloc[-len(predictions):].copy()
        df_signals['prediction'] = predictions.values
        df_signals['hour'] = df_signals['open_time'].dt.hour
        df_signals['day_of_week'] = df_signals['open_time'].dt.day_name()
        
        # Calcular força média do sinal por hora e dia
        signal_strength = df_signals.groupby(['day_of_week', 'hour'])['prediction'].mean().unstack()
        
        # Reordenar dias da semana
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        signal_strength = signal_strength.reindex(day_order)
        
        fig = go.Figure(data=go.Heatmap(
            z=signal_strength.values,
            x=signal_strength.columns,
            y=signal_strength.index,
            colorscale='RdYlGn',
            text=signal_strength.values.round(4),
            texttemplate="%{text}",
            colorbar=dict(title="Signal Strength")
        ))
        
        fig.update_layout(
            title='Signal Strength Heatmap (by Hour and Day)',
            template='plotly_dark',
            xaxis_title='Hour of Day',
            yaxis_title='Day of Week',
            height=500
        )
        
        return fig
    
    def create_comprehensive_dashboard(self, symbol: str, timeframe: str = '60', 
                                     emas: List[int] = [9, 21]) -> Dict[str, go.Figure]:
        """Cria dashboard completo de análise"""
        
        print(f"Criando dashboard para {symbol}...")
        
        # Executar análise ML
        results = self.ml_predictor.run_complete_analysis(symbol, timeframe, emas)
        
        if 'error' in results:
            print(f"Erro na análise: {results['error']}")
            return {}
        
        # Carregar dados novamente para gráficos
        df = busca_velas(symbol, timeframe, emas)
        
        # Preparar dados para gráficos
        X_train, X_test, y_train, y_test = self.ml_predictor.prepare_data(df)
        best_model_name = results['best_model']
        predictions = results['all_results'][best_model_name]['predictions']
        
        # Criar gráficos
        charts = {}
        
        # 1. Gráfico principal com candlesticks e predições
        charts['main_chart'] = self.create_candlestick_with_predictions(
            df, predictions, f"{symbol} - ML Trading Analysis"
        )
        
        # 2. Importância das features
        if results['feature_importance'] is not None:
            charts['feature_importance'] = self.create_feature_importance_chart(
                results['feature_importance']
            )
        
        # 3. Comparação de modelos
        charts['model_comparison'] = self.create_model_comparison_chart(
            results['all_results']
        )
        
        # 4. Análise de distribuição
        charts['prediction_analysis'] = self.create_prediction_distribution(
            pd.Series(predictions), y_test
        )
        
        # 5. Heatmap de força dos sinais
        charts['signal_heatmap'] = self.create_signal_strength_heatmap(
            df, pd.Series(predictions)
        )
        
        print(f"Dashboard criado com {len(charts)} gráficos")
        
        return {
            'charts': charts,
            'analysis_results': results
        }
    
    def save_charts_html(self, charts: Dict[str, go.Figure], 
                        symbol: str, output_dir: str = "charts/") -> List[str]:
        """Salva gráficos como arquivos HTML"""
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        saved_files = []
        
        for chart_name, fig in charts.items():
            filename = f"{output_dir}{symbol}_{chart_name}.html"
            fig.write_html(filename)
            saved_files.append(filename)
            print(f"Gráfico salvo: {filename}")
        
        return saved_files

def teste_chart_predictor():
    """Teste do sistema de gráficos"""
    chart_predictor = ChartPredictor()
    
    # Criar dashboard completo
    dashboard = chart_predictor.create_comprehensive_dashboard('BTCUSDT', '60', [9, 21])
    
    if dashboard:
        print("\n=== Dashboard Criado com Sucesso ===")
        print(f"Gráficos disponíveis: {list(dashboard['charts'].keys())}")
        
        # Salvar gráficos
        saved_files = chart_predictor.save_charts_html(
            dashboard['charts'], 'BTCUSDT'
        )
        
        print(f"Arquivos salvos: {saved_files}")
        
        return dashboard
    
    return None

if __name__ == "__main__":
    dashboard = teste_chart_predictor()
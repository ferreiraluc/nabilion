#!/usr/bin/env python3
"""
Sistema Principal de Análise ML para Trading
Integração completa: Feature Engineering + ML Predictions + Visualizations
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os

# Importar nossos módulos
from feature_engineering import FeatureEngineer
from ml_predictor import MLPredictor
from funcoes_bybit import busca_velas

class TradingMLSystem:
    """Sistema principal de ML para trading"""
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.ml_predictor = MLPredictor()
        
    def analyze_crypto(self, symbol: str, timeframe: str = '60', emas: list = [9, 21]):
        """Análise completa de uma criptomoeda"""
        
        print(f"\n🚀 ANÁLISE ML COMPLETA - {symbol}")
        print("="*50)
        
        try:
            # 1. Carregar dados históricos
            print("📊 Carregando dados históricos...")
            df = busca_velas(symbol, timeframe, emas)
            print(f"✓ {len(df)} velas carregadas ({timeframe}min)")
            
            # 2. Processar features
            print("\n🔧 Processando features...")
            df_features = self.feature_engineer.engineer_all_features(df)
            print(f"✓ {len(self.feature_engineer.feature_names)} features criadas")
            
            # 3. Preparar dados para ML
            print("\n🤖 Preparando modelos ML...")
            X_train, X_test, y_train, y_test = self.ml_predictor.prepare_data(df)
            
            # 4. Treinar e avaliar modelos
            print("\n📈 Treinando modelos...")
            training_results = self.ml_predictor.train_models(X_train, y_train)
            evaluation_results = self.ml_predictor.evaluate_models(X_test, y_test, training_results)
            
            # 5. Selecionar melhor modelo
            best_model_name, best_result = self.ml_predictor.get_best_model(evaluation_results)
            
            # 6. Fazer predição para próximo período
            print(f"\n🎯 Gerando predição com {best_model_name}...")
            next_prediction = self.ml_predictor.predict_next_prices(df, best_model_name)
            
            # 7. Análise de features importantes
            feature_importance = self.ml_predictor.feature_importance.get(best_model_name)
            
            # 8. Compilar resultados
            analysis_result = {
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'data_info': {
                    'candles': len(df),
                    'features': len(self.feature_engineer.feature_names),
                    'train_samples': len(X_train),
                    'test_samples': len(X_test)
                },
                'best_model': {
                    'name': best_model_name,
                    'r2_score': best_result['r2'],
                    'mae': best_result['mae'],
                    'direction_accuracy': best_result['direction_accuracy']
                },
                'prediction': next_prediction,
                'top_features': feature_importance.head(15).to_dict('records') if feature_importance is not None else [],
                'all_models': evaluation_results
            }
            
            # 9. Exibir relatório
            self._print_analysis_report(analysis_result)
            
            return analysis_result
            
        except Exception as e:
            print(f"❌ Erro na análise: {e}")
            import traceback
            traceback.print_exc()
            return {'error': str(e)}
    
    def _print_analysis_report(self, result: dict):
        """Imprime relatório da análise"""
        
        print(f"\n📋 RELATÓRIO DE ANÁLISE")
        print("="*50)
        
        # Informações dos dados
        data_info = result['data_info']
        print(f"📊 Dados: {data_info['candles']} velas, {data_info['features']} features")
        print(f"🔢 Treino: {data_info['train_samples']} | Teste: {data_info['test_samples']}")
        
        # Performance do melhor modelo
        best_model = result['best_model']
        print(f"\n🏆 Melhor Modelo: {best_model['name'].upper()}")
        print(f"📈 R² Score: {best_model['r2_score']:.4f}")
        print(f"📊 MAE: {best_model['mae']:.6f}")
        print(f"🎯 Acurácia Direcional: {best_model['direction_accuracy']:.1%}")
        
        # Predição
        prediction = result['prediction']
        direction_emoji = "📈" if prediction['direction'] == 'UP' else "📉"
        
        print(f"\n🔮 PREDIÇÃO PRÓXIMO PERÍODO")
        print(f"💰 Preço Atual: ${prediction['current_price']:,.2f}")
        print(f"🎯 Preço Predito: ${prediction['predicted_price']:,.2f}")
        print(f"📊 Direção: {direction_emoji} {prediction['direction']}")
        print(f"🎲 Confiança: {prediction['confidence']:.1f}%")
        print(f"📈 Retorno Esperado: {prediction['predicted_return']*100:+.4f}%")
        
        # Top features
        top_features = result['top_features']
        if top_features:
            print(f"\n🔝 TOP 10 FEATURES MAIS IMPORTANTES:")
            for i, feature in enumerate(top_features[:10], 1):
                print(f"{i:2d}. {feature['feature']:25s} {feature['importance']:.4f}")
        
        # Comparação de modelos
        all_models = result['all_models']
        print(f"\n📊 COMPARAÇÃO DE MODELOS:")
        print(f"{'Modelo':<20} {'R²':<8} {'MAE':<10} {'Dir.Acc':<8}")
        print("-" * 50)
        
        for model_name, model_result in all_models.items():
            if 'r2' in model_result:
                print(f"{model_name:<20} {model_result['r2']:<8.4f} {model_result['mae']:<10.6f} {model_result['direction_accuracy']:<8.3f}")
    
    def analyze_multiple_cryptos(self, symbols: list, timeframe: str = '60'):
        """Analisa múltiplas criptomoedas"""
        
        print(f"\n🌟 ANÁLISE MULTI-CRYPTO")
        print(f"Símbolos: {', '.join(symbols)}")
        print("="*50)
        
        results = []
        
        for i, symbol in enumerate(symbols, 1):
            print(f"\n[{i}/{len(symbols)}] Analisando {symbol}...")
            
            try:
                result = self.analyze_crypto(symbol, timeframe)
                if 'error' not in result:
                    results.append(result)
                else:
                    print(f"❌ Falha na análise de {symbol}")
                    
            except Exception as e:
                print(f"❌ Erro em {symbol}: {e}")
                continue
        
        # Ranking por performance
        if results:
            print(f"\n🏆 RANKING POR ACURÁCIA DIRECIONAL")
            print("="*60)
            
            ranked = sorted(results, key=lambda x: x['best_model']['direction_accuracy'], reverse=True)
            
            print(f"{'#':<3} {'Symbol':<10} {'Model':<15} {'Dir.Acc':<8} {'Predição':<10}")
            print("-" * 60)
            
            for i, result in enumerate(ranked, 1):
                symbol = result['symbol']
                model = result['best_model']['name']
                accuracy = result['best_model']['direction_accuracy']
                direction = result['prediction']['direction']
                
                emoji = "📈" if direction == 'UP' else "📉"
                
                print(f"{i:<3} {symbol:<10} {model:<15} {accuracy:<8.3f} {emoji} {direction}")
        
        return results
    
    def save_analysis_report(self, result: dict, filename: str = None):
        """Salva relatório em arquivo"""
        
        if filename is None or filename == '':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ml_analysis_{result['symbol']}_{timestamp}.json"
        
        # Criar diretório se não existir
        os.makedirs('reports', exist_ok=True)
        filepath = f"reports/{filename}"
        
        import json
        
        # Converter numpy types para JSON serializable
        def convert_numpy(obj):
            if isinstance(obj, np.integer):
                return int(obj)
            elif isinstance(obj, np.floating):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return obj
        
        # Limpar resultado para JSON
        clean_result = {}
        for key, value in result.items():
            if key != 'all_models':  # Skip models dict que tem objetos não serializáveis
                clean_result[key] = convert_numpy(value)
        
        with open(filepath, 'w') as f:
            json.dump(clean_result, f, indent=2, default=str)
        
        print(f"💾 Relatório salvo: {filepath}")
        return filepath

# Exemplos de uso
def exemplo_analise_individual():
    """Exemplo: análise de uma crypto"""
    system = TradingMLSystem()
    result = system.analyze_crypto('BTCUSDT', '60', [9, 21])
    
    if 'error' not in result:
        system.save_analysis_report(result)
    
    return result

def exemplo_analise_multipla():
    """Exemplo: análise de múltiplas cryptos"""
    system = TradingMLSystem()
    
    symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'ADAUSDT', 'SOLUSDT']
    results = system.analyze_multiple_cryptos(symbols, '60')
    
    return results

def menu_interativo():
    """Menu interativo para o sistema"""
    
    system = TradingMLSystem()
    
    while True:
        print(f"\n🤖 SISTEMA ML TRADING")
        print("="*30)
        print("1. Analisar crypto individual")
        print("2. Analisar múltiplas cryptos")
        print("3. Análise rápida BTC")
        print("4. Sair")
        
        escolha = input("\nEscolha uma opção: ").strip()
        
        if escolha == '1':
            symbol = input("Digite o símbolo (ex: BTCUSDT): ").strip().upper()
            if symbol:
                result = system.analyze_crypto(symbol)
                if 'error' not in result:
                    save = input("Salvar relatório? (s/n): ").strip().lower()
                    if save == 's':
                        system.save_analysis_report(result)
        
        elif escolha == '2':
            symbols_input = input("Digite os símbolos separados por vírgula: ").strip()
            if symbols_input:
                symbols = [s.strip().upper() for s in symbols_input.split(',')]
                system.analyze_multiple_cryptos(symbols)
        
        elif escolha == '3':
            print("Executando análise rápida do BTC...")
            system.analyze_crypto('BTCUSDT', '60', [9, 21])
        
        elif escolha == '4':
            print("👋 Saindo do sistema...")
            break
        
        else:
            print("❌ Opção inválida!")

if __name__ == "__main__":
    # Executar análise de exemplo
    print("🚀 Iniciando exemplo de análise...")
    resultado = exemplo_analise_individual()
    
    # Opcional: menu interativo
    # menu_interativo()
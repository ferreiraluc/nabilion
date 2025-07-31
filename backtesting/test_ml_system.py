#!/usr/bin/env python3
"""
Teste simples do sistema ML para trading
"""

from feature_engineering import FeatureEngineer
from ml_predictor import MLPredictor
from funcoes_bybit import busca_velas

def teste_rapido():
    """Teste rápido do sistema"""
    
    print("🚀 TESTE RÁPIDO DO SISTEMA ML")
    print("="*40)
    
    try:
        # 1. Carregar dados
        print("📊 Carregando dados BTC...")
        df = busca_velas('BTCUSDT', '60', [9, 21])
        print(f"✓ {len(df)} velas carregadas")
        
        # 2. Feature Engineering
        print("\n🔧 Feature Engineering...")
        engineer = FeatureEngineer()
        df_features = engineer.engineer_all_features(df)
        print(f"✓ {len(engineer.feature_names)} features criadas")
        
        # 3. ML Prediction
        print("\n🤖 Predição ML...")
        predictor = MLPredictor()
        X_train, X_test, y_train, y_test = predictor.prepare_data(df)
        
        # Treinar apenas Random Forest (mais rápido)
        print("Treinando Random Forest...")
        model = predictor.models['random_forest']
        scaler = predictor.scalers['random_forest']
        
        X_scaled = scaler.fit_transform(X_train)
        model.fit(X_scaled, y_train)
        
        # Avaliar
        X_test_scaled = scaler.transform(X_test)
        predictions = model.predict(X_test_scaled)
        
        from sklearn.metrics import r2_score, mean_absolute_error
        r2 = r2_score(y_test, predictions)
        mae = mean_absolute_error(y_test, predictions)
        direction_accuracy = (predictions * y_test > 0).mean()
        
        print(f"✓ R² Score: {r2:.4f}")
        print(f"✓ MAE: {mae:.6f}")
        print(f"✓ Direction Accuracy: {direction_accuracy:.3f}")
        
        # 4. Próxima predição
        print("\n📈 Próxima Predição...")
        latest_features = df_features[engineer.feature_names].iloc[-1:].dropna()
        
        if not latest_features.empty:
            X_next_scaled = scaler.transform(latest_features)
            next_return = model.predict(X_next_scaled)[0]
            
            current_price = df['close'].iloc[-1]
            predicted_price = current_price * (1 + next_return)
            direction = "📈 UP" if next_return > 0 else "📉 DOWN"
            confidence = min(abs(next_return) * 10000, 100)  # Scale para %
            
            print(f"💰 Preço Atual: ${current_price:,.2f}")
            print(f"🎯 Preço Predito: ${predicted_price:,.2f}")
            print(f"📊 Direção: {direction}")
            print(f"🎲 Confiança: {confidence:.1f}%")
            print(f"📈 Retorno Esperado: {next_return*100:+.4f}%")
        
        # 5. Top Features
        print(f"\n🔝 TOP 10 FEATURES IMPORTANTES:")
        if hasattr(model, 'feature_importances_'):
            import pandas as pd
            importance_df = pd.DataFrame({
                'feature': latest_features.columns,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            for i, row in importance_df.head(10).iterrows():
                print(f"{importance_df.index.get_loc(i)+1:2d}. {row['feature']:25s} {row['importance']:.4f}")
        
        print(f"\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        
        return {
            'model_performance': {'r2': r2, 'mae': mae, 'direction_accuracy': direction_accuracy},
            'prediction': {'current_price': current_price, 'predicted_price': predicted_price, 
                          'direction': direction, 'confidence': confidence},
            'feature_count': len(engineer.feature_names)
        }
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = teste_rapido()
import os
import json

def obter_caminho_velas(cripto, tempo_grafico, start, end, pasta='dados_historicos'):
    os.makedirs(pasta, exist_ok=True)
    nome_arquivo = f'{cripto}_{tempo_grafico}m_{start}-{end}.json'
    return os.path.join(pasta, nome_arquivo)

def carregar_velas_json(caminho_arquivo):
    if os.path.exists(caminho_arquivo):
        with open(caminho_arquivo, 'r') as f:
            return json.load(f)
    return None

def salvar_velas_json(caminho_arquivo, velas):
    with open(caminho_arquivo, 'w') as f:
        json.dump(velas, f)
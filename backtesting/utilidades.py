from decimal import Decimal, ROUND_DOWN

def quantidade_cripto_para_operar(saldo, minimo_para_operar, preco_atual):
    poderia_operar = saldo / preco_atual
    quantidade_cripto_para_operar = int(poderia_operar / minimo_para_operar) * minimo_para_operar
    quantidade_cripto_para_operar = Decimal(quantidade_cripto_para_operar)
    return quantidade_cripto_para_operar.quantize(Decimal(f'{minimo_para_operar}'), rounding=ROUND_DOWN)
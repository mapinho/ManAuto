from apps.motor.proxima_preventiva import calcular_proxima_preventiva


def test_calcula_restante_e_meses_como_no_prototipo_v42():
    # itv=250, uso=120 -> rest=130; uso_med=150 -> meses=r1(130/150)=0.9
    resultado = calcular_proxima_preventiva(uso=120, intervalo=250, uso_medio_mensal=150)
    assert resultado.restante == 130
    assert resultado.meses == 0.9


def test_uso_medio_zero_retorna_99_meses():
    resultado = calcular_proxima_preventiva(uso=10, intervalo=250, uso_medio_mensal=0)
    assert resultado.meses == 99.0


def test_uso_maior_que_intervalo_usa_resto_da_divisao():
    # uso já passou de um ciclo: 620 % 250 = 120 -> restante = 130
    resultado = calcular_proxima_preventiva(uso=620, intervalo=250, uso_medio_mensal=150)
    assert resultado.restante == 130


def test_intervalo_invalido_nao_estoura_divisao_por_zero():
    resultado = calcular_proxima_preventiva(uso=10, intervalo=0, uso_medio_mensal=100)
    assert resultado == calcular_proxima_preventiva(uso=10, intervalo=0, uso_medio_mensal=100)
    assert resultado.meses == 99.0

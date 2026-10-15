"""FIAP - Fase 2: gerenciamento de pouso da missao Aurora Siger.

Grupo 40 - Felipe Cagnin de Lima.
Execute: python3 mgpeb.py
Simulacao didatica, sem controle de equipamentos reais.
Usa apenas a biblioteca padrao do Python.
"""

from collections import deque
from math import isfinite


COMBUSTIVEL_MINIMO = 20  # Percentual minimo para autorizar a descida.
COMBUSTIVEL_URGENTE = 30  # Abaixo disso, antecipar a avaliacao na fila.
VENTO_MAXIMO = 40  # km/h; limiar ficticio para a janela de pouso.
MASSA_MAXIMA = 10000  # kg; capacidade ficticia da area de pouso.


def criar_sistema():
    """Cada modulo fica em apenas um estado operacional por vez."""
    return {
        "fila": deque(),
        "pousados": [],
        "espera": [],
        "alertas": [],
        "pilha_alertas": [],
        "historico": [],
    }


def numero_valido(valor):
    """Aceita numeros comuns; rejeita texto, booleanos, infinito e NaN."""
    return type(valor) in (int, float) and isfinite(valor)


def validar_modulo(modulo):
    for campo in ("identificador", "nome", "tipo_carga"):
        if not isinstance(modulo[campo], str) or not modulo[campo].strip():
            raise ValueError("Identificador, nome e tipo de carga sao obrigatorios.")
    if type(modulo["prioridade"]) is not int or not 1 <= modulo["prioridade"] <= 5:
        raise ValueError("A prioridade deve ser um inteiro de 1 a 5.")
    if type(modulo["criticidade"]) is not int or not 1 <= modulo["criticidade"] <= 5:
        raise ValueError("A criticidade deve ser um inteiro de 1 a 5.")
    for campo in ("combustivel", "massa_kg", "chegada_min"):
        if not numero_valido(modulo[campo]):
            raise ValueError("Combustivel, massa e chegada devem ser numeros finitos.")
    if not 0 <= modulo["combustivel"] <= 100:
        raise ValueError("Combustivel deve estar entre 0 e 100%.")
    if modulo["massa_kg"] <= 0 or modulo["chegada_min"] < 0:
        raise ValueError("Massa deve ser positiva e chegada nao pode ser negativa.")
    if type(modulo["sensores_integros"]) is not bool:
        raise ValueError("sensores_integros deve ser True ou False.")


def validar_ambiente(ambiente):
    for campo in ("tempo_min", "vento_kmh"):
        if not numero_valido(ambiente[campo]) or ambiente[campo] < 0:
            raise ValueError("Tempo e vento devem ser numeros finitos nao negativos.")
    if type(ambiente["area_livre"]) is not bool:
        raise ValueError("area_livre deve ser True ou False.")


def buscar_por_identificador(modulos, identificador):
    """Busca linear: visita os registros ate encontrar o identificador."""
    for modulo in modulos:
        if modulo["identificador"] == identificador:
            return modulo
    return None


def buscar_por_carga(modulos, tipo_carga):
    """Busca linear que pode retornar mais de um resultado. O(n)."""
    encontrados = []
    for modulo in modulos:
        if modulo["tipo_carga"].casefold() == tipo_carga.casefold():
            encontrados.append(modulo)
    return encontrados


def buscar_menor_combustivel(modulos):
    modulo_com_menos_combustivel = None
    for modulo in modulos:
        if (modulo_com_menos_combustivel is None
                or modulo["combustivel"] < modulo_com_menos_combustivel["combustivel"]):
            modulo_com_menos_combustivel = modulo
    return modulo_com_menos_combustivel


def buscar_maior_prioridade(modulos):
    """Prioridade 1 e a mais alta; empates preservam a ordem de entrada."""
    modulo_prioritario = None
    for modulo in modulos:
        if (modulo_prioritario is None
                or modulo["prioridade"] < modulo_prioritario["prioridade"]):
            modulo_prioritario = modulo
    return modulo_prioritario


def cadastrar_modulo(sistema, modulo):
    validar_modulo(modulo)
    for estado in ("fila", "pousados", "espera", "alertas"):
        if buscar_por_identificador(sistema[estado], modulo["identificador"]) is not None:
            raise ValueError("Ja existe um modulo com esse identificador.")
    # Uma copia impede que a alteracao do dicionario de entrada mude o cadastro.
    sistema["fila"].append(modulo.copy())


def chave_ordenacao(modulo):
    """Compara os criterios na ordem em que aparecem na tupla."""
    # O grupo 0 e avaliado antes do grupo 1. Urgencia nao dispensa seguranca.
    grupo_de_urgencia = 0 if modulo["combustivel"] < COMBUSTIVEL_URGENTE else 1
    return (
        grupo_de_urgencia,
        modulo["prioridade"],
        modulo["combustivel"],
        -modulo["criticidade"],  # O sinal negativo coloca a maior criticidade antes.
        modulo["chegada_min"],
    )


def ordenar_fila(sistema):
    """Insertion sort estavel, escrito explicitamente, sem sort()/sorted().

    Reorganiza apenas os candidatos. Uma posicao melhor nao libera um pouso.
    Custo O(n^2) no pior caso, adequado aos cinco modulos deste exemplo.
    """
    modulos_ordenados = list(sistema["fila"])
    for indice in range(1, len(modulos_ordenados)):
        modulo_atual = modulos_ordenados[indice]
        indice_anterior = indice - 1
        # Abre espaco para inserir o modulo na posicao correta.
        while (indice_anterior >= 0
               and chave_ordenacao(modulos_ordenados[indice_anterior])
               > chave_ordenacao(modulo_atual)):
            modulos_ordenados[indice_anterior + 1] = modulos_ordenados[indice_anterior]
            indice_anterior -= 1
        modulos_ordenados[indice_anterior + 1] = modulo_atual
    sistema["fila"] = deque(modulos_ordenados)


def requisitos_basicos_atendidos(
        combustivel_suficiente, vento_seguro, area_livre, sensores_integros):
    """Porta AND (E): todas as quatro condicoes precisam ser verdadeiras."""
    return (combustivel_suficiente and vento_seguro
            and area_livre and sensores_integros)


def avaliar_pouso(modulo, ambiente):
    """Decide entre pouso autorizado, alerta e espera; informa cada motivo."""
    validar_modulo(modulo)
    validar_ambiente(ambiente)
    condicoes = {
        "combustivel_suficiente": modulo["combustivel"] >= COMBUSTIVEL_MINIMO,
        "vento_seguro": ambiente["vento_kmh"] <= VENTO_MAXIMO,
        "area_livre": ambiente["area_livre"],
        "sensores_integros": modulo["sensores_integros"],
        "massa_permitida": modulo["massa_kg"] <= MASSA_MAXIMA,
        "chegou_a_orbita": modulo["chegada_min"] <= ambiente["tempo_min"],
    }
    requisitos_basicos = requisitos_basicos_atendidos(
        condicoes["combustivel_suficiente"], condicoes["vento_seguro"],
        condicoes["area_livre"], condicoes["sensores_integros"],
    )
    pouso_autorizado = (requisitos_basicos and condicoes["massa_permitida"]
                       and condicoes["chegou_a_orbita"])
    alerta_necessario = (not condicoes["combustivel_suficiente"]
                        or not condicoes["sensores_integros"]
                        or not condicoes["massa_permitida"])

    motivos_de_bloqueio = {
        "combustivel_suficiente": "combustivel abaixo de 20%",
        "vento_seguro": "vento acima de 40 km/h",
        "area_livre": "area de pouso ocupada",
        "sensores_integros": "falha nos sensores",
        "massa_permitida": "massa acima de 10000 kg",
        "chegou_a_orbita": "modulo ainda nao chegou a orbita",
    }
    motivos = []
    for nome_condicao, descricao in motivos_de_bloqueio.items():
        if not condicoes[nome_condicao]:
            motivos.append(descricao)

    # AND autoriza; NOT e OR identificam falhas que precisam de revisao.
    if pouso_autorizado:
        status = "AUTORIZADO"
    elif alerta_necessario:
        status = "ALERTA"
    else:
        status = "ESPERA"
    return {"status": status, "motivos": motivos, "condicoes": condicoes}


def processar_proximo(sistema, ambiente):
    """Retira o primeiro da fila e avalia somente um modulo por chamada."""
    validar_ambiente(ambiente)
    if not sistema["fila"]:
        return None
    modulo = sistema["fila"][0]
    decisao = avaliar_pouso(modulo, ambiente)
    sistema["fila"].popleft()
    evento = {
        "identificador": modulo["identificador"],
        "nome": modulo["nome"],
        "tempo_min": ambiente["tempo_min"],
        "status": decisao["status"],
        "motivos": decisao["motivos"],
        "condicoes": decisao["condicoes"],
    }
    if decisao["status"] == "AUTORIZADO":
        sistema["pousados"].append(modulo)
        # A descida e instantanea neste prototipo, mas a pista fica ocupada
        # ate uma chamada explicita a liberar_area() apos a inspecao simulada.
        ambiente["area_livre"] = False
    elif decisao["status"] == "ALERTA":
        sistema["alertas"].append(modulo)
        sistema["pilha_alertas"].append(evento)
    else:
        sistema["espera"].append(modulo)
    sistema["historico"].append(evento)
    return evento


def liberar_area(ambiente):
    """Representa a confirmacao de area desocupada apos inspecao."""
    validar_ambiente(ambiente)
    ambiente["area_livre"] = True


def reenfileirar_espera(sistema):
    """Retorna apenas modulos em espera para uma nova avaliacao completa."""
    for modulo in sistema["espera"]:
        sistema["fila"].append(modulo)
    sistema["espera"].clear()
    ordenar_fila(sistema)


def revisar_ultimo_alerta(sistema):
    """Revisa o alerta mais recente; o modulo continua bloqueado."""
    if not sistema["pilha_alertas"]:
        return None
    evento = sistema["pilha_alertas"].pop()
    sistema["historico"].append({
        "identificador": evento["identificador"],
        "nome": evento["nome"],
        "status": "ALERTA REVISADO",
        "motivos": ["Revisao registrada; modulo permanece bloqueado."],
    })
    return evento


def altura_descida(tempo_segundos):
    """h(t) = 1000 - 20t + 0.1t^2, em metros, para 0 <= t <= 100 s.

    Modelo cinematico idealizado de uma etapa final ja desacelerada.
    Nao representa queda livre nem inclui arrasto, gravidade e controle real.
    """
    if not numero_valido(tempo_segundos) or not 0 <= tempo_segundos <= 100:
        raise ValueError("O modelo de altura vale somente de 0 a 100 segundos.")
    return 1000 - 20 * tempo_segundos + 0.1 * tempo_segundos ** 2


def criar_exemplo():
    """Dados ficticios; chegada em minutos a partir do inicio da operacao."""
    # Cada valor tem seu campo escrito ao lado, sem depender de uma tupla posicional.
    modulos = [
        {
            "identificador": "HAB01", "nome": "Habitacao", "tipo_carga": "habitacao",
            "prioridade": 3, "combustivel": 55, "massa_kg": 8500,
            "criticidade": 3, "chegada_min": 0, "sensores_integros": True,
        },
        {
            "identificador": "ENE01", "nome": "Energia", "tipo_carga": "energia",
            "prioridade": 1, "combustivel": 60, "massa_kg": 6200,
            "criticidade": 5, "chegada_min": 0, "sensores_integros": True,
        },
        {
            "identificador": "LAB01", "nome": "Laboratorio", "tipo_carga": "laboratorio",
            "prioridade": 4, "combustivel": 45, "massa_kg": 4500,
            "criticidade": 2, "chegada_min": 15, "sensores_integros": False,
        },
        {
            "identificador": "LOG01", "nome": "Logistica", "tipo_carga": "logistica",
            "prioridade": 5, "combustivel": 15, "massa_kg": 9000,
            "criticidade": 2, "chegada_min": 10, "sensores_integros": True,
        },
        {
            "identificador": "MED01", "nome": "Suporte medico", "tipo_carga": "medico",
            "prioridade": 2, "combustivel": 25, "massa_kg": 3800,
            "criticidade": 5, "chegada_min": 5, "sensores_integros": True,
        },
    ]
    sistema = criar_sistema()
    for modulo in modulos:
        cadastrar_modulo(sistema, modulo)
    return sistema


def descrever_modulo(modulo):
    """Mostra o nome da carga junto de seu identificador de cadastro."""
    return f'{modulo["nome"]} ({modulo["identificador"]})'


def mostrar_evento(evento):
    motivos = "; ".join(evento["motivos"]) or "todos os requisitos atendidos"
    print(f'{descrever_modulo(evento)}: {evento["status"]} - {motivos}')


def demonstracao():
    sistema = criar_exemplo()
    ambiente = {"tempo_min": 20, "vento_kmh": 25, "area_livre": True}
    print("Gerenciamento de pouso - Aurora Siger | Grupo 40")
    print("Simulacao didatica; dados e limites ficticios.\n")
    print("Menor combustivel:", descrever_modulo(buscar_menor_combustivel(sistema["fila"])))
    print("Maior prioridade:", descrever_modulo(buscar_maior_prioridade(sistema["fila"])))
    cargas_medicas = buscar_por_carga(sistema["fila"], "medico")
    print("Carga medica:", [descrever_modulo(modulo) for modulo in cargas_medicas])
    print("Busca por identificador HAB01:",
          descrever_modulo(buscar_por_identificador(sistema["fila"], "HAB01")))
    ordenar_fila(sistema)
    print("Fila ordenada:", " -> ".join(descrever_modulo(modulo) for modulo in sistema["fila"]))
    print("\nRodada 1 (sem liberar a area entre candidatos):")
    while sistema["fila"]:
        mostrar_evento(processar_proximo(sistema, ambiente))
    print("\nInspecao simulada confirmou a desocupacao da area.")
    liberar_area(ambiente)
    # Exercicio explicito de janela atmosferica: a espera persiste com vento alto.
    ambiente["vento_kmh"] = 55
    reenfileirar_espera(sistema)
    print("Rodada 2 (vento de 55 km/h):")
    while sistema["fila"]:
        mostrar_evento(processar_proximo(sistema, ambiente))
    ambiente["vento_kmh"] = 25
    reenfileirar_espera(sistema)
    print("\nRodada 3 (vento de 25 km/h; inspecao libera area apos cada pouso):")
    while sistema["fila"]:
        evento = processar_proximo(sistema, ambiente)
        mostrar_evento(evento)
        if evento["status"] == "AUTORIZADO":
            liberar_area(ambiente)
    print("\nPilha de alertas (o ultimo registrado e revisado primeiro):")
    while sistema["pilha_alertas"]:
        evento = revisar_ultimo_alerta(sistema)
        print(descrever_modulo(evento), "revisado; permanece em alerta.")
    print("\nResumo final:")
    for estado in ("fila", "pousados", "espera", "alertas"):
        print(estado + ":", [descrever_modulo(modulo) for modulo in sistema[estado]])
    print("\nAltura na etapa final da descida (tempo em segundos):")
    for tempo in (0, 20, 40, 60, 80, 100):
        print(f"Tempo: {tempo:3d} segundos | Altura: {altura_descida(tempo):6.1f} metros")


if __name__ == "__main__":
    demonstracao()

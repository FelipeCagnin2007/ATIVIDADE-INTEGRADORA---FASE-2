"""FIAP - Fase 2: MGPEB da missao Aurora Siger.

Grupo 40 - Felipe Cagnin de Lima.
Execute: python3 mgpeb.py
Simulacao didatica: valores ficticios, sem controle de equipamentos reais.
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
    return type(valor) in (int, float) and isfinite(valor)


def validar_modulo(modulo):
    for campo in ("id", "tipo_carga"):
        if not isinstance(modulo[campo], str) or not modulo[campo].strip():
            raise ValueError("Identificador e tipo de carga sao obrigatorios.")
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
    if type(modulo["sensores_ok"]) is not bool:
        raise ValueError("sensores_ok deve ser True ou False.")


def validar_ambiente(ambiente):
    for campo in ("tempo_min", "vento_kmh"):
        if not numero_valido(ambiente[campo]) or ambiente[campo] < 0:
            raise ValueError("Tempo e vento devem ser numeros finitos nao negativos.")
    if type(ambiente["area_livre"]) is not bool:
        raise ValueError("area_livre deve ser True ou False.")


def buscar_por_id(modulos, identificador):
    """Busca linear: percorre os registros ate encontrar o ID. O(n)."""
    for modulo in modulos:
        if modulo["id"] == identificador:
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
    menor = None
    for modulo in modulos:
        if menor is None or modulo["combustivel"] < menor["combustivel"]:
            menor = modulo
    return menor


def buscar_maior_prioridade(modulos):
    """Prioridade 1 e a mais alta; empates preservam a ordem de entrada."""
    maior = None
    for modulo in modulos:
        if maior is None or modulo["prioridade"] < maior["prioridade"]:
            maior = modulo
    return maior


def cadastrar_modulo(sistema, modulo):
    validar_modulo(modulo)
    for estado in ("fila", "pousados", "espera", "alertas"):
        if buscar_por_id(sistema[estado], modulo["id"]) is not None:
            raise ValueError("Ja existe um modulo com esse identificador.")
    # Uma copia impede que a alteracao do dicionario de entrada mude o cadastro.
    sistema["fila"].append(modulo.copy())


def chave_ordenacao(modulo):
    """Ordem lexicografica: urgencia, prioridade, combustivel, carga, chegada."""
    urgente = 0 if modulo["combustivel"] < COMBUSTIVEL_URGENTE else 1
    return (
        urgente,
        modulo["prioridade"],
        modulo["combustivel"],
        -modulo["criticidade"],
        modulo["chegada_min"],
    )


def ordenar_fila(sistema):
    """Insertion sort estavel, escrito explicitamente, sem sort()/sorted().

    Reorganiza apenas os candidatos. Uma posicao melhor nao libera um pouso.
    Custo O(n^2) no pior caso, adequado aos cinco modulos deste exemplo.
    """
    ordenados = list(sistema["fila"])
    for indice in range(1, len(ordenados)):
        atual = ordenados[indice]
        anterior = indice - 1
        while anterior >= 0 and chave_ordenacao(ordenados[anterior]) > chave_ordenacao(atual):
            ordenados[anterior + 1] = ordenados[anterior]
            anterior -= 1
        ordenados[anterior + 1] = atual
    sistema["fila"] = deque(ordenados)


def regra_principal(combustivel_ok, atmosfera_ok, area_livre, sensores_ok):
    """Porta AND: P0 = C AND A AND L AND S."""
    return combustivel_ok and atmosfera_ok and area_livre and sensores_ok


def avaliar_pouso(modulo, ambiente):
    """P = P0 AND M AND T. Alerta B = NOT C OR NOT S OR NOT M."""
    validar_modulo(modulo)
    validar_ambiente(ambiente)
    sinais = {
        "C": modulo["combustivel"] >= COMBUSTIVEL_MINIMO,
        "A": ambiente["vento_kmh"] <= VENTO_MAXIMO,
        "L": ambiente["area_livre"],
        "S": modulo["sensores_ok"],
        "M": modulo["massa_kg"] <= MASSA_MAXIMA,
        "T": modulo["chegada_min"] <= ambiente["tempo_min"],
    }
    principal = regra_principal(sinais["C"], sinais["A"], sinais["L"], sinais["S"])
    autorizado = principal and sinais["M"] and sinais["T"]
    alerta = not sinais["C"] or not sinais["S"] or not sinais["M"]
    descricoes = {
        "C": "combustivel abaixo de 20%",
        "A": "vento acima de 40 km/h",
        "L": "area de pouso ocupada",
        "S": "falha nos sensores",
        "M": "massa acima de 10000 kg",
        "T": "modulo ainda nao chegou a orbita",
    }
    motivos = [texto for sinal, texto in descricoes.items() if not sinais[sinal]]
    if autorizado:
        status = "AUTORIZADO"
    elif alerta:
        status = "ALERTA"
    else:
        status = "ESPERA"
    return {"status": status, "motivos": motivos, "sinais": sinais}


def processar_proximo(sistema, ambiente):
    """FIFO apos a ordenacao; simula somente uma autorizacao por chamada."""
    validar_ambiente(ambiente)
    if not sistema["fila"]:
        return None
    modulo = sistema["fila"][0]
    decisao = avaliar_pouso(modulo, ambiente)
    sistema["fila"].popleft()
    evento = {
        "id": modulo["id"],
        "tempo_min": ambiente["tempo_min"],
        "status": decisao["status"],
        "motivos": decisao["motivos"],
        "sinais": decisao["sinais"],
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
    """LIFO: retirar da pilha registra a revisao, sem liberar o modulo."""
    if not sistema["pilha_alertas"]:
        return None
    evento = sistema["pilha_alertas"].pop()
    sistema["historico"].append({
        "id": evento["id"],
        "status": "ALERTA REVISADO",
        "motivos": ["Revisao registrada; modulo permanece bloqueado."],
    })
    return evento


def altura_descida(tempo_s):
    """h(t) = 1000 - 20t + 0.1t^2, em metros, para 0 <= t <= 100 s.

    Modelo cinematico idealizado de uma etapa final ja desacelerada.
    Nao representa queda livre nem inclui arrasto, gravidade e controle real.
    """
    if not numero_valido(tempo_s) or not 0 <= tempo_s <= 100:
        raise ValueError("O modelo de altura vale somente de 0 a 100 segundos.")
    return 1000 - 20 * tempo_s + 0.1 * tempo_s ** 2


def criar_exemplo():
    """Dados ficticios; chegada em minutos a partir do inicio da operacao."""
    dados = [
        ("HAB01", "habitacao", 3, 55, 8500, 3, 0, True),
        ("ENE01", "energia", 1, 60, 6200, 5, 0, True),
        ("LAB01", "laboratorio", 4, 45, 4500, 2, 15, False),
        ("LOG01", "logistica", 5, 15, 9000, 2, 10, True),
        ("MED01", "medico", 2, 25, 3800, 5, 5, True),
    ]
    campos = ("id", "tipo_carga", "prioridade", "combustivel", "massa_kg",
              "criticidade", "chegada_min", "sensores_ok")
    sistema = criar_sistema()
    for valores in dados:
        cadastrar_modulo(sistema, dict(zip(campos, valores)))
    return sistema


def mostrar_evento(evento):
    motivos = "; ".join(evento["motivos"]) or "todos os requisitos atendidos"
    print(f'{evento["id"]}: {evento["status"]} - {motivos}')


def demonstracao():
    sistema = criar_exemplo()
    ambiente = {"tempo_min": 20, "vento_kmh": 25, "area_livre": True}
    print("MGPEB - Aurora Siger | Grupo 40")
    print("Simulacao didatica; dados e limites ficticios.\n")
    print("Menor combustivel:", buscar_menor_combustivel(sistema["fila"])["id"])
    print("Maior prioridade:", buscar_maior_prioridade(sistema["fila"])["id"])
    print("Carga medica:", [m["id"] for m in buscar_por_carga(sistema["fila"], "medico")])
    print("Busca por ID HAB01:", buscar_por_id(sistema["fila"], "HAB01")["tipo_carga"])
    ordenar_fila(sistema)
    print("Fila ordenada:", " -> ".join(m["id"] for m in sistema["fila"]))
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
    print("\nPilha de alertas (ordem de revisao LIFO):")
    while sistema["pilha_alertas"]:
        evento = revisar_ultimo_alerta(sistema)
        print(evento["id"], "revisado; permanece em alerta.")
    print("\nResumo final:")
    for estado in ("fila", "pousados", "espera", "alertas"):
        print(estado + ":", [m["id"] for m in sistema[estado]])
    print("\nAltura na etapa final da descida (tempo em segundos):")
    for tempo in (0, 20, 40, 60, 80, 100):
        print(f"t = {tempo:3d} s | h = {altura_descida(tempo):6.1f} m")


if __name__ == "__main__":
    demonstracao()

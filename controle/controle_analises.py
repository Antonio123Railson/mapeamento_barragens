from controle.validacao import EntradaInvalida, RegistroAusente, filtros_sismicos, id_valido, numero, paginacao
from modelo import analise


def proximidade(args, identificador=None):
    identificador = id_valido(args.get("barragem_id") if identificador is None else identificador)
    raio = numero(args.get("raio_km", 50), "raio_km", 0.01, 1000)
    dados = analise.proximidade(identificador, raio, *filtros_sismicos(args), *paginacao(args))
    if dados is None:
        raise RegistroAusente("Barragem não encontrada.")
    if dados["barragem"]["geometry"] is None:
        raise EntradaInvalida("A barragem não possui coordenadas para a análise.")
    return dados


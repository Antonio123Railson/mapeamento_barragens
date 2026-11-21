from controle.validacao import EntradaInvalida, RegistroAusente, caixa, id_valido, paginacao, texto
from modelo import barragem

UFS = "AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split()


def listar(args):
    uf = texto(args.get("uf", ""), "UF").upper()
    if uf and uf not in UFS:
        raise EntradaInvalida("Informe uma UF brasileira.")
    mapeada = args.get("mapeada", "0")
    if mapeada not in ("0", "1"):
        raise EntradaInvalida("mapeada deve ser 0 ou 1.")
    return barragem.listar(uf, texto(args.get("municipio", ""), "município"),
                          texto(args.get("nome", ""), "nome"), caixa(args),
                          *paginacao(args), mapeada=mapeada == "1")


def buscar(identificador):
    dados = barragem.buscar(id_valido(identificador))
    if dados is None:
        raise RegistroAusente("Barragem não encontrada.")
    return dados


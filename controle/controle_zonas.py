from controle.validacao import caixa, paginacao
from modelo import zona_sismogenica


def listar(args):
    return zona_sismogenica.listar(caixa(args), *paginacao(args))


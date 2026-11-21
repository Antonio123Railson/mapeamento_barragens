from controle.validacao import caixa, filtros_sismicos, paginacao
from modelo import sismo


def listar(args):
    return sismo.listar(*filtros_sismicos(args), caixa(args), *paginacao(args))


import math
import re
from datetime import date


class EntradaInvalida(ValueError):
    """Parâmetro de consulta inválido."""


class RegistroAusente(LookupError):
    """Registro solicitado não encontrado."""


def inteiro(valor, nome, minimo, maximo):
    try:
        convertido = int(valor)
        if minimo <= convertido <= maximo:
            return convertido
    except (ValueError, TypeError):
        pass
    raise EntradaInvalida(f"{nome} deve ser um inteiro entre {minimo} e {maximo}.")


def numero(valor, nome, minimo, maximo):
    try:
        convertido = float(valor)
        if math.isfinite(convertido) and minimo <= convertido <= maximo:
            return convertido
    except (ValueError, TypeError):
        pass
    raise EntradaInvalida(f"{nome} deve estar entre {minimo} e {maximo}.")


def texto(valor, nome):
    valor = valor.strip()
    if len(valor) > 120 or any(ord(caractere) < 32 for caractere in valor):
        raise EntradaInvalida(f"{nome} deve conter até 120 caracteres imprimíveis.")
    return valor


def caixa(args):
    if "bbox" not in args:
        return None
    partes = args["bbox"].split(",")
    if len(partes) != 4:
        raise EntradaInvalida("bbox deve conter oeste,sul,leste,norte.")
    oeste, sul, leste, norte = [numero(valor, "bbox", -faixa, faixa)
                                for valor, faixa in zip(partes, (180, 90, 180, 90))]
    if oeste >= leste or sul >= norte:
        raise EntradaInvalida("bbox precisa estar em ordem crescente.")
    return oeste, sul, leste, norte


def paginacao(args):
    return (inteiro(args.get("limite", 100), "limite", 1, 500),
            inteiro(args.get("pagina", 1), "pagina", 1, 10000))


def data(valor, nome):
    if not valor:
        return None
    try:
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", valor):
            resultado = date.fromisoformat(valor)
            if resultado < date.max:
                return resultado
    except ValueError:
        pass
    raise EntradaInvalida(f"{nome} deve ser uma data válida no formato AAAA-MM-DD.")


def filtros_sismicos(args):
    magnitude = numero(args.get("magnitude_minima", -10), "magnitude_minima", -10, 12)
    inicio, fim = data(args.get("inicio"), "inicio"), data(args.get("fim"), "fim")
    if inicio and fim and inicio > fim:
        raise EntradaInvalida("A data inicial deve preceder ou coincidir com a data final.")
    return magnitude, inicio, fim


def id_valido(identificador):
    return inteiro(identificador, "id", 1, 2**63 - 1)


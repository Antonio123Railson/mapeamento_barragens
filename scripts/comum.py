import math
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def baixar(url):
    try:
        with urlopen(Request(url, headers={"User-Agent": "AtlasBarragensAcademico/1.0"}),
                     timeout=40) as resposta:
            return resposta.read()
    except HTTPError as erro:
        raise ValueError(f"Fonte respondeu HTTP {erro.code}. Use um arquivo local.") from erro
    except OSError as erro:
        raise ValueError(f"Falha de rede: {erro}. Use um arquivo local.") from erro


def decimal(valor, minimo, maximo):
    numero = float(str(valor).strip().replace(",", "."))
    if not math.isfinite(numero) or not minimo <= numero <= maximo:
        raise ValueError("Número fora da faixa.")
    return numero


def executar(funcao):
    import psycopg

    try:
        funcao()
    except psycopg.Error as erro:
        if erro.sqlstate:
            raise SystemExit(f"Falha PostgreSQL ({erro.sqlstate}): {erro.diag.message_primary}") from None
        raise SystemExit(f"Falha de conexão PostgreSQL ({type(erro).__name__}). Verifique o serviço e o .env.") from None
    except (ValueError, OSError) as erro:
        raise SystemExit(str(erro)) from None


import json
from datetime import date, datetime

from db.conexao import conectar

PROVENIENCIA = "f.nome AS fonte, f.endereco_url AS fonte_url, f.data_coleta, f.versao AS fonte_versao"


def consultar(sql, parametros=()):
    with conectar() as conexao:
        return conexao.execute(sql, parametros).fetchall()


def feicao(linha):
    campos = dict(linha)
    geometria = campos.pop("geometria", None)
    identificador = campos.pop("id")
    return {"type": "Feature", "id": identificador,
            "geometry": json.loads(geometria) if geometria else None,
            "properties": {chave: valor.isoformat() if isinstance(valor, (date, datetime)) else valor
                           for chave, valor in campos.items()}}


def colecao(linhas, limite, pagina):
    return {"type": "FeatureCollection", "features": [feicao(linha) for linha in linhas[:limite]],
            "paginacao": {"pagina": pagina, "limite": limite, "mais": len(linhas) > limite}}


def caixa(criterios, parametros, bbox):
    if bbox:
        criterios.append("ST_Intersects(t.geometria, ST_MakeEnvelope(%s,%s,%s,%s,4326))")
        parametros.extend(bbox)


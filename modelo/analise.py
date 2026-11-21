from pathlib import Path

from modelo.geografia import consultar

SQL = (Path(__file__).resolve().parents[1] / "db" / "consultas_espaciais.sql").read_text(encoding="utf-8")


def proximidade(identificador, raio, magnitude, inicio, fim, limite, pagina):
    linhas = consultar(SQL, {
        "id": identificador, "metros": raio * 1000, "magnitude": magnitude,
        "inicio": inicio, "fim": fim, "limite": limite, "offset": (pagina - 1) * limite,
    })
    if not linhas:
        return None

    dados = linhas[0]
    dados["barragem"] = {"type": "Feature", "id": dados.pop("id"), "geometry": dados.pop("geometry"),
                         "properties": {"nome": dados.pop("nome")}}
    dados["eventos"] = {"type": "FeatureCollection", "features": dados["eventos"]}
    dados["paginacao"] = {"pagina": pagina, "limite": limite, "mais": pagina * limite < dados["total"]}
    dados["parametros"] = {"raio_km": raio, "magnitude_minima": magnitude,
                           "inicio": inicio.isoformat() if inicio else None,
                           "fim": fim.isoformat() if fim else None}
    return dados


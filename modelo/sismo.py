from modelo.geografia import PROVENIENCIA, caixa, colecao, consultar

BASE = f"""
SELECT t.id, t.codigo_origem, t.data_hora, t.magnitude, t.profundidade_km,
 ST_AsGeoJSON(t.geometria) geometria, {PROVENIENCIA}
FROM eventos_sismicos t JOIN fontes_dados f ON t.fonte_id=f.id
"""


def filtros_sismicos(magnitude, inicio, fim):
    criterios, valores = ["t.magnitude >= %s"], [magnitude]
    if inicio:
        criterios.append("t.data_hora >= %s::date")
        valores.append(inicio)
    if fim:
        criterios.append("t.data_hora < (%s::date + 1)")
        valores.append(fim)
    return criterios, valores


def listar(magnitude, inicio, fim, bbox, limite, pagina):
    criterios, valores = filtros_sismicos(magnitude, inicio, fim)
    caixa(criterios, valores, bbox)
    sql = BASE + " WHERE " + " AND ".join(criterios) + " ORDER BY t.data_hora DESC, t.id LIMIT %s OFFSET %s"
    return colecao(consultar(sql, [*valores, limite + 1, (pagina - 1) * limite]), limite, pagina)


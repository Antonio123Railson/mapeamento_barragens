from modelo.geografia import PROVENIENCIA, caixa, colecao, consultar, feicao

BASE = f"""
SELECT t.id, t.codigo_anm, t.nome, t.municipio, t.uf, t.categoria_risco,
 t.dano_potencial, t.data_atualizacao, ST_AsGeoJSON(t.geometria) geometria, {PROVENIENCIA}
FROM barragens t JOIN fontes_dados f ON t.fonte_id=f.id
"""


def listar(uf, municipio, nome, bbox, limite, pagina, mapeada=False):
    criterios = ["TRUE"]
    valores = []
    caixa(criterios, valores, bbox)
    if mapeada:
        criterios.append("t.geometria IS NOT NULL")
    if uf:
        criterios.append("t.uf = %s")
        valores.append(uf)
    if municipio:
        criterios.append("lower(t.municipio) = lower(%s)")
        valores.append(municipio)
    if nome:
        criterios.append("strpos(lower(t.nome), lower(%s)) > 0")
        valores.append(nome)
    sql = BASE + " WHERE " + " AND ".join(criterios) + " ORDER BY t.id LIMIT %s OFFSET %s"
    return colecao(consultar(sql, [*valores, limite + 1, (pagina - 1) * limite]), limite, pagina)


def buscar(identificador):
    linhas = consultar(BASE + " WHERE t.id = %s", (identificador,))
    return feicao(linhas[0]) if linhas else None


def estatisticas():
    return consultar("""
        SELECT (SELECT count(*) FROM barragens) barragens,
               (SELECT count(*) FROM barragens WHERE geometria IS NOT NULL) barragens_mapeadas,
               (SELECT count(*) FROM eventos_sismicos) sismos,
               (SELECT count(*) FROM zonas_sismogenicas) zonas,
               (SELECT COALESCE(jsonb_agg(to_jsonb(f) ORDER BY f.nome, f.data_coleta DESC), '[]')
                FROM fontes_dados f WHERE f.id IN (
                    SELECT fonte_id FROM barragens UNION
                    SELECT fonte_id FROM eventos_sismicos UNION
                    SELECT fonte_id FROM zonas_sismogenicas
                )) fontes
    """)[0]


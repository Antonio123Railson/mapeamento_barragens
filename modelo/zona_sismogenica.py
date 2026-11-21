from modelo.geografia import PROVENIENCIA, caixa, colecao, consultar


def listar(bbox, limite, pagina):
    criterios, parametros = ["TRUE"], []
    caixa(criterios, parametros, bbox)
    sql = f"""
        SELECT t.id, t.nome, t.classificacao, t.descricao, t.metodologia, t.referencia_cientifica,
               ST_AsGeoJSON(ST_ForcePolygonCCW(t.geometria),9,0) geometria, {PROVENIENCIA}
        FROM zonas_sismogenicas t JOIN fontes_dados f ON t.fonte_id=f.id
        WHERE {" AND ".join(criterios)} ORDER BY t.id LIMIT %s OFFSET %s
    """
    dados = colecao(consultar(sql, [*parametros, limite + 1, (pagina - 1) * limite]), limite, pagina)
    disponivel = bool(dados["features"]) or consultar(
        "SELECT EXISTS (SELECT 1 FROM zonas_sismogenicas) disponivel")[0]["disponivel"]
    dados["disponivel"] = disponivel
    if not disponivel:
        dados["mensagem"] = "A camada aguarda a importação de polígonos com fonte e metodologia científicas."
    return dados


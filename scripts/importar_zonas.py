import argparse
from pathlib import Path
from urllib.parse import urlparse

import geopandas as gpd

from db.conexao import conectar
from modelo.fonte_dados import registrar
from scripts.comum import executar

SQL = """
INSERT INTO zonas_sismogenicas
(nome, classificacao, descricao, metodologia, referencia_cientifica, geometria, fonte_id)
VALUES (%s,%s,%s,%s,%s, ST_Multi(ST_Force2D(ST_Transform(ST_GeomFromText(%s,%s),4326))), %s)
ON CONFLICT (referencia_cientifica,nome) DO UPDATE SET
 classificacao=EXCLUDED.classificacao, descricao=EXCLUDED.descricao,
 metodologia=EXCLUDED.metodologia, geometria=EXCLUDED.geometria, fonte_id=EXCLUDED.fonte_id
"""


def principal():
    parser = argparse.ArgumentParser(description="Importa polígonos sismogênicos publicados.")
    parser.add_argument("arquivo", type=Path)
    parser.add_argument("--camada")
    for campo in ("fonte", "url", "versao", "metodologia", "referencia"):
        parser.add_argument(f"--{campo}", required=True, type=str.strip)
    argumentos = parser.parse_args()
    if not all((argumentos.fonte, argumentos.versao, argumentos.metodologia, argumentos.referencia)):
        parser.error("Preencha os metadados científicos.")
    url = urlparse(argumentos.url)
    if url.scheme not in ("https", "http") or not url.hostname:
        parser.error("Informe uma URL pública.")
    if argumentos.arquivo.suffix.lower() not in (".geojson", ".gpkg"):
        parser.error("Use GeoJSON ou GeoPackage.")
    dados = gpd.read_file(argumentos.arquivo, layer=argumentos.camada)
    srid = dados.crs.to_epsg() if dados.crs else None
    if dados.empty or not {"nome", "classificacao"} <= set(dados.columns):
        raise ValueError("A camada precisa de polígonos e dos campos nome e classificacao.")
    if not srid:
        raise ValueError("A camada precisa de um CRS com código EPSG.")
    geometrias = dados.geometry
    if (not geometrias.geom_type.isin(["Polygon", "MultiPolygon"]).all()
            or geometrias.is_empty.any() or not geometrias.is_valid.all()):
        raise ValueError("A camada contém geometrias não poligonais, vazias ou inválidas.")
    registros = {}
    for _, linha in dados.iterrows():
        nomes = [linha.get(campo) for campo in ("nome", "classificacao")]
        if not all(isinstance(valor, str) and valor.strip() for valor in nomes):
            raise ValueError("Nome e classificação devem ser preenchidos em cada polígono.")
        nome, classificacao = (valor.strip() for valor in nomes)
        if nome in registros:
            raise ValueError(f"Nome de zona duplicado: {nome}.")
        descricao = linha.get("descricao")
        registros[nome] = (nome, classificacao, descricao if isinstance(descricao, str) else "",
                           argumentos.metodologia, argumentos.referencia, linha[dados.geometry.name].wkt, srid)
    with conectar() as conexao, conexao.cursor() as cursor:
        fonte = registrar(conexao, argumentos.fonte, argumentos.url, argumentos.versao)
        cursor.executemany(SQL, [(*registro, fonte) for registro in registros.values()])
    print(f"Zonas gravadas: {len(registros)}.")


if __name__ == "__main__":
    executar(principal)


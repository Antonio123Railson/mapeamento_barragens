import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode

from db.conexao import conectar
from modelo.fonte_dados import registrar
from scripts.comum import baixar, decimal, executar

URL = "https://earthquake.usgs.gov/fdsnws/event/1/"
TAMANHO_PAGINA = 1000
SQL = """
INSERT INTO eventos_sismicos (codigo_origem,data_hora,magnitude,profundidade_km,geometria,fonte_id)
SELECT %s,%s,%s,%s,ponto,%s FROM (SELECT ST_SetSRID(ST_MakePoint(%s,%s),4326) ponto) p
WHERE EXISTS (
    SELECT 1 FROM areas_importacao l
    WHERE ST_Intersects(l.geometria,p.ponto)
)
OR EXISTS (
    SELECT 1 FROM fronteira_importacao f
    WHERE ST_DWithin(f.segmento,p.ponto::geography,%s)
)
ON CONFLICT (codigo_origem) DO UPDATE SET data_hora=EXCLUDED.data_hora,
 magnitude=EXCLUDED.magnitude, profundidade_km=EXCLUDED.profundidade_km,
 geometria=EXCLUDED.geometria, fonte_id=EXCLUDED.fonte_id
"""


def ler_geojson(conteudo):
    if not conteudo.strip():
        return []
    dados = json.loads(conteudo)
    if (not isinstance(dados, dict) or dados.get("type") != "FeatureCollection"
            or not isinstance(dados.get("features"), list)):
        raise ValueError("O arquivo precisa ser uma FeatureCollection do USGS.")
    return dados["features"]


def consultar(inicio, fim, magnitude, margem):
    # Caixa conservadora de pré-seleção. O limite IBGE decide a inclusão final.
    folga = margem / 85
    deslocamento = 1
    while True:
        consulta = urlencode(dict(format="geojson", eventtype="earthquake", orderby="time-asc",
                                  starttime=inicio.isoformat(), endtime=fim.isoformat(),
                                  minmagnitude=magnitude, minlatitude=-35-folga,
                                  maxlatitude=6+folga, minlongitude=-75-folga,
                                  maxlongitude=-28+folga, limit=TAMANHO_PAGINA, offset=deslocamento))
        pagina = ler_geojson(baixar(URL + "query?" + consulta))
        yield from pagina
        if len(pagina) < TAMANHO_PAGINA:
            break
        deslocamento += len(pagina)


def normalizar(eventos, inicio, fim, magnitude_minima):
    registros = {}
    invalidos = 0
    for evento in eventos:
        try:
            codigo = evento["id"]
            propriedades = evento["properties"]
            if evento["geometry"]["type"] != "Point" or not isinstance(codigo, str) or not codigo.strip():
                raise ValueError("Identificação ou geometria inválida.")
            if propriedades.get("type", "earthquake") != "earthquake":
                continue
            lon, lat, profundidade = evento["geometry"]["coordinates"][:3]
            lon, lat = decimal(lon, -180, 180), decimal(lat, -90, 90)
            profundidade = None if profundidade is None else decimal(profundidade, -100, 1000)
            magnitude = decimal(propriedades["mag"], -10, 12)
            instante = datetime.fromtimestamp(float(propriedades["time"]) / 1000, timezone.utc)
            if inicio <= instante.date() <= fim and magnitude >= magnitude_minima:
                registros[codigo] = (codigo, instante, magnitude, profundidade, lon, lat)
        except (AttributeError, TypeError, ValueError, KeyError, OverflowError, OSError):
            invalidos += 1
    return registros, invalidos


def principal():
    parser = argparse.ArgumentParser(description="Importa terremotos do USGS no recorte territorial IBGE.")
    parser.add_argument("--inicio", required=True, type=date.fromisoformat)
    parser.add_argument("--fim", required=True, type=date.fromisoformat)
    parser.add_argument("--magnitude-minima", default=0, type=float)
    parser.add_argument("--margem-km", default=0, type=float)
    parser.add_argument("--limite", required=True, type=Path, help="Malha País do IBGE (ZIP, GPKG ou GeoJSON).")
    parser.add_argument("--arquivo", type=Path, help="GeoJSON USGS local.")
    argumentos = parser.parse_args()
    margem = decimal(argumentos.margem_km, 0, 1000)
    magnitude = decimal(argumentos.magnitude_minima, -10, 12)
    if not argumentos.inicio <= argumentos.fim < date.max:
        parser.error("Período inválido.")

    import geopandas as gpd

    caminho = f"zip://{argumentos.limite.resolve().as_posix()}" if argumentos.limite.suffix.lower() == ".zip" else argumentos.limite
    malha = gpd.read_file(caminho)
    if (malha.empty or not malha.crs or not malha.geometry.is_valid.all()
            or not malha.geometry.geom_type.isin(["Polygon", "MultiPolygon"]).all()):
        raise ValueError("A malha deve conter polígonos válidos e CRS conhecido.")
    limite = malha.to_crs(4326).geometry.union_all()
    if limite.is_empty or not limite.is_valid:
        raise ValueError("A união da malha territorial é inválida.")
    if argumentos.arquivo:
        eventos = ler_geojson(argumentos.arquivo.read_bytes())
    else:
        eventos = consultar(argumentos.inicio, argumentos.fim + timedelta(days=1), magnitude, margem)
    registros, invalidos = normalizar(eventos, argumentos.inicio, argumentos.fim, magnitude)
    if not registros:
        print(f"Nenhum evento elegível. Registros inválidos: {invalidos}.")
        return
    metros = margem * 1000
    versao = (f"{argumentos.inicio} a {argumentos.fim}, M≥{magnitude:g}, "
              f"malha {argumentos.limite.name}, margem {margem:g} km")
    with conectar() as conexao, conexao.cursor() as cursor:
        cursor.execute("SET LOCAL statement_timeout = '5min'")
        cursor.execute("CREATE TEMP TABLE limite_importacao (geometria geometry(Geometry,4326)) ON COMMIT DROP")
        cursor.execute("INSERT INTO limite_importacao VALUES (ST_Force2D(ST_GeomFromText(%s,4326)))", (limite.wkt,))
        cursor.execute("""
            CREATE TEMP TABLE areas_importacao ON COMMIT DROP AS
            SELECT pedaço geometria FROM limite_importacao l
            CROSS JOIN LATERAL ST_Subdivide(l.geometria,256) pedaço
        """)
        cursor.execute("CREATE INDEX ON areas_importacao USING gist (geometria)")
        cursor.execute("ANALYZE areas_importacao")
        cursor.execute("CREATE TEMP TABLE fronteira_importacao (segmento geography(LineString,4326)) ON COMMIT DROP")
        if margem > 0:
            # Agrupa vértices originais em trechos de 64 segmentos com um vértice de sobreposição.
            # Nenhum segmento geodésico precisa ser interpolado para criar o índice.
            cursor.execute("""
                INSERT INTO fronteira_importacao
                SELECT ST_MakeLine(ponto.geom ORDER BY ponto.path[1])::geography
                FROM limite_importacao l
                CROSS JOIN LATERAL ST_Dump(ST_Boundary(l.geometria)) linha
                CROSS JOIN LATERAL ST_DumpPoints(linha.geom) ponto
                CROSS JOIN LATERAL generate_series(
                    greatest(0, (ponto.path[1] - 2) / 64), (ponto.path[1] - 1) / 64
                ) AS trecho
                GROUP BY linha.path, trecho
                HAVING count(*) >= 2
            """)
            cursor.execute("CREATE INDEX ON fronteira_importacao USING gist (segmento)")
            cursor.execute("ANALYZE fronteira_importacao")
        fonte = registrar(conexao, "USGS · Earthquake Catalog", URL, versao)
        cursor.executemany(SQL, [(*linha[:4], fonte, *linha[4:], metros)
                                 for linha in registros.values()])
        gravados = cursor.rowcount
        if not gravados:
            conexao.rollback()
    print(f"Gravados: {gravados} | Fora do limite: {len(registros)-gravados} | Inválidos: {invalidos}.")


if __name__ == "__main__":
    executar(principal)


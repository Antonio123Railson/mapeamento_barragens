import os
from datetime import date

import psycopg
import pytest
from psycopg.rows import dict_row

from main import criar_app
from modelo import analise
from scripts import importar_sismos
from scripts.importar_sismos import ler_geojson, normalizar


@pytest.fixture
def cliente():
    return criar_app().test_client()


@pytest.mark.parametrize("consulta", ["raio_km=0", "raio_km=inf", "raio_km=1001",
                                      "inicio=2025-01-02&fim=2025-01-01",
                                      "inicio=2025-02-30", "magnitude_minima=NaN"])
def test_validacao(cliente, consulta):
    assert cliente.get("/api/analises/barragem/1?" + consulta).status_code == 400


def test_ausente_e_sem_coordenadas(cliente, monkeypatch):
    monkeypatch.setattr(analise, "proximidade", lambda *_: None)
    assert cliente.get("/api/analises/barragem/1").status_code == 404
    monkeypatch.setattr(analise, "proximidade", lambda *_: {"barragem": {"geometry": None}})
    assert cliente.get("/api/analises/barragem/1").status_code == 400


def test_importador_sismos():
    assert ler_geojson(b"") == []
    evento = {"id": "us1", "geometry": {"type": "Point", "coordinates": [-45, -20, 8]},
              "properties": {"time": 1704067200000, "mag": 4.5}}
    registros, invalidos = normalizar([evento, evento, {}], date(2024, 1, 1), date(2024, 1, 1), 4)
    assert (set(registros), invalidos) == ({"us1"}, 1)
    assert registros["us1"][1].isoformat() == "2024-01-01T00:00:00+00:00"


def test_paginacao_usgs(monkeypatch):
    import json
    from urllib.parse import parse_qs, urlsplit

    offsets = []

    def baixar(url):
        offset = parse_qs(urlsplit(url).query)["offset"][0]
        offsets.append(offset)
        pagina = ["a", "b"] if offset == "1" else ["c"]
        return json.dumps({"type": "FeatureCollection", "features": pagina}).encode()

    monkeypatch.setattr(importar_sismos, "baixar", baixar)
    monkeypatch.setattr(importar_sismos, "TAMANHO_PAGINA", 2)
    assert list(importar_sismos.consultar(date(2024, 1, 1), date(2024, 2, 1), 3, 0)) == ["a", "b", "c"]
    assert offsets == ["1", "3"]


def test_distancias_reais_postgis(cliente, monkeypatch):
    dsn = os.getenv("TESTE_POSTGIS_DSN")
    if not dsn:
        pytest.skip("Defina TESTE_POSTGIS_DSN para testar a distância no PostGIS.")
    # Tabelas temporárias isolam os registros de teste do catálogo acadêmico.
    with psycopg.connect(dsn, row_factory=dict_row) as conexao:
        conexao.execute("SET TIME ZONE 'UTC'")
        conexao.execute("""
            CREATE TEMP TABLE barragens (id int, nome text, geometria geometry(Point,4326));
            CREATE TEMP TABLE fontes_dados (id int, nome text, endereco_url text,
                                            data_coleta timestamptz, versao text);
            CREATE TEMP TABLE eventos_sismicos (id int, codigo_origem text, data_hora timestamptz,
                magnitude float8, profundidade_km float8, geometria geometry(Point,4326), fonte_id int);
            CREATE TEMP TABLE zonas_sismogenicas (nome text, referencia_cientifica text,
                                                metodologia text, geometria geometry(Polygon,4326));
            INSERT INTO barragens VALUES (1, 'Teste', ST_SetSRID(ST_Point(0,0),4326));
            INSERT INTO fontes_dados VALUES (1,'Teste','https://example.org',now(),'teste');
            INSERT INTO eventos_sismicos VALUES
                (1,'a','2024-01-31 23:59:59+00',4,10,ST_SetSRID(ST_Point(0.1,0),4326),1),
                (2,'b','2024-01-10',5,5,ST_SetSRID(ST_Point(0.2,0),4326),1),
                (3,'c','2024-01-10',9,5,ST_SetSRID(ST_Point(1,0),4326),1),
                (4,'d','2024-02-01',6,5,ST_SetSRID(ST_Point(0.1,0),4326),1),
                (5,'e','2024-01-10',2,5,ST_SetSRID(ST_Point(0.1,0),4326),1);
        """)
        def consultar(sql, valores):
            return conexao.execute(sql, valores).fetchall()

        monkeypatch.setattr(analise, "consultar", consultar)
        resposta = cliente.get("/api/analises/barragem/1?raio_km=25&fim=2024-01-31&magnitude_minima=3&limite=1")
        assert resposta.status_code == 200
        dados = resposta.json
        assert dados["total"] == 2
        assert dados["menor_distancia_km"] == pytest.approx(11.132, abs=0.01)
        assert dados["maior_magnitude"] == 5
        assert dados["por_ano"] == [{"ano": 2024, "total": 2}]
        assert dados["paginacao"]["mais"]
        assert dados["eventos"]["features"][0]["properties"]["codigo_origem"] == "a"


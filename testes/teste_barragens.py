from datetime import date
from io import StringIO

import pytest

from main import criar_app
from modelo import barragem
from scripts.importar_barragens import COLUNAS, FINALIDADE, coordenada, ler_csv, normalizar


@pytest.fixture
def cliente():
    return criar_app().test_client()


def test_api_geojson_e_filtros(cliente, monkeypatch):
    parametros = []

    def consultar(sql, valores):
        parametros.extend(valores)
        assert "ST_Intersects" in sql
        assert "Itabira" not in sql
        return [{"id": 1, "nome": "Barragem de teste",
                 "data_atualizacao": date(2024, 3, 1),
                 "geometria": '{"type":"Point","coordinates":[-43,-19]}'}]

    monkeypatch.setattr(barragem, "consultar", consultar)
    resposta = cliente.get("/api/barragens?uf=mg&municipio=Itabira&bbox=-50,-30,-40,-10&limite=2&pagina=2")
    assert resposta.status_code == 200
    assert resposta.json["type"] == "FeatureCollection"
    assert resposta.json["features"][0]["properties"]["data_atualizacao"] == "2024-03-01"
    assert parametros == [-50, -30, -40, -10, "MG", "Itabira", 3, 2]


@pytest.mark.parametrize("query", ["uf=XX", "bbox=-30,-40,-80,0", "bbox=NaN,0,1,2",
                                  "limite=501", "pagina=0", "mapeada=sim"])
def test_filtros_invalidos(cliente, query):
    assert cliente.get("/api/barragens?" + query).status_code == 400


def test_barragem_ausente(cliente, monkeypatch):
    monkeypatch.setattr(barragem, "buscar", lambda _: None)
    assert cliente.get("/api/barragens/1").status_code == 404
    assert cliente.get("/api/barragens/invalida").status_code == 400


def test_falha_interna_generica(cliente, monkeypatch):
    def falhar(_):
        raise RuntimeError("informação interna")
    monkeypatch.setattr(barragem, "buscar", falhar)
    resposta = cliente.get("/api/barragens/1")
    assert resposta.status_code == 500
    assert "informação interna" not in resposta.get_data(as_text=True)


@pytest.mark.parametrize("rota", ["/", "/mapa", "/barragens", "/analises", "/sobre"])
def test_paginas(cliente, rota):
    resposta = cliente.get(rota)
    assert resposta.status_code == 200
    assert 'lang="pt-BR"' in resposta.get_data(as_text=True)


def test_normalizacao_anm():
    import csv

    arquivo = StringIO()
    escritor = csv.writer(arquivo)
    escritor.writerow([*COLUNAS.values(), FINALIDADE])
    escritor.writerow(["42", "MG", "Teste", "Itabira", "-19°30'00.0''", "-43°10'30.0''", "Baixo", "Alto", "Rejeitos"])
    escritor.writerow(["43", "PA", "Teste 2", "Marabá", "", "", "", "", "Mista"])
    escritor.writerow(["44", "MG", "Teste 3", "Itabira", "-19", "-43", "", "", "Sedimentos"])
    leitor, codificacao, separador = ler_csv(arquivo.getvalue().encode("cp1252"))
    registros, ausentes, invalidos, fora = normalizar(
        leitor, COLUNAS, FINALIDADE, {"rejeitos", "mista"}, date(2024, 3, 1))
    assert (codificacao, separador, ausentes, invalidos, fora) == ("cp1252", ",", 1, 0, 1)
    assert registros["42"][6:8] == pytest.approx((-43.175, -19.5))
    assert registros["43"][6:8] == (None, None)


@pytest.mark.parametrize("valor", ["91", "NaN", "-19°60'00''", "90°00'01''", ""])
def test_rejeita_coordenada_invalida(valor):
    with pytest.raises(ValueError):
        coordenada(valor, 90)


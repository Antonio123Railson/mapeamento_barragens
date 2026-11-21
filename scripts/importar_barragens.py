import argparse
import csv
import io
import re
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path

from db.conexao import conectar
from modelo.fonte_dados import registrar
from scripts.comum import baixar, decimal, executar

URL = "https://dadosabertos.anm.gov.br/SIGBM/Barragens.csv"
FINALIDADE = "Estrutura com o Objetivo de Contenção"
COLUNAS = {
    "codigo": "ID",
    "uf": "UF",
    "nome": "Nome",
    "municipio": "Município",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "risco": "Categoria de Risco - CRI",
    "dano": "Dano Potencial Associado - DPA",
}
UF_BR = frozenset("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())
SQL = """
INSERT INTO barragens
(codigo_anm, nome, municipio, uf, categoria_risco, dano_potencial, geometria, fonte_id, data_atualizacao)
VALUES (%s,%s,%s,%s,%s,%s,ST_SetSRID(ST_MakePoint(%s,%s),4326),%s,%s)
ON CONFLICT (codigo_anm) DO UPDATE SET
 nome=EXCLUDED.nome, municipio=EXCLUDED.municipio, uf=EXCLUDED.uf,
 categoria_risco=EXCLUDED.categoria_risco, dano_potencial=EXCLUDED.dano_potencial,
 geometria=EXCLUDED.geometria, fonte_id=EXCLUDED.fonte_id, data_atualizacao=EXCLUDED.data_atualizacao
WHERE barragens.data_atualizacao IS NULL OR EXCLUDED.data_atualizacao >= barragens.data_atualizacao
"""


def ler_csv(conteudo):
    for codificacao in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texto = conteudo.decode(codificacao)
            break
        except UnicodeDecodeError:
            continue
    linha = texto.splitlines()[0] if texto.splitlines() else ""
    if not linha:
        raise ValueError("CSV vazio.")
    separador = max((";", ",", "\t"), key=lambda sep: len(next(csv.reader([linha], delimiter=sep))))
    leitor = csv.DictReader(io.StringIO(texto, newline=""), delimiter=separador)
    leitor.fieldnames = [campo.strip() for campo in leitor.fieldnames]
    if len(leitor.fieldnames) < 2 or len(set(leitor.fieldnames)) != len(leitor.fieldnames):
        raise ValueError("Cabeçalho CSV inválido ou com colunas duplicadas.")
    return leitor, codificacao, separador


def coordenada(valor, maximo):
    dms = re.fullmatch(r"""([+\-]?)(\d{1,3})°\s*(\d{1,2})'\s*(\d+(?:[.,]\d+)?)(?:''|")""", valor)
    if not dms:
        return decimal(valor, -maximo, maximo)
    sinal, graus, minutos, segundos = dms.groups()
    minutos, segundos = int(minutos), decimal(segundos, 0, 60)
    if minutos >= 60 or segundos >= 60:
        raise ValueError("Minutos ou segundos fora da faixa.")
    convertido = (int(graus) + minutos / 60 + segundos / 3600) * (-1 if sinal == "-" else 1)
    return decimal(convertido, -maximo, maximo)


def normalizar(leitor, colunas, coluna_finalidade, valores, data_base):
    registros = {}
    sem_coordenadas = invalidos = fora_escopo = 0
    exigidas = set(colunas.values()) | {coluna_finalidade}
    faltantes = exigidas - set(leitor.fieldnames)
    if faltantes:
        raise ValueError("Colunas ausentes: " + ", ".join(sorted(faltantes)))
    for linha in leitor:
        if None in linha or any(linha[campo] is None for campo in exigidas):
            invalidos += 1
            continue
        if linha[coluna_finalidade].strip().casefold() not in valores:
            fora_escopo += 1
            continue
        dados = {chave: linha[campo].strip() for chave, campo in colunas.items()}
        codigo, uf = dados["codigo"], dados["uf"].upper()
        if not codigo or not dados["nome"] or not dados["municipio"] or uf not in UF_BR:
            invalidos += 1
            continue
        try:
            lon = coordenada(dados["longitude"], 180)
            lat = coordenada(dados["latitude"], 90)
            if lon == lat == 0:
                raise ValueError("Coordenada de preenchimento.")
        except ValueError:
            lon = lat = None
            sem_coordenadas += 1
        data = data_base
        if dados.get("atualizacao"):
            try:
                data = (datetime.strptime(dados["atualizacao"], "%d/%m/%Y").date()
                        if "/" in dados["atualizacao"] else date.fromisoformat(dados["atualizacao"]))
            except ValueError:
                invalidos += 1
                continue
        registro = (codigo, dados["nome"], dados["municipio"], uf, dados["risco"] or None,
                    dados["dano"] or None, lon, lat, data)
        anterior = registros.get(codigo)
        if anterior and anterior != registro:
            raise ValueError(f"Identificador oficial repetido com registros conflitantes: {codigo}.")
        registros[codigo] = registro
    return registros, sem_coordenadas, invalidos, fora_escopo


def principal():
    parser = argparse.ArgumentParser(description="Importa barragens de rejeitos do CSV oficial SIGBM.")
    parser.add_argument("arquivo", nargs="?", type=Path)
    parser.add_argument("--inspecionar", action="store_true")
    parser.add_argument("--coluna-codigo", default=COLUNAS["codigo"], help="Cabeçalho do identificador SIGBM.")
    parser.add_argument("--coluna-uf", default=COLUNAS["uf"], help="Cabeçalho da unidade federativa.")
    parser.add_argument("--coluna-finalidade", default=FINALIDADE, help="Cabeçalho de finalidade da estrutura.")
    parser.add_argument("--valor-rejeitos", action="append", help="Categoria exata a incluir. Repetível.")
    parser.add_argument("--coluna-atualizacao")
    parser.add_argument("--data-base", type=date.fromisoformat, help="Data da edição do CSV.")
    parser.add_argument("--validar", action="store_true", help="Normaliza e conta sem gravar.")
    argumentos = parser.parse_args()
    conteudo = argumentos.arquivo.read_bytes() if argumentos.arquivo else baixar(URL)
    leitor, codificacao, separador = ler_csv(conteudo)
    print(f"Codificação: {codificacao} | Separador: {separador!r}")
    if argumentos.inspecionar:
        print("\n".join(leitor.fieldnames))
        if argumentos.coluna_finalidade in leitor.fieldnames:
            print("Valores:", sorted({(linha.get(argumentos.coluna_finalidade) or "").strip()
                                      for linha in leitor}))
        return
    if not argumentos.data_base:
        parser.error("Informe --data-base com a data da edição do arquivo.")
    colunas = COLUNAS | {"codigo": argumentos.coluna_codigo, "uf": argumentos.coluna_uf}
    if argumentos.coluna_atualizacao:
        colunas["atualizacao"] = argumentos.coluna_atualizacao
    valores = {valor.strip().casefold() for valor in (argumentos.valor_rejeitos or ["Rejeitos", "Mista"])
               if valor.strip()}
    registros, ausentes, invalidos, fora_escopo = normalizar(
        leitor, colunas, argumentos.coluna_finalidade, valores, argumentos.data_base)
    print(f"Elegíveis: {len(registros)} | Coordenadas ausentes/inválidas: {ausentes} | "
          f"Linhas inválidas: {invalidos} | Fora do recorte: {fora_escopo}")
    if not registros:
        raise ValueError("Nenhum registro elegível. Confira os valores de finalidade.")
    if argumentos.validar:
        return
    versao = f"{argumentos.data_base} / SHA-256 {sha256(conteudo).hexdigest()}"
    with conectar() as conexao, conexao.cursor() as cursor:
        fonte = registrar(conexao, "ANM · SIGBM", URL, versao)
        cursor.executemany(SQL, [(*linha[:-1], fonte, linha[-1]) for linha in registros.values()])
        gravados = cursor.rowcount
    print(f"Registros inseridos ou atualizados: {gravados}.")


if __name__ == "__main__":
    executar(principal)


from flask import Blueprint, request

from controle import controle_barragens
from modelo.barragem import estatisticas

bp = Blueprint("barragens", __name__, url_prefix="/api")


@bp.get("/barragens")
def listar():
    return controle_barragens.listar(request.args)


@bp.get("/barragens/<id>")
def buscar(id):
    return controle_barragens.buscar(id)


@bp.get("/estatisticas")
def resumo():
    return estatisticas()


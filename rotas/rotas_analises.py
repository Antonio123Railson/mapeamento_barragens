from flask import Blueprint, request

from controle import controle_analises

bp = Blueprint("analises", __name__, url_prefix="/api/analises")


@bp.get("/proximidade")
def proximidade():
    return controle_analises.proximidade(request.args)


@bp.get("/barragem/<id>")
def por_barragem(id):
    return controle_analises.proximidade(request.args, id)


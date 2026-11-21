from flask import Blueprint, request

from controle import controle_zonas

bp = Blueprint("zonas", __name__, url_prefix="/api")


@bp.get("/zonas")
def listar():
    return controle_zonas.listar(request.args)


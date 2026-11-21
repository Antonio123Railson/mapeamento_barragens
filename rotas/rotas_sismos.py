from flask import Blueprint, request

from controle import controle_sismos

bp = Blueprint("sismos", __name__, url_prefix="/api")


@bp.get("/sismos")
def listar():
    return controle_sismos.listar(request.args)


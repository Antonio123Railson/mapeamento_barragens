from flask import Blueprint, render_template

from controle.controle_barragens import UFS

bp = Blueprint("paginas", __name__)


@bp.get("/")
def inicio():
    return render_template("index.html")


@bp.get("/mapa")
def mapa():
    return render_template("mapa.html", ufs=UFS)


@bp.get("/barragens")
def barragens():
    return render_template("barragens.html", ufs=UFS)


@bp.get("/analises")
def analises():
    return render_template("analises.html", ufs=UFS)


@bp.get("/sobre")
def sobre():
    return render_template("sobre.html")


import os

from dotenv import load_dotenv
from flask import Flask, request
from werkzeug.exceptions import HTTPException

from controle.validacao import EntradaInvalida, RegistroAusente
from rotas import rotas_analises, rotas_barragens, rotas_paginas, rotas_sismos, rotas_zonas


def criar_app():
    load_dotenv()
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY") or None
    for modulo in (rotas_paginas, rotas_barragens, rotas_sismos, rotas_zonas, rotas_analises):
        app.register_blueprint(modulo.bp)

    @app.errorhandler(EntradaInvalida)
    def entrada_invalida(erro):
        return {"erro": str(erro)}, 400

    @app.errorhandler(RegistroAusente)
    def registro_ausente(erro):
        return {"erro": str(erro)}, 404

    @app.errorhandler(Exception)
    def tratar_erro(erro):
        if isinstance(erro, HTTPException):
            if request.path.startswith("/api/"):
                return {"erro": "Rota indisponível."}, erro.code
            return erro
        app.logger.exception("Falha ao processar %s", request.path)
        if request.path.startswith("/api/"):
            return {"erro": "Não foi possível consultar os dados. Tente novamente mais tarde."}, 500
        return "Falha interna.", 500

    return app


app = criar_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", debug=os.getenv("FLASK_DEBUG", "").lower() in ("1", "true"),
            use_debugger=False)


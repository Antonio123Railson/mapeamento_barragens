def registrar(conexao, nome, endereco, versao):
    return conexao.execute(
        """INSERT INTO fontes_dados (nome, endereco_url, versao)
           VALUES (%s, %s, %s) RETURNING id""",
        (nome, endereco, versao),
    ).fetchone()["id"]


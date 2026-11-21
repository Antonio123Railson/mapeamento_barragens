import { consultar, dataUTC, elemento, fonteLink, parametros } from "./api.js";

const formulario = document.querySelector("#filtros-barragens");
const status = document.querySelector("#barragens-status");
const tabela = document.querySelector("#lista-barragens");
const anterior = document.querySelector("#anterior");
const proxima = document.querySelector("#proxima");
const dialogo = document.querySelector("#detalhes");
const corpo = document.querySelector("#detalhes-corpo");
let filtros = parametros(formulario);
let pagina = 1;
let requisicao;
let detalhe;

async function listar(numero) {
  requisicao?.abort();
  const atual = new AbortController();
  requisicao = atual;
  const consulta = new URLSearchParams(filtros);
  consulta.set("limite", "25");
  consulta.set("pagina", numero);
  anterior.disabled = proxima.disabled = true;
  status.textContent = "Consultando barragens…";
  try {
    const dados = await consultar("/api/barragens", consulta, atual.signal);
    if (atual.signal.aborted) return;
    pagina = numero;
    tabela.replaceChildren(...dados.features.map(feicao => {
      const p = feicao.properties;
      const botao = elemento("button", p.nome);
      botao.className = "link-botao";
      botao.addEventListener("click", () => abrir(feicao.id));
      const linha = elemento("tr", "");
      const celula = elemento("td", "");
      celula.append(botao);
      linha.append(celula, ...[p.municipio, p.uf, p.categoria_risco, p.dano_potencial]
        .map(valor => elemento("td", valor)));
      return linha;
    }));
    status.textContent = dados.features.length
      ? "Página " + pagina + " · " + dados.features.length + " barragens"
      : "Nenhuma barragem encontrada para os filtros selecionados.";
    anterior.disabled = pagina === 1;
    proxima.disabled = !dados.paginacao.mais;
  } catch (erro) {
    if (!atual.signal.aborted) {
      status.textContent = erro.message;
      tabela.replaceChildren();
    }
  }
}

async function abrir(id) {
  detalhe?.abort();
  const atual = new AbortController();
  detalhe = atual;
  document.querySelector("#detalhes-titulo").textContent = "Detalhes da barragem";
  corpo.textContent = "Consultando…";
  if (!dialogo.open) dialogo.showModal();
  try {
    const dados = await consultar("/api/barragens/" + id, undefined, atual.signal);
    if (atual.signal.aborted) return;
    const p = dados.properties;
    document.querySelector("#detalhes-titulo").textContent = p.nome;
    corpo.replaceChildren(...[
      "Código ANM: " + p.codigo_anm,
      p.municipio + " · " + p.uf,
      "Categoria de risco: " + (p.categoria_risco ?? "—"),
      "Dano potencial: " + (p.dano_potencial ?? "—"),
      "Atualização: " + (p.data_atualizacao ?? "—"),
      "Coleta: " + dataUTC(p.data_coleta) + " UTC"
    ].map(texto => elemento("p", texto)), fonteLink(p.fonte, p.fonte_url));
    const posicao = elemento("p", "Coordenadas indisponíveis.");
    if (dados.geometry) {
      const link = elemento("a", "Analisar proximidade");
      link.href = "/analises?barragem_id=" + id;
      posicao.replaceChildren(link);
    }
    corpo.append(posicao);
  } catch (erro) {
    if (!atual.signal.aborted) corpo.textContent = erro.message;
  }
}

dialogo.addEventListener("close", () => detalhe?.abort());
anterior.addEventListener("click", () => listar(pagina - 1));
proxima.addEventListener("click", () => listar(pagina + 1));
formulario.addEventListener("submit", evento => {
  evento.preventDefault();
  filtros = parametros(formulario);
  listar(1);
});
listar(1);


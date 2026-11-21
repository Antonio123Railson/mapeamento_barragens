import { consultar, dataUTC, decimal, elemento, fonteLink, parametros } from "./api.js";
import { criarCamada, criarMapa } from "./camadas.js";

const busca = document.querySelector("#busca-analise");
const formulario = document.querySelector("#form-analise");
const opcoes = formulario.elements.barragem_id;
const status = document.querySelector("#analise-status");
const resultado = document.querySelector("#resultado");
const anterior = document.querySelector("#eventos-anterior");
const proxima = document.querySelector("#eventos-proxima");
let pagina = 1;
let filtros;
let buscaAtual;
let consultaAtual;
let mapa;
let pontos;
let circulo;
let centro;
let grafico;

async function carregarBarragens(id) {
  buscaAtual?.abort();
  const atual = new AbortController();
  buscaAtual = atual;
  status.textContent = "Buscando barragens…";
  try {
    const query = parametros(busca);
    query.set("limite", "100");
    query.set("mapeada", "1");
    const dados = await consultar("/api/barragens", query, atual.signal);
    const itens = dados.features;
    if (id && !itens.some(item => String(item.id) === id)) {
      const escolhida = await consultar("/api/barragens/" + encodeURIComponent(id), undefined, atual.signal);
      if (escolhida.geometry) itens.unshift(escolhida);
    }
    if (atual.signal.aborted) return;
    opcoes.replaceChildren(new Option("Escolha uma barragem", ""), ...itens.map(item =>
      new Option(item.properties.nome + " · " + item.properties.municipio + "/" + item.properties.uf, item.id)));
    if (id) opcoes.value = id;
    status.textContent = itens.length
      ? (dados.paginacao.mais ? "Refine a busca para encontrar barragens além das 100 primeiras." : "")
      : "Nenhuma barragem com coordenadas encontrada.";
  } catch (erro) {
    if (!atual.signal.aborted) status.textContent = erro.message;
  }
}

function exibirMapa(dados, mover) {
  if (!window.L) {
    document.querySelector("#mapa-analise").textContent = "Biblioteca de mapa indisponível.";
    return;
  }
  const [lon, lat] = dados.barragem.geometry.coordinates;
  if (!mapa) {
    mapa = criarMapa("mapa-analise");
    circulo = L.circle([lat, lon], { color: "#096b68", fillOpacity: .12 }).addTo(mapa);
    pontos = criarCamada("sismos").addTo(mapa);
    centro = L.marker([lat, lon], {
      icon: L.divIcon({ className: "icone-barragem", iconSize: [13, 13] })
    }).addTo(mapa);
  }
  circulo.setLatLng([lat, lon]).setRadius(dados.parametros.raio_km * 1000);
  centro.setLatLng([lat, lon]).bindTooltip(elemento("span", dados.barragem.properties.nome));
  pontos.clearLayers().addData(dados.eventos);
  if (mover) {
    mapa.invalidateSize();
    mapa.fitBounds(circulo.getBounds(), { padding: [18, 18], maxZoom: 15 });
  }
}

function exibir(dados, mover) {
  const p = dados.parametros;
  const texto = (id, valor) => { document.querySelector("#" + id).textContent = valor; };
  resultado.hidden = false;
  texto("resultado-titulo", dados.barragem.properties.nome);
  texto("parametros", "Raio " + decimal.format(p.raio_km) + " km · Magnitude mínima " +
    decimal.format(p.magnitude_minima) + " · " + (p.inicio ?? "Sem início") + " a " + (p.fim ?? "sem fim") + " (UTC)");
  texto("zonas-resultado", dados.zonas.length ? "Zonas que contêm a barragem: " +
    dados.zonas.map(zona => zona.nome + " (" + zona.referencia + ")").join(", ") : "");
  texto("total", decimal.format(dados.total));
  texto("distancia", dados.menor_distancia_km == null ? "—" : decimal.format(dados.menor_distancia_km) + " km");
  texto("magnitude", dados.maior_magnitude == null ? "—" : decimal.format(dados.maior_magnitude));
  texto("eventos-pagina", "Página " + dados.paginacao.pagina);
  document.querySelector("#lista-eventos").replaceChildren(...dados.eventos.features.map(feicao => {
    const e = feicao.properties;
    const linha = elemento("tr", "");
    const fonte = elemento("td", "");
    fonte.append(fonteLink(e.fonte, e.fonte_url));
    linha.append(...[e.codigo_origem, dataUTC(e.data_hora), decimal.format(e.magnitude),
      e.profundidade_km == null ? "—" : decimal.format(e.profundidade_km) + " km",
      decimal.format(e.distancia_km) + " km"].map(valor => elemento("td", valor)), fonte);
    return linha;
  }));
  exibirMapa(dados, mover);
  texto("serie-anual", dados.por_ano.map(ano => ano.ano + ": " + ano.total).join(" · ") || "Sem eventos no período.");
  if (mover && window.Chart) {
    grafico?.destroy();
    grafico = new Chart(document.querySelector("#grafico"), {
      type: "bar",
      data: { labels: dados.por_ano.map(ano => ano.ano),
        datasets: [{ label: "Eventos", data: dados.por_ano.map(ano => ano.total), backgroundColor: "#137965" }] },
      options: { animation: false, scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
        plugins: { legend: { display: false } } }
    });
  }
}

async function analisar(numero, mover = false) {
  consultaAtual?.abort();
  const atual = new AbortController();
  consultaAtual = atual;
  const query = new URLSearchParams(filtros);
  query.set("pagina", numero);
  query.set("limite", "50");
  anterior.disabled = proxima.disabled = true;
  status.textContent = "Calculando distâncias…";
  if (mover) resultado.hidden = true;
  try {
    const dados = await consultar("/api/analises/proximidade", query, atual.signal);
    if (atual.signal.aborted) return;
    pagina = numero;
    exibir(dados, mover);
    anterior.disabled = numero === 1;
    proxima.disabled = !dados.paginacao.mais;
    status.textContent = dados.total ? "" : "Nenhum evento registrado no recorte selecionado.";
  } catch (erro) {
    if (!atual.signal.aborted) {
      status.textContent = erro.message;
      if (!mover) {
        anterior.disabled = pagina === 1;
        proxima.disabled = numero < pagina;
      }
    }
  }
}

busca.addEventListener("submit", evento => {
  evento.preventDefault();
  carregarBarragens();
});
formulario.addEventListener("submit", evento => {
  evento.preventDefault();
  filtros = parametros(formulario);
  analisar(1, true);
});
anterior.addEventListener("click", () => analisar(pagina - 1));
proxima.addEventListener("click", () => analisar(pagina + 1));
document.querySelector("#relatorio").addEventListener("click", () => window.print());
carregarBarragens(new URLSearchParams(location.search).get("barragem_id"));


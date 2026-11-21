import { consultar, parametros } from "./api.js";
import { brasil, criarCamada, criarMapa } from "./camadas.js";

const status = document.querySelector("#mapa-status");
if (window.L) iniciar();
else status.textContent = "Leaflet indisponível. Confira o acesso à biblioteca externa.";

function iniciar() {
  const zonaStatus = document.querySelector("#zonas-status");
  const formulario = document.querySelector("#filtros-mapa");
  const mapa = criarMapa("mapa", () => {
    const area = document.querySelector("#mapa");
    if (area.querySelector(".aviso-tiles")) return;
    const aviso = L.control({ position: "bottomleft" });
    aviso.onAdd = () => {
      const elemento = L.DomUtil.create("div", "aviso-tiles");
      elemento.textContent = "Falha ao carregar parte do mapa-base.";
      return elemento;
    };
    aviso.addTo(mapa);
  }).fitBounds(brasil);
  const controles = [...document.querySelectorAll("[data-camada]")];
  const camadas = new Map(controles.map(item => [item.dataset.camada, criarCamada(item.dataset.camada).addTo(mapa)]));
  let filtros = parametros(formulario);
  let requisicao;

  async function atualizar() {
    requisicao?.abort();
    const atual = new AbortController();
    requisicao = atual;
    const area = mapa.getBounds();
    const bbox = [Math.max(-180, area.getWest()), Math.max(-90, area.getSouth()),
      Math.min(180, area.getEast()), Math.min(90, area.getNorth())].map(valor => valor.toFixed(6)).join(",");
    const ativos = controles.filter(item => item.checked && !item.disabled);
    status.textContent = ativos.length ? "Consultando área visível…" : "Ative uma camada para exibir os dados.";
    const resultados = await Promise.allSettled(ativos.map(async item => {
      const tipo = item.dataset.camada;
      const chaves = { barragens: ["uf", "municipio"], sismos: ["magnitude_minima", "inicio", "fim"], zonas: [] };
      const query = new URLSearchParams({ bbox, limite: tipo === "zonas" ? 50 : 500 });
      for (const chave of chaves[tipo]) if (filtros.has(chave)) query.set(chave, filtros.get(chave));
      const dados = await consultar("/api/" + tipo, query, atual.signal);
      if (atual.signal.aborted) return {};
      camadas.get(tipo).clearLayers().addData(dados);
      if (tipo === "zonas") {
        item.disabled = !dados.disponivel;
        item.checked = dados.disponivel;
        zonaStatus.textContent = dados.mensagem ?? "";
      }
      return { total: dados.features.length, mais: dados.paginacao.mais };
    }));
    if (atual.signal.aborted || !ativos.length) return;
    const mensagens = resultados.flatMap((resultado, indice) => {
      if (resultado.status === "fulfilled") return [];
      camadas.get(ativos[indice].dataset.camada).clearLayers();
      return [ativos[indice].dataset.camada + ": " + resultado.reason.message];
    });
    const exibidos = resultados.flatMap(item => item.status === "fulfilled" ? [item.value] : []);
    const total = exibidos.reduce((soma, item) => soma + item.total, 0);
    const recorte = exibidos.some(item => item.mais) ? " Limite atingido. Aproxime a área ou refine os filtros." : "";
    status.textContent = (exibidos.length ? total + " feições na área visível." + recorte + " " : "") + mensagens.join(" ");
  }

  mapa.on("moveend", atualizar);
  formulario.addEventListener("submit", evento => {
    evento.preventDefault();
    filtros = parametros(formulario);
    atualizar();
  });
  document.querySelector("#restaurar").addEventListener("click", () => mapa.fitBounds(brasil));
  controles.forEach(item => item.addEventListener("change", () => {
    const camada = camadas.get(item.dataset.camada);
    if (item.checked) camada.clearLayers().addTo(mapa);
    else camada.remove();
    atualizar();
  }));
  atualizar();
}


import { dataUTC, decimal, elemento, fonteLink } from "./api.js";

export const brasil = [[-34, -74], [6, -29]];

export function criarMapa(id, aviso) {
  const mapa = L.map(id, { preferCanvas: true, minZoom: 3,
    maxBounds: [[-85, -179], [85, 179]], maxBoundsViscosity: 1 });
  const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19, noWrap: true
  }).addTo(mapa);
  if (aviso) tiles.on("tileerror", aviso);
  L.control.scale({ imperial: false }).addTo(mapa);
  return mapa;
}

export function criarCamada(tipo) {
  return L.geoJSON(null, {
    style: { color: "#7641a1", weight: 2, dashArray: "5 4", fillColor: "#c8a6ee", fillOpacity: .35 },
    pointToLayer(feicao, posicao) {
      if (tipo === "barragens") {
        return L.marker(posicao, { title: feicao.properties.nome,
          icon: L.divIcon({ className: "icone-barragem", iconSize: [13, 13] }) });
      }
      return L.circleMarker(posicao, { radius: 5, color: "#fff", weight: 1.5,
        fillColor: "#c94926", fillOpacity: .9 });
    },
    onEachFeature(feicao, camada) {
      const p = feicao.properties;
      const popup = elemento("div", "");
      popup.className = "popup";
      if (tipo === "barragens") {
        const link = elemento("a", "Analisar proximidade");
        link.href = "/analises?barragem_id=" + encodeURIComponent(feicao.id);
        popup.append(elemento("h3", p.nome), elemento("p", p.municipio + " · " + p.uf),
          elemento("p", "Categoria de risco: " + (p.categoria_risco ?? "—")),
          elemento("p", "Dano potencial: " + (p.dano_potencial ?? "—")), link);
      } else if (tipo === "sismos") {
        popup.append(elemento("h3", "Magnitude " + decimal.format(p.magnitude)),
          elemento("p", dataUTC(p.data_hora) + " UTC"),
          elemento("p", p.profundidade_km == null ? "Profundidade indisponível" :
            "Profundidade: " + decimal.format(p.profundidade_km) + " km"));
      } else {
        popup.append(elemento("h3", p.nome), elemento("p", p.classificacao), elemento("p", p.descricao),
          elemento("p", p.metodologia), elemento("p", p.referencia_cientifica));
      }
      if (p.fonte) popup.append(elemento("br", ""), fonteLink(p.fonte, p.fonte_url),
        elemento("p", "Coleta: " + dataUTC(p.data_coleta) + " UTC"));
      camada.bindPopup(popup);
    }
  });
}


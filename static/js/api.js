export function parametros(formulario) {
  return new URLSearchParams([...new FormData(formulario)]
    .map(([chave, valor]) => [chave, valor.trim()])
    .filter(([, valor]) => valor !== ""));
}

export async function consultar(caminho, filtros = new URLSearchParams(), signal) {
  const resposta = await fetch(caminho + (filtros.size ? "?" + filtros : ""), { signal });
  const dados = await resposta.json();
  if (!resposta.ok) throw new Error(dados.erro || "Falha na consulta.");
  return dados;
}

export function elemento(tag, texto) {
  const item = document.createElement(tag);
  item.textContent = texto ?? "—";
  return item;
}

export function fonteLink(nome, endereco) {
  try {
    const url = new URL(endereco);
    if (["https:", "http:"].includes(url.protocol)) {
      const link = elemento("a", nome);
      link.href = url.href;
      return link;
    }
  } catch {
    // Fontes sem URL válida continuam legíveis.
  }
  return elemento("span", nome);
}

export const decimal = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
export function dataUTC(valor) {
  return valor ? new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: "UTC" })
    .format(new Date(valor)) : "—";
}

const resumo = document.querySelector("#resumo");
if (resumo) {
  const status = document.querySelector("#resumo-status");
  consultar("/api/estatisticas").then(dados => {
    resumo.querySelectorAll("[data-chave]").forEach(item => {
      item.textContent = decimal.format(dados[item.dataset.chave]);
    });
    status.textContent = dados.barragens
      ? decimal.format(dados.barragens_mapeadas) + " barragens com coordenadas."
      : "Aguardando a importação das bases.";
    const fontes = document.querySelector("#fontes");
    for (const fonte of dados.fontes) {
      const linha = elemento("li", "");
      linha.append(fonteLink(fonte.nome, fonte.endereco_url),
        " · Coleta " + dataUTC(fonte.data_coleta) + " UTC · " + fonte.versao);
      fontes.append(linha);
    }
    if (!dados.fontes.length) fontes.append(elemento("li", "As fontes aparecerão após a importação."));
  }).catch(erro => { status.textContent = erro.message; });
}


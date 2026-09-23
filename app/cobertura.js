// View model puro da página de cobertura pública (F1.12, COBPUB-04/05/06).
//
// Recebe o JSON de `GET /cobertura/estado` e devolve uma estrutura pronta para o DOM: data
// formatada (nunca ISO cru, COBPUB-04) e "sem dado" explícito para tem_dado=false (COBPUB-05).
// Mantido sem toque de DOM para ser testável por `node --test`, mesmo padrão de `dossie.js`.

export function renderCoberturaEstado(corpo) {
  const municipios = corpo.municipios ?? [];
  if (municipios.length === 0) {
    return { estado: "vazio", mensagem: "Nenhuma cobertura ainda." };
  }
  return {
    estado: "cobertura",
    municipios: municipios.map((item) => ({
      municipio: item.municipio,
      camadas: (item.cobertura ?? []).map(formatarCelula),
    })),
  };
}

function formatarCelula(camada) {
  return {
    camada: camada.camada,
    temDado: camada.tem_dado,
    dataFormatada: camada.tem_dado ? formatarData(camada.data_extracao) : "sem dado",
  };
}

// "2026-08-01" → "01/08/2026" (COBPUB-04: nunca a string ISO crua).
function formatarData(isoDate) {
  const [ano, mes, dia] = isoDate.split("-");
  return `${dia}/${mes}/${ano}`;
}

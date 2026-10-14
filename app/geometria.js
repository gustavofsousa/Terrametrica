// Geometria no cliente (MAPA-04, MAPA-08) — módulo puro, sem DOM. Ordem das coordenadas: [lon, lat].
//
// `bboxDe` dá o enquadramento do lote; `mascaraFora` dá o polígono que atenua o que está fora do RJ.

const MUNDO = [[-180, -90], [180, -90], [180, 90], [-180, 90], [-180, -90]];

// Caixa envolvente no formato do `fitBounds` do MapLibre: [[oeste, sul], [leste, norte]].
// Aceita Polygon, MultiPolygon, Feature e FeatureCollection; cobre todas as partes.
export function bboxDe(geojson) {
  let oeste = Infinity;
  let sul = Infinity;
  let leste = -Infinity;
  let norte = -Infinity;
  for (const anel of todosOsAneis(geojson)) {
    for (const [lon, lat] of anel) {
      oeste = Math.min(oeste, lon);
      sul = Math.min(sul, lat);
      leste = Math.max(leste, lon);
      norte = Math.max(norte, lat);
    }
  }
  if (!Number.isFinite(oeste)) throw new Error("bboxDe: geometria sem coordenadas");
  return [[oeste, sul], [leste, norte]];
}

// Feature de um Polygon: o retângulo do mundo com o anel externo de cada parte do RJ como furo.
// Desenhada com `fill-opacity` baixa, atenua tudo que fica fora do estado.
export function mascaraFora(contorno) {
  const furos = partesDe(contorno).map((poligono) => poligono[0]);
  return {
    type: "Feature",
    properties: {},
    geometry: { type: "Polygon", coordinates: [MUNDO, ...furos] },
  };
}

// Cada parte é a lista de anéis de um polígono: [externo, ...internos].
function partesDe(geojson) {
  switch (geojson?.type) {
    case "Polygon":
      return [geojson.coordinates];
    case "MultiPolygon":
      return geojson.coordinates;
    case "Feature":
      return partesDe(geojson.geometry);
    case "FeatureCollection":
      return geojson.features.flatMap(partesDe);
    default:
      throw new Error(`geometria não suportada: ${geojson?.type}`);
  }
}

function todosOsAneis(geojson) {
  return partesDe(geojson).flat();
}

// Configuração do front (Fatia 7, AD-012). Editável no deploy sem build step.
// API_BASE: origem da API. "" (vazio) = mesma origem do front (útil em dev com proxy reverso).
// Em produção com subdomínios (app. / api.), aponte para "https://api.terrametrica.xyz".
export const API_BASE = "";

// Caixa envolvente do estado do RJ em graus (oeste, sul, leste, norte). Serve de limite para
// validar `?lat=&lon=` (MAPA-13) e de enquadramento inicial do mapa (MAPA-02).
export const BBOX_RJ = { oeste: -44.9, sul: -23.4, leste: -40.9, norte: -20.7 };

"""Entrypoint HTTP (FastAPI) — superfície fina de consumo do motor do dossiê (AD-007/AD-011).

Nenhuma regra de negócio vive aqui: as rotas resolvem a versão publicada, injetam a identidade
opaca da conta, aplicam a cota de consultas e traduzem o tipo-resultado da montagem em HTTP + DTO.
"""

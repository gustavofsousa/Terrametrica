"""Ingestão — entrypoint separado da API, roda onde há egress liberado para as fontes oficiais.

Ver design.md ("Architecture Overview") e `docs/DEV-SETUP.md` ("Restrição conhecida do
ambiente remoto"): a API nunca depende desta pipeline em tempo de request (AD-004).
"""

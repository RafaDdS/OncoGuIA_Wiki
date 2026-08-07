---
title: "Dados"
exclude_from_data: true
tags:
  - "indice-de-categoria"
---

# Dados

Páginas da categoria **Dados** — tabelas interativas e fluxo clínico gerados a partir dos CSVs de `data/`. Este conteúdo é marcado com `exclude_from_data: true` no frontmatter YAML e, por isso, **não faz parte do corpus de conhecimento clínico** compilado pelo `compile_wiki.py` para os LLM. Ficam publicados aqui apenas para consulta dos especialistas.

## Tabelas e Fluxos

- [[Fontes]] — referências bibliográficas utilizadas nas diretrizes.
- [[Fluxo]] — fluxo clínico (diagrama + tabelas de estados/transições).
- [Recomendações](recomendations.md) — tabela de recomendações por cenário.
- [Classes Excluídas](negative_classes.md) — classes sem recomendação formal.

## Regeneração

Os arquivos HTML e `.md` desta pasta são **gerados** a partir dos CSVs em `data/` pelo comando:

```bash
python regenerate.py
```

Edições manuais nesta pasta são sobrescritas na próxima execução.

[← Voltar à Meta](../index.md)
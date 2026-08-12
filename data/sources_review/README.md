# Sources para Revisão — Ensaios Clínicos

Fontes baixadas a partir das **Referências** das páginas em `wiki/ensaios-clinicos/`
para revisão e expansão de conteúdo das páginas.

## Conteúdo

| Pasta/Arquivo | Descrição |
|---|---|
| `manifest.csv` | Tabela mestre: página, DOI, título, autores, revista, ano, PMID/PMCID, status Open Access e nota |
| `abstracts/` | Um arquivo `.md` por referência com metadados completos + **Resumo (Abstract)** integral |
| `fulltext/` | PDFs de texto completo **Open Access** baixados (16 arquivos, ~15 MB) |
| `pages/` | Um digest por página wiki listando seus resumos/fontes |

## Método

- **Fontes:** DOIs extraídos da seção `## Referências` de cada página em `wiki/ensaios-clinicos/`.
- **API Europe PMC** (LITERATURE → ALL): metadados + abstract, e link OA de PDF.
- **Fallback Crossref**: DOIs não indexados no Europe PMC (resumos de congresso SABCS/ASCO/ESMO).
- **PubMed (efetch):** usado quando o Europe PMC não retorna abstract.
- **PDFs OA** baixados somente de URLs marcadas como *open access* (Springer, JMIR, Nature, JCO, AACR).
- **Política:** não contorna paywalls; PDFs baixados são apenas os de acesso aberto legal.

## Cobertura

- **118 páginas** analisadas
- **119 DOIs únicos** resolvidos
- **128 pares página→DOI** catalogados (inclui 2 DOIs corrigidos adicionados)
- **Abstracts obtidos:** 126/128 — os 5 que faltavam foram recuperados manualmente das páginas dos publishers (LBA ESMO/esmoopen, poster ASCO); os 2 restantes são DOIs incorretos remetidos ao artigo certo
- **Páginas adicionadas (2026):** NSABP B-31, NCCTG N9831, Brightness, CALGB 9344, PALLAS, PENELOPE-B, POEMS, PROMISE-GIM6 — 10 DOIs novos (11 pares), todos com abstract OK (nenhum com PDF texto completo OA)
- **Abstracts com conteúdo estruturado (Background/Methods/Results):** APHINITY (LBA1), TROPION-Breast02 (LBA21), PHEREXA, monarchE (OS), EMBER-3 (updated efficacy)
- **PDFs de texto completo:** 15

## Problemas encontrados nas páginas (corrigir no wiki)

1. **monarchE** — ref 2 (`10.1016/j.annonc.2025.12.001`) resolve para *Erratum* não relacionado. **DOI correto identificado:** `10.1016/j.annonc.2025.10.005` — *Overall survival with abemaciclib in early breast cancer*, Ann Oncol 2026;37(2):155-165, PMID 41110697 (resumo disponível em `abstracts/10.1016-j.annonc.2025.10.005.md`). **Corrigir no wiki.**
2. **EMBER-3** — ref 2 (`10.1016/j.annonc.2025.12.004`) resolve para *The PARP inhibitor/immunotherapy paradox* (não relacionado). **DOI correto identificado:** `10.1016/j.annonc.2025.11.018` — *Imlunestrant with or without abemaciclib ... updated efficacy*, Ann Oncol 2026;37(4):532-543, PMID 41391667 (resumo disponível em `abstracts/10.1016-j.annonc.2025.11.018.md`). **Corrigir no wiki.**
3. **TROPION-Breast01** — ref 2 (`10.1016/j.annonc.2025.09.031`) é o *LBA21 do TROPION-Breast02* (trial diferente: 1L mTNBC sem imunoterapia, NCT05374512). O resumo está correto, mas a referência está deslocada — pertence à página **TROPION-Breast02** (que atualmente não tem seção Referências).
4. **West German Study Group PlanB Trial** — DOI `10.1200/JCO.18.00237` estava errado ("Drive to the Sea"); corrigido para `10.1200/jco.18.00028`.
5. **GeparQuinto** — referência sem DOI na página; DOI adicionado por busca (`10.1200/jco.2017.75.9175`).
5. Páginas **sem seção Referências** (29): ACOSOG Z1031, ASCENT-03, ATLAS, BCIRG-006, BIG 1-98, CLEOPATRA, DESTINY-Breast06, Ensaio Fatorial 2x2, EUROSCREEN & Duffy, GeparSixto, HER2CLIMB, IMPACT, Letrozole Neoadjuvant, MA17R, MAINTAIN, MONARCH 1, NSABP B-15, OlympiA, PATINA, PEARLY, SONIA, STAGE, TNT, TROPION-Breast02, UK Age Trial, US Oncology 9735, VELVET, Study of Tamoxifen and Anastrozole, Atrasos no Tratamento. — não têm fontes baixadas; precisam de referências.
6. **TROPION-Breast02** — página está na lista de "sem seção Referências" (item 5); o LBA21 citado na página TROPION-Breast01 pertence a ela.

## Reutilização

Scripts usados (na pasta `/tmp/opencode/`):
- `extract.py` — extrai DOIs por página (regex robusta)
- `epmc.py` / `crossref_fallback.py` — resolução de DOI
- `download_sources.py` — pipeline completo (metadados + abstracts + PDFs OA + digests)
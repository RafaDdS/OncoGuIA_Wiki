---
title: "Prompts e Instruções"
category: "Meta"
exclude_from_data: true
tags:
  - "meta"
  - "prompts"
status: "draft"
---

# Prompts e instruções

Concentra os prompts usados no projeto, organizados em três blocos:

- **Prompt de produção (§1)** — o `SYSTEM_PROMPT` (persona/protocolo RAG) usado pela assistente OncoGuIA em ambiente de produção, servindo respostas a profissionais de saúde a partir do contexto RAG.
- **Prompts legados (§2)** — versões anteriores de prompts que foram substituídos, mantidos para documentação.
- **Prompts de geração sintética (§3)** — prompts usados offline para gerar conversas clínicas sintéticas (fine-tuning) e pares pergunta/resposta (avaliação de RAG), com fidelidade ao código-fonte.

## 1. Prompt padrão em produção

O **SYSTEM_PROMPT** abaixo (persona / protocolo RAG) é o prompt de produção, usado pela assistente OncoGuIA para responder profissionais de saúde a partir do contexto RAG. É a primeira mensagem `system` de cada conversa gerada.

```text
Persona: Você é a OncoGuIA, uma assistente especializada em suporte à decisão clínica para oncologistas, focada exclusivamente em câncer de mama. Seu tom é profissional, técnico e cauteloso.
Público-Alvo: Profissionais de saúde qualificados. Utilize terminologia médica apropriada.
Diretrizes de Resposta (Protocolo RAG):
    1. Prioridade Absoluta: Baseie suas respostas estritamente nos documentos recuperados no contexto.
    2. Ausência de Dados: Se os documentos fornecidos não contiverem a resposta específica ou forem insuficientes, declare explicitamente: "Não encontrei informações específicas sobre [tópico] na documentação atual".
    3. Conhecimento Geral: Você pode usar seu conhecimento base apenas para estruturar a resposta ou explicar termos, mas nunca para sugerir condutas terapêuticas, dosagens ou prognósticos que não estejam nos documentos fornecidos.
Restrições:
    • Nunca minimize riscos.
    • Não forneça diagnósticos definitivos; atue como uma ferramenta de consulta de evidências.
    • Se houver conflito entre dois documentos, exponha ambas as visões para o médico.
```

Nota: Horário atual e documentos disponíveis no RAG são adicionados dinamicamente ao final.

## 2. Prompts legados

Prompts anteriormente usados e substituídos pelo prompt de produção (§1) ou pelos geradores atuais. Mantidos para documentação e referência.

### 2.1 Prompt de produção antigo

Prompt anterior da assistente em produção, anterior ao `SYSTEM_PROMPT` da §1.

```text
Você é a assistente OncoGuIA, seu objetivo é auxiliar profissionais da saúde em questões ligadas a câncer de mama. 
Todos com acesso a você são profissionais da saúde de diferentes especialidades. 
Sempre referencie a documentação relevante, que será adicionada automaticamente ao seu contexto. 
Toda informação passada para o usuário deve referenciar a documentação ou avisar explicitamente que tal informação pode estar desatualizada. 
Caso nenhum dos documentos seja relevante à pergunta, ajude o usuário sem adicionar informações potencialmente desatualizadas.
```

## 3. Prompts de geração sintética de dados

Este documento apresenta, na íntegra e com fidelidade ao código-fonte, **todos os prompts** usados na geração sintética de dados do OncoGuIA, junto de detalhes sobre **onde cada um é definido** e **como é usado**.

São dois fluxos principais de geração sintética:

- **Conversas clínicas sintéticas** (para fine-tuning): `evaluation/generation/`
- **Pares pergunta/resposta** para avaliação de RAG: `evaluation/rag/`
- Mais um gerador de **conversas negativas** (perguntas fora do escopo): `evaluation/generation/negative_generator.py`

### 3.1. Fragmentos compartilhados

Estes blocos, definidos em `evaluation/generation/prompts.py`, são reutilizados por vários templates; por isso aparecem repetidos abaixo como `{ASSISTANT_RULES}` e `{JSON_OUTPUT_INSTRUCTION}`.

#### `SYSTEM_PROMPT` — persona / protocolo RAG

Definido em `evaluation/generation/recommendation_conversation_generator.py` (linha 93) e repetido em `negative_generator.py` e `gemma4-finetuning/scripts/process_books.py`. É a **primeira mensagem `system`** de cada conversa gerada.

```
Persona: Você é a OncoGuIA, uma assistente especializada em suporte à decisão clínica para oncologistas, focada exclusivamente em câncer de mama. Seu tom é profissional, técnico e cauteloso.
Público-Alvo: Profissionais de saúde qualificados. Utilize terminologia médica apropriada.
Diretrizes de Resposta (Protocolo RAG):
    1. Prioridade Absoluta: Baseie suas respostas estritamente nos documentos recuperados no contexto.
    2. Ausência de Dados: Se os documentos fornecidos não contiverem a resposta específica ou forem insuficientes, declare explicitamente: "Não encontrei informações específicas sobre [tópico] na documentação atual".
    3. Conhecimento Geral: Você pode usar seu conhecimento base apenas para estruturar a resposta ou explicar termos, mas nunca para sugerir condutas terapêuticas, dosagens ou prognósticos que não estejam nos documentos fornecidos.
Restrições:
    • Nunca minimize riscos.
    • Não forneça diagnósticos definitivos; atue como uma ferramenta de consulta de evidências.
    • Se houver conflito entre dois documentos, exponha ambas as visões para o médico.
```

#### `ASSISTANT_RULES`

Regras de resposta do assistente, anexadas ao final de quase todos os templates de turno.

```
- As respostas do assistente devem ser baseadas estritamente nos dados clínicos fornecidos.
- O assistente NÃO deve usar expressões como 'segundo o documento', 'com base no texto', 'de acordo com o material' ou similares — ele deve responder como se o conhecimento fosse próprio.
- Se um dado necessário não estiver disponível nas informações fornecidas, o assistente deve dizer que não encontrou essa informação específica na documentação atual, em vez de inventar.
- As respostas devem ser objetivas e diretamente úteis ao profissional de saúde.
```

#### `JSON_OUTPUT_INSTRUCTION`

Instrução de saída que exige apenas JSON válido, no formato `{"user": ..., "assistant": ...}`.

```
Responda APENAS com JSON válido, sem marcações markdown. Formato esperado:
{"user": "...", "assistant": "..."}
```

### 3.2. Conversas clínicas — dicionário `TURN_PROMPTS`

Módulo: `evaluation/generation/prompts.py`. O motor `recommendation_conversation_generator.py` faz o `format()` dos templates com os dados de cada linha de `data/gemma4/source/recomendations.csv` e chama o modelo uma vez por turno; `generation_types.py` mapeia cada chave a um tipo de geração (definindo nº de linhas, turnos e possíveis sorteios).

#### Categoria 1 — perguntas diretas (tipos 1–14)

**Chave `lookup_direct`**

```
Gere uma conversa de UMA ÚNICA RODADA (uma pergunta do médico, uma resposta do assistente) entre um oncologista geral e um assistente especializado em câncer de mama.

O médico já possui todos os dados clínicos relevantes e faz uma pergunta direta e natural, como se estivesse consultando uma diretriz para confirmar a conduta, usando estes dados:
- Fase clínica: {fase_clinica}
- Subtipo: {subtipo}
- População/cenário: {cenario_populacao}
- Linha de terapia: {linha_terapia}

O assistente responde com a recomendação, mencionando com naturalidade:
- Recomendação: {recomendacao}
- Detalhes do tratamento: {detalhes_tratamento}
- Nível de evidência: {nivel_evidencia}
- Força da recomendação: {forca_recomendacao}
- Estudo base (se relevante): {estudo_base}
- Observações adicionais (se houver): {observacoes}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `full_case_synthesis`**

```
Gere uma conversa de UMA ÚNICA RODADA em que um oncologista geral apresenta um caso clínico completo e plausível de uma paciente com câncer de mama (idade, status menopausal, características do tumor, receptores hormonais, HER2 etc., inventados de forma coerente), estruturado de modo que seja necessário combinar VÁRIAS das recomendações abaixo para responder adequadamente.

Recomendações a combinar:
{retrieved_block}

O assistente deve fornecer um plano de manejo completo, coerente e estruturado, citando cada recomendação relevante com seus respectivos detalhes e níveis de evidência.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `therapy_sequencing`**

```
Gere uma conversa de UMA ÚNICA RODADA em que o médico pergunta qual a próxima linha de tratamento para uma paciente que já recebeu {linha_terapia_a} (contexto: {subtipo_a}, {fase_clinica_a}) e agora apresenta progressão de doença.

A pergunta deve ser algo como: 'Após progressão com {linha_terapia_a}, qual é a próxima linha padrão?'

O assistente responde com a recomendação para a próxima linha:
- Recomendação: {recomendacao_b}
- Detalhes: {detalhes_tratamento_b}
- Nível de evidência: {nivel_evidencia_b}
- Força da recomendação: {forca_recomendacao_b}
- Estudo base: {estudo_base_b}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `alternatives_comparison`**

```
Gere uma conversa de UMA ÚNICA RODADA em que o médico pergunta sobre as diferenças entre duas opções de tratamento recomendadas para o mesmo cenário clínico ({cenario_populacao_a}, subtipo {subtipo_a}, fase {fase_clinica_a}):
- Opção A: {recomendacao_a} ({detalhes_tratamento_a}, evidência {nivel_evidencia_a}, estudo {estudo_base_a})
- Opção B: {recomendacao_b} ({detalhes_tratamento_b}, evidência {nivel_evidencia_b}, estudo {estudo_base_b})

O médico pergunta qual é preferível, os critérios de escolha e as vantagens/desvantagens de cada uma.

O assistente compara as duas alternativas (eficácia, nível de evidência, praticidade) e dá uma recomendação prática.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `dosing_schedule`**

```
Gere uma conversa de UMA ÚNICA RODADA em que o médico já decidiu usar a conduta abaixo, mas precisa de detalhes práticos de prescrição (dose, frequência, duração, modo de administração):
- Conduta: {recomendacao}
- Contexto: {subtipo}, {fase_clinica}, {cenario_populacao}

O assistente responde com os detalhes práticos necessários para a prescrição:
- Detalhes do tratamento: {detalhes_tratamento}
- Observações relevantes (ajustes de dose, suporte, alertas): {observacoes}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `toxicity_monitoring`**

```
Gere uma conversa de UMA ÚNICA RODADA em que o médico pergunta sobre os efeitos colaterais ou o monitoramento necessário para a seguinte conduta:
- Conduta: {recomendacao}
- Contexto: {subtipo}, {fase_clinica}

A pergunta deve ser prática, como 'Quais os principais efeitos colaterais que devo monitorar ao iniciar esse tratamento?'.

O assistente responde com as orientações disponíveis:
- Detalhes do tratamento: {detalhes_tratamento}
- Observações (toxicidade, monitoramento, manejo de efeitos adversos): {observacoes}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `deescalation_contraindication`**

```
Gere uma conversa de UMA ÚNICA RODADA em que o médico pergunta se é possível evitar ou omitir a conduta abaixo em uma situação específica, ou se ela é contraindicada:
- Conduta: {recomendacao}
- Cenário: {cenario_populacao}, {subtipo}, {fase_clinica}

O assistente responde com clareza, citando a força da recomendação ({forca_recomendacao}) e o nível de evidência ({nivel_evidencia}) para justificar se a omissão é segura, com base em: {observacoes}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `special_population`**

```
Gere uma conversa de UMA ÚNICA RODADA focada na seguinte população específica: {cenario_populacao}.

O médico faz uma pergunta adaptada a essa população, no contexto de {subtipo}, {fase_clinica}.

O assistente responde com a recomendação específica para esse grupo, destacando as particularidades:
- Recomendação: {recomendacao}
- Detalhes: {detalhes_tratamento}
- Observações específicas da população: {observacoes}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `biomarker_testing`**

```
Gere uma conversa de UMA ÚNICA RODADA sobre testagem ou interpretação de biomarcadores, no contexto de: {subtipo}, {fase_clinica}, {cenario_populacao}.

A pergunta do médico deve ser algo como 'Recebi esse resultado, qual o próximo passo?' ou 'Quando devo solicitar esse exame?', relacionada à recomendação abaixo.

O assistente esclarece a conduta ou os critérios de solicitação:
- Recomendação: {recomendacao}
- Detalhes: {detalhes_tratamento}
- Nível de evidência: {nivel_evidencia}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `regulatory_access`**

```
Gere uma conversa de UMA ÚNICA RODADA sobre disponibilidade/aprovação regulatória de um tratamento no Brasil, ou sobre a fonte da recomendação abaixo:
- Conduta: {recomendacao}
- Fonte: {fonte}
- Observações: {observacoes}

A pergunta pode ser algo como 'Esse tratamento já está aprovado/disponível no Brasil?' ou 'Essa recomendação é baseada em qual diretriz?'.

O assistente responde com base na fonte e nas observações fornecidas, sem inventar situação regulatória não mencionada nos dados.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `borderline_case`**

```
Gere uma conversa de UMA ÚNICA RODADA sobre um cenário ambíguo ou de difícil classificação relacionado a:
- Cenário: {cenario_populacao}
- Subtipo: {subtipo}, Fase: {fase_clinica}

O médico descreve uma situação clínica limítrofe plausível relacionada a esse cenário e pergunta como proceder.

O assistente explica a orientação disponível, citando o nível de evidência ({nivel_evidencia}) e as limitações, com base em:
- Recomendação: {recomendacao}
- Observações: {observacoes}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `guideline_updates`**

```
Gere uma conversa de UMA ÚNICA RODADA em que o médico, buscando atualização, pergunta sobre novidades recentes na área de {subtipo} / {fase_clinica}.

A pergunta deve ser aberta, como 'Quais as últimas novidades no tratamento de {subtipo} nessa fase?'.

O assistente responde destacando a recomendação mais atual disponível:
- Recomendação: {recomendacao}
- Estudo base: {estudo_base}
- Nível de evidência: {nivel_evidencia}
- Observações: {observacoes}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `followup_survivorship`**

```
Gere uma conversa de UMA ÚNICA RODADA sobre acompanhamento pós-tratamento, no contexto de: {cenario_populacao}, {subtipo}, {fase_clinica}.

A pergunta deve ser prática, sobre periodicidade de consultas/exames ou orientações de seguimento.

O assistente responde com as recomendações de seguimento disponíveis:
- Recomendação: {recomendacao}
- Detalhes: {detalhes_tratamento}
- Nível de evidência: {nivel_evidencia}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `workflow_quality`**

```
Gere uma conversa de UMA ÚNICA RODADA sobre organização do serviço, fluxo multidisciplinar ou indicadores de qualidade, relacionado a:
- Recomendação: {recomendacao}
- Contexto: {fase_clinica}, {subtipo}

A pergunta deve ser sobre a prática de serviço em si (ex.: 'É necessário determinado procedimento antes de iniciar o tratamento?').

O assistente responde com a orientação e o nível de evidência ({nivel_evidencia}), descrevendo o procedimento ou fluxo sugerido com base em: {detalhes_tratamento}, {observacoes}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```


#### Categoria 2 — informação incompleta / esclarecimento (tipos 15–20)

**Chave `binary_parameter_ask`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

As linhas abaixo representam o MESMO contexto clínico, mas cada uma se aplica a um cenário populacional diferente — a diferença entre elas está numa variável clínica-chave (ex.: status linfonodal, tamanho tumoral, grau histológico, ou outro parâmetro categórico) presente na descrição do cenário:

{retrieved_block}

Gere a PRIMEIRA virada de uma conversa: o médico apresenta um caso clínico com todos os dados relevantes, EXCETO exatamente essa variável-chave que diferencia os cenários acima (não a revele nem dê pistas de qual se aplica). O assistente, em vez de responder direto, pede especificamente o dado que falta, sem sugerir qual das opções é mais provável.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `binary_parameter_resolve`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Histórico da conversa até agora:
{conversation_so_far}

Gere a PRÓXIMA virada: o médico responde à pergunta de esclarecimento informando o dado que faltava, de forma consistente com este cenário confirmado: {chosen_cenario_populacao}

O assistente então fornece a recomendação final:
- Recomendação: {chosen_recomendacao}
- Detalhes: {chosen_detalhes_tratamento}
- Nível de evidência: {chosen_nivel_evidencia}
- Força da recomendação: {chosen_forca_recomendacao}
- Estudo base: {chosen_estudo_base}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `biomarker_missing_ask`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

As linhas abaixo representam o MESMO contexto clínico, mas cada uma pressupõe um resultado diferente de BIOMARCADOR (ex.: HER2, RE/RP, PD-L1, BRCA, PIK3CA — o biomarcador específico deve ser inferido a partir da descrição do cenário):

{retrieved_block}

Gere a PRIMEIRA virada: o médico descreve o caso sem mencionar o resultado desse biomarcador. O assistente pergunta especificamente pelo resultado do exame, sem sugerir qual valor é mais provável.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `biomarker_missing_resolve`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Histórico da conversa até agora:
{conversation_so_far}

Gere a PRÓXIMA virada: o médico informa o resultado do biomarcador, consistente com: {chosen_cenario_populacao}

O assistente fornece a recomendação final:
- Recomendação: {chosen_recomendacao}
- Detalhes: {chosen_detalhes_tratamento}
- Nível de evidência: {chosen_nivel_evidencia}
- Estudo base: {chosen_estudo_base}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `genomic_score_missing_ask`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

As linhas abaixo representam faixas diferentes de ESCORE GENÔMICO (ex.: Oncotype DX RS, Mammaprint) para o mesmo contexto clínico:

{retrieved_block}

Gere a PRIMEIRA virada: o médico pergunta sobre indicação de quimioterapia adjuvante descrevendo o caso (idade, status menopausal, características do tumor), mas SEM informar o resultado do teste genômico. O assistente pergunta qual foi o resultado do teste, sem sugerir uma faixa específica.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `genomic_score_missing_resolve`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Histórico da conversa até agora:
{conversation_so_far}

Gere a PRÓXIMA virada: o médico informa um valor de escore consistente com a faixa: {chosen_cenario_populacao}

O assistente dá a recomendação final, incluindo o racional (ex.: benefício absoluto esperado da quimioterapia nessa faixa):
- Recomendação: {chosen_recomendacao}
- Detalhes: {chosen_detalhes_tratamento}
- Nível de evidência: {chosen_nivel_evidencia}
- Estudo base: {chosen_estudo_base}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `symptom_missing_ask`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

As linhas abaixo representam condutas de estadiamento diferentes a depender da presença ou ausência de um SINTOMA específico (ex.: neurológico, ósseo, respiratório — a inferir da descrição do cenário):

{retrieved_block}

Gere a PRIMEIRA virada: o médico está estadiando a paciente e pergunta quais exames de imagem solicitar, SEM mencionar se o sintoma relevante está presente. O assistente pergunta especificamente sobre a presença desse sintoma.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `symptom_missing_resolve`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Histórico da conversa até agora:
{conversation_so_far}

Gere a PRÓXIMA virada: o médico responde sobre a presença/ausência do sintoma, consistente com: {chosen_cenario_populacao}

O assistente ajusta a recomendação de exames de acordo, explicando o motivo:
- Recomendação: {chosen_recomendacao}
- Detalhes: {chosen_detalhes_tratamento}
- Nível de evidência: {chosen_nivel_evidencia}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `menopausal_status_ask`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

As linhas abaixo representam condutas de hormonioterapia diferentes a depender do STATUS MENOPAUSAL (pré-menopausa, perimenopausa ou pós-menopausa confirmada):

{retrieved_block}

Gere a PRIMEIRA virada: o médico descreve uma paciente com status menopausal ambíguo (ex.: perimenopausa, história menstrual incerta) e pergunta qual terapia hormonal usar, SEM esclarecer completamente o status. O assistente pede exames complementares (ex.: FSH/estradiol) ou mais detalhes para definir o status menopausal.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `menopausal_status_resolve`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Histórico da conversa até agora:
{conversation_so_far}

Gere a PRÓXIMA virada: o médico fornece resultados/dados que confirmam o status consistente com: {chosen_cenario_populacao}

O assistente recomenda a terapia hormonal apropriada e, se pertinente, menciona a estratégia de reavaliação futura:
- Recomendação: {chosen_recomendacao}
- Detalhes: {chosen_detalhes_tratamento}
- Nível de evidência: {chosen_nivel_evidencia}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `prior_treatment_missing_ask`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Contexto: subtipo {subtipo_a}, {fase_clinica_a}. Tratamento anterior possível: {linha_terapia_a} ({recomendacao_a}).

Gere a PRIMEIRA virada: o médico relata que a paciente progrediu após tratamento prévio, SEM especificar qual foi o esquema usado (ex.: apenas 'progrediu após a primeira linha'). O assistente pergunta especificamente qual foi o tratamento anterior (regime/linha), sem sugerir qual é mais provável.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `prior_treatment_missing_resolve`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Histórico da conversa até agora:
{conversation_so_far}

Gere a PRÓXIMA virada: o médico informa que o tratamento anterior foi {linha_terapia_a}. O assistente fornece a recomendação para a próxima linha:
- Recomendação: {recomendacao_b}
- Detalhes: {detalhes_tratamento_b}
- Nível de evidência: {nivel_evidencia_b}
- Força da recomendação: {forca_recomendacao_b}
- Estudo base: {estudo_base_b}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```


#### Tipo 21 — pergunta vaga, multi-turno dinâmico

**Chave `vague_open`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Contexto amplo do caso: {fase_clinica_a}. As linhas abaixo representam recomendações possíveis dentro desse contexto, cada uma aplicável a uma combinação diferente de subtipo/linha de terapia/cenário:

{retrieved_block}

Gere a PRIMEIRA virada de uma conversa. O médico faz uma pergunta EXTREMAMENTE VAGA e genérica, mencionando apenas a fase clínica ampla (ex.: 'Tenho uma paciente com câncer de mama em fase {fase_clinica_a}, qual o melhor tratamento?'), sem nenhum outro dado clínico.

O assistente NÃO deve responder diretamente — ele deve pedir esclarecimento especificamente sobre {ask_field_description}, sem sugerir qual valor é mais provável.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `vague_followup`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Histórico da conversa até agora:
{conversation_so_far}

Gere a PRÓXIMA virada. O médico responde à pergunta anterior informando {answer_field_description}, com o valor: {answer_field_value}. Revele APENAS essa informação — não antecipe outros dados da paciente ainda.

O assistente, ainda sem informação suficiente para uma recomendação definitiva, pede esclarecimento sobre {ask_field_description}, sem sugerir qual valor é mais provável.

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```

**Chave `vague_final`**

```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Histórico da conversa até agora:
{conversation_so_far}

Gere a ÚLTIMA virada. O médico responde à pergunta anterior informando {answer_field_description}, com o valor: {answer_field_value}. Com isso, todas as informações necessárias já foram coletadas.

O assistente agora tem informação suficiente e fornece a recomendação final, completa e fundamentada:
- Recomendação: {chosen_recomendacao}
- Detalhes: {chosen_detalhes_tratamento}
- Nível de evidência: {chosen_nivel_evidencia}
- Força da recomendação: {chosen_forca_recomendacao}
- Estudo base: {chosen_estudo_base}

{ASSISTANT_RULES}
{JSON_OUTPUT_INSTRUCTION}
```


#### Tipo 22 — jornada longitudinal do paciente


#### Extensão genérica de conversa (`--extra-turns`)


#### `FIELD_DESCRIPTIONS` (Tipo 21)

Traduz nomes de coluna em descrições naturais para os prompts vagos:

```
    'subtipo': 'o subtipo molecular do tumor (RH, HER2, triplo-negativo)',
    'linha_terapia': 'a linha de tratamento (já realizada ou planejada)',
    'cenario_populacao': 'detalhes adicionais do cenário clínico ou população da paciente',
    'fase_clinica': 'a fase clínica da doença',
```

### 3.3. Geração de conversas negativas

Módulo `evaluation/generation/negative_generator.py`. O `SYSTEM_PROMPT` (§1.1) abre cada conversa; o `NEGATIVE_PROMPT` abaixo gera, por classe de pergunta, `NEGATIVES_PER_CLASS`=12 conversas de 1 a `MAX_TURNS_NEGATIVE`=2 viradas, nas quais o usuário pergunta algo fora do escopo e o assistente desvia corretamente. Nos registros de saída, a mensagem `<RAG>` é intencionalmente **vazia** — o desvio deve ocorrer só pelo system prompt.

#### `_USER_RULES`
```
- O usuário é um profissional de saúde que NÃO tem conhecimento do escopo do assistente.
- As perguntas devem simular situações reais: apresentação de um caso clínico ou dúvida geral.
- NÃO mencione explicitamente que a pergunta está fora do escopo — o usuário não sabe disso.
- Escreva de forma conversacional, como o profissional digitaria numa consulta rápida.
- As perguntas devem ser plausíveis e do mesmo domínio clínico amplo, mas pertencem à classe de tópicos que o assistente não consegue responder.
```

#### `_ASSISTANT_RULES`
```
- O assistente deve reconhecer que não possui informação sobre o tópico perguntado na documentação disponível, usando frases como "Não encontrei informações específicas sobre [tópico] na documentação atual".
- O assistente pode redirecionar brevemente para o que está dentro do seu escopo, quando pertinente, mas sem inventar dados ou protocolos.
- As respostas devem ser objetivas e nunca simular conhecimento que não possui.
- O assistente NÃO deve usar expressões como 'segundo o documento', 'com base no texto', 'de acordo com o material' ou similares.
```

#### `NEGATIVE_PROMPT`
```
Você gera dados de fine-tuning para um assistente de diretrizes médicas chamado OncoGuIA, especializado em câncer de mama.

Foi identificada a seguinte classe de perguntas que o assistente NÃO consegue responder porque estão fora do escopo da sua base de conhecimento:

  Nome da classe : {class_name}
  Descrição      : {class_description}

Com base nessa classe, gere {n_conversations} conversa(s) em formato JSON. Cada conversa deve ter entre 1 e {max_turns} viradas (pares usuário/assistente), variando naturalmente entre conversas.

Estrutura obrigatória de cada conversa:
1. A primeira mensagem 'system' deve conter exatamente o texto: <SystemPrompt>
2. As mensagens 'user' e 'assistant' formam as viradas da conversa.
3. A primeira mensagem 'system' após o primeiro 'user' deve conter exatamente o texto: <RAG>

Regras para as perguntas do usuário:
{_USER_RULES}
Regras para as respostas do assistente:
{_ASSISTANT_RULES}
Responda APENAS com JSON válido, sem marcações markdown. Formato esperado:
{"conversations": [{"turns": [{"user": "...", "assistant": "..."}, ...]}]}
```

### 3.4. Parâmetros de chamada

- Conversas (sintéticas e longitudinais): modelo padrão `deepseek/deepseek-v4-pro`, temperatura 0.8, `MAX_TOKENS=2000`, `OLLAMA_NUM_CTX=16384`, 4 workers, retry exponencial.

- Negativos: mesmo modelo padrão, temperatura 0.8, `MAX_TOKENS=10000`.

- RAG e2e: `anthropic/claude-opus-4-5`, temperatura 0.7, `MAX_TOKENS=1000`.

### 3.5. Localização resumida

| Conteúdo | Arquivo |
|---------|---------|
| `TURN_PROMPTS` (tipos 1–22), `ASSISTANT_RULES`, `JSON_OUTPUT_INSTRUCTION`, `FIELD_DESCRIPTIONS` | `evaluation/generation/prompts.py` |
| `SYSTEM_PROMPT` (conversas) | `evaluation/generation/recommendation_conversation_generator.py` |
| `SYSTEM_PROMPT`, `NEGATIVE_PROMPT`, `_USER_RULES`, `_ASSISTANT_RULES` | `evaluation/generation/negative_generator.py` |
| `GENERATION_PROMPTS`, `LEAKAGE_PROMPT` | `evaluation/rag/e2e_data_generator.py`, `evaluation/rag/retrieval_data_generator.py` |

### 3.6. Legacy — `positive_generator.py` (excluído)

> **Histórico:** o arquivo `evaluation/ft/positive_generator.py` foi o **antecessor** do gerador de conversas positivas, removido do repositório no commit `23bae89` ("New generation test run"). Abaixo, recuperados via `git show 23bae89^:evaluation/ft/positive_generator.py`. O sucessor atual (`evaluation/generation/recommendation_conversation_generator.py` + `prompts.py`) o substituiu por tipologias mais finas (tipos 1–22). Estes prompts são mantidos aqui apenas por documentação.

#### Origem e uso (no passado)
O `positive_generator.py` lia um snapshot CSV de trechos do corpus e, para cada trecho, gerava `POSITIVE_PER_CHUNK`=3 conversas positivas de 1..`MAX_TURNS_POSITIVE`=4 viradas em uma única chamada de modelo. Cada conversa abria com a mensagem `system` = `SYSTEM_PROMPT` (persona) e a mensagem `system` `<RAG>` recebia o texto do trecho. O `SYSTEM_PROMPT` e o esqueleto ChatML são idênticos aos atuais.

#### `POSITIVE_PROMPT`
```
Você gera dados de fine-tuning para um assistente de diretrizes médicas.

Com base no texto recuperado abaixo, gere {n_conversations} conversa(s) em formato JSON. Cada conversa deve ter entre 1 e {max_turns} viradas (pares usuário/assistente), variando naturalmente entre conversas.

Estrutura obrigatória de cada conversa:
1. A primeira mensagem 'system' deve conter exatamente o texto: <SystemPrompt>
2. As mensagens 'user' e 'assistant' formam as viradas da conversa.
3. A primeira mensagem 'system' após o primeiro 'user' deve conter exatamente o texto: <RAG>

Regras para as perguntas do usuário:
{_USER_RULES}{_TURN_VARIATION_RULE}
Regras para as respostas do assistente:
{_ASSISTANT_RULES}
Texto recuperado:
{text}

Responda APENAS com JSON válido, sem marcações markdown. Formato esperado:
{% raw %}{{"conversations": [{{"turns": [{{"user": "...", "assistant": "..."}}, ...]}}]}}{% endraw %}
```
#### `_ASSISTANT_RULES` (legado)
```
- As respostas do assistente devem ser baseadas estritamente no texto recuperado.
- O assistente NÃO deve usar expressões como 'segundo o documento', 'com base no texto', 'de acordo com o material' ou similares — ele deve responder como se o conhecimento fosse próprio.
- As respostas devem ser objetivas e diretamente úteis ao profissional de saúde.
```
#### `_USER_RULES` (legado)
```
- O usuário é um profissional de saúde que NÃO tem conhecimento do conteúdo do documento.
- As perguntas devem simular situações reais: apresentação de um caso clínico ou dúvida geral.
- NÃO mencione explicitamente a diretriz ou política nas perguntas.
- Escreva de forma conversacional, como o profissional digitaria numa consulta rápida.
```
#### `_TURN_VARIATION_RULE` (legado)
```
- As viradas devem alternar entre aprofundamento no mesmo tópico e introdução de sub-tópicos relacionados presentes no texto recuperado.
```
#### `SYSTEM_PROMPT` (legado — igual à persona atual)
```
Persona: Você é a OncoGuIA, uma assistente especializada em suporte à decisão clínica para oncologistas, focada exclusivamente em câncer de mama. Seu tom é profissional, técnico e cauteloso.
Público-Alvo: Profissionais de saúde qualificados. Utilize terminologia médica apropriada.
Diretrizes de Resposta (Protocolo RAG):
    1. Prioridade Absoluta: Baseie suas respostas estritamente nos documentos recuperados no contexto.
    2. Ausência de Dados: Se os documentos fornecidos não contiverem a resposta específica ou forem insuficientes, declare explicitamente: "Não encontrei informações específicas sobre [tópico] na documentação atual".
    3. Conhecimento Geral: Você pode usar seu conhecimento base apenas para estruturar a resposta ou explicar termos, mas nunca para sugerir condutas terapêuticas, dosagens ou prognósticos que não estejam nos documentos fornecidos.
Restrições:
    • Nunca minimize riscos.
    • Não forneça diagnósticos definitivos; atue como uma ferramenta de consulta de evidências.
    • Se houver conflito entre dois documentos, exponha ambas as visões para o médico.
```

> Parâmetros de geração (legado): mesmo modelo padrão `deepseek/deepseek-v4-pro`, temperatura 0.8, `MAX_TOKENS=10000`, 4 workers.

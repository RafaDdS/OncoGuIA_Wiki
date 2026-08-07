---
title: "Notas de Geração"
category: "Notas"
tags:
  - "notas"
  - "consenso"
status: "draft"
---

# Notas de geração

## 1. Comportamento Diante de Informações Clínicas Faltantes

* **Contexto:** Até a versão 2 do gerador, a IA apenas devolve uma pergunta quando falta um dado da paciente, o que pode quebrar o fluxo da conversa.
* **Diretriz Revisada:** Quando o cenário clínico fornecido pelo usuário estiver incompleto, a IA deve evitar o bloqueio da resposta usando a seguinte hierarquia de ações:
1. **Ramificação Condicional (Cenários Limitados):** Se a variável faltante gerar apenas 2 a 3 possibilidades (ex: status do linfonodo positivo vs. negativo), a IA deve explicar que a conduta depende desse fator e fornecer as respostas para cada cenário (Ex: *"Como o status linfonodal não foi informado, temos dois cenários: Se for positivo, a indicação é X; se for negativo, a indicação é Y."*).
2. **Assunção Declarada:** A IA tem permissão para assumir um dado faltante mais provável para construir sua resposta, **desde que** essa premissa seja declarada de forma direta e evidente no início da explicação (Ex: *"Assumindo que a paciente possua status [[HER2|HER2 negativo]], a abordagem seria..."*).
3. **Solicitação de Dados:** Fazer perguntas diretas ao usuário deve ser reservado apenas para casos onde faltam dados estruturais que gerariam dezenas de ramificações, tornando a resposta confusa.

[← Voltar às Notas Práticas](index.md)
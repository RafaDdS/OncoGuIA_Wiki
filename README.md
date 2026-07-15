# OncoGuIA_Wiki
Este repositório contém a documentação curada e estruturada sobre diretrizes oncológicas, com foco no diagnóstico e tratamento do câncer de mama. 

A base foi desenhada para facilitar o ciclo de curadoria por especialistas médicos e, simultaneamente, servir como fonte de dados padronizada para sistemas de Suporte à Decisão Clínica baseados em Recuperação Aumentada por Geração (RAG).

## Tecnologias e Formato

O projeto utiliza **Markdown** associado a **Wikilinks** (`[[Nome da Página]]`) para criar uma rede interativa de conhecimento. A renderização visual, pesquisa e navegação web são gerenciadas pelo **MkDocs** com o tema Material.

## Pré-requisitos e Instalação

Para rodar a wiki localmente e visualizar as alterações em tempo real, certifique-se de ter o Python 3.x instalado e instale as dependências listadas no projeto:

```bash
pip install -r requirements.txt
```

## Executando Localmente

Inicie o servidor de desenvolvimento do MkDocs na raiz do projeto (onde está localizado o arquivo `mkdocs.yml`):

```bash
mkdocs serve
```
A wiki estará disponível no seu navegador, geralmente no endereço `http://127.0.0.1:8000/`.

## Estrutura

Cada arquivo `.md` na pasta `wiki/` representa um nó do conhecimento oncológico. A arquitetura foi pensada para extração limpa:
- **Frontmatter (YAML):** Pode ser utilizado no topo dos arquivos para metadados (ex: status de revisão do especialista, split do dataset).

## Deploy Automático (GitHub Pages)

Este repositório está integrado com **GitHub Actions**. Qualquer modificação e *push* realizado na branch principal acionará automaticamente a compilação do MkDocs, atualizando a versão online da base de conhecimento através do GitHub Pages.

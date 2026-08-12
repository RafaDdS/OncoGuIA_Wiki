import os
import re
from pathlib import Path

def define_env(env):
    
    # 1. Macro local e sensível ao contexto (sem argumentos)
    @env.macro
    def gerar_lista_arquivos():
        # A macro lê metadados do MkDocs para descobrir exatamente de qual arquivo foi chamada
        caminho_atual = Path(env.page.file.abs_src_path).parent
        docs_dir = Path(env.conf['docs_dir'])

        def preencher_diretorio(diretorio, nivel):
            markdown = ""
            try:
                itens = sorted(diretorio.iterdir(), key=lambda x: x.name.lower())
            except FileNotFoundError:
                return ""

            arquivos = [f for f in itens if f.is_file() and f.suffix == ".md" and f.name != "index.md"]
            pastas = [p for p in itens if p.is_dir() and not p.name.startswith('.')]

            for arq in arquivos:
                markdown += f"- [[{arq.stem}]]\n"
            if arquivos:
                markdown += "\n"

            for pasta in pastas:
                titulo = re.sub(r'^\d+[-_]?', '', pasta.name).replace("-", " ").title()
                caminho_index = pasta / "index.md"
                if caminho_index.exists():
                    titulo_index = extrair_titulo(caminho_index)
                    if titulo_index:
                        titulo = titulo_index
                    href = pasta.name + "/index.md"
                    markdown += f"{'#' * nivel} [{titulo}]({href})\n\n"
                else:
                    markdown += f"{'#' * nivel} {titulo}\n\n"
                markdown += preencher_diretorio(pasta, nivel + 1)

            return markdown

        def extrair_titulo(path_index):
            try:
                texto = path_index.read_text(encoding="utf-8")
            except (IOError, UnicodeDecodeError):
                return None
            m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', texto, re.MULTILINE)
            return m.group(1).strip() if m else None

        return preencher_diretorio(caminho_atual, 2)

    # 2. Macro recursiva para o índice mestre (com cabeçalhos clicáveis)
    @env.macro
    def gerar_indice_principal():
        # Captura dinamicamente qual é o diretório raiz definido no mkdocs.yml (ex: 'wiki')
        docs_dir = Path(env.conf['docs_dir'])
        
        def percorrer_diretorio(diretorio, nivel=2):
            markdown = ""
            itens = sorted(diretorio.iterdir(), key=lambda x: x.name)
            
            pastas = [p for p in itens if p.is_dir() and not p.name.startswith('.')]
            arquivos = [a for a in itens if a.is_file() and a.name.endswith('.md') and a.name != 'index.md']
            
            # 1. Lista os arquivos soltos na pasta atual
            if arquivos:
                for arq in arquivos:
                    markdown += f"- [[{arq.stem}]]\n"
                markdown += "\n"
            
            # 2. Entra recursivamente nas subpastas
            for pasta in pastas:
                titulo_pasta = re.sub(r'^\d+[-_]?', '', pasta.name).replace("-", " ").title()
                
                # Verifica se a pasta possui um index.md próprio
                caminho_index = pasta / "index.md"
                
                if caminho_index.exists():
                    # Calcula o caminho relativo a partir da raiz (ex: 'biomarcadores/index.md')
                    caminho_relativo = pasta.relative_to(docs_dir)
                    # Formata o cabeçalho como um link clicável
                    markdown += f"{'#' * nivel} [{titulo_pasta}]({caminho_relativo}/index.md)\n\n"
                else:
                    # Mantém o cabeçalho como texto puro se a pasta não tiver um index
                    markdown += f"{'#' * nivel} {titulo_pasta}\n\n"
                
                # Chamada recursiva
                markdown += percorrer_diretorio(pasta, nivel + 1)
            
            return markdown
            
        return percorrer_diretorio(docs_dir, 2)
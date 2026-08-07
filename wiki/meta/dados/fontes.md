---
exclude_from_data: true
tags:
  - "meta"
  - "fontes"
---

# Fontes

Referências bibliográficas utilizadas na elaboração das diretrizes. A tabela abaixo permite buscar, filtrar por documento de origem e ordenar por qualquer coluna.

<iframe id="sources-table" src="../fontes.html" style="width: 100%; border: none; overflow: hidden;" scrolling="no"></iframe>

<script>
  window.addEventListener('DOMContentLoaded', () => {
    const iframe = document.getElementById('sources-table');
    const updateHeight = () => {
      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        if (doc && doc.body) {
          const height = Math.max(
            doc.body.scrollHeight,
            doc.documentElement.scrollHeight,
            doc.body.offsetHeight,
            doc.documentElement.offsetHeight
          );
          if (height > 0) iframe.style.height = height + 'px';
        }
      } catch (e) { console.error(e); }
    };
    iframe.addEventListener('load', () => {
      updateHeight();
      let checks = 0;
      const timer = setInterval(() => {
        updateHeight();
        checks++;
        if (checks > 25) clearInterval(timer);
      }, 200);
    });
  });
</script>

---
title: "Home"
tags:
  - "indice"
---

# Wiki — Diretrizes de Câncer de Mama 2026

Índice de todas as páginas propostas, organizadas por categoria. Gerado a partir dos glossários de 4 documentos: [[estadiamento/index|Estadiamento]], Adjuvante, Neoadjuvante e Metastático.

{{ gerar_indice_principal() }}

<iframe id="wiki-graph" src="graph.html" style="width: 100%; border: none; overflow: hidden;" scrolling="no"></iframe>

<script>
  window.addEventListener('DOMContentLoaded', () => {
    const iframe = document.getElementById('wiki-graph');
    
    const updateHeight = () => {
      try {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        if (doc && doc.body) {
          // Find the maximum height of the rendered Matplotlib content
          const height = Math.max(
            doc.body.scrollHeight, 
            doc.documentElement.scrollHeight,
            doc.body.offsetHeight, 
            doc.documentElement.offsetHeight
          );
          if (height > 0) {
            iframe.style.height = height + 'px';
          }
        }
      } catch (e) {
        console.error("Could not resize iframe:", e);
      }
    };

    iframe.addEventListener('load', () => {
      updateHeight();
      
      // Matplotlib graphs render asynchronously; this polls every 200ms 
      // for a few seconds to catch the graph as it grows and finishes loading.
      let checks = 0;
      const timer = setInterval(() => {
        updateHeight();
        checks++;
        if (checks > 25) clearInterval(timer); // Stops after ~5 seconds
      }, 200);
    });
  });
</script>
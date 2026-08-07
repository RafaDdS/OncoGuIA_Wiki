---
exclude_from_data: true
tags:
  - "meta"
  - "dados"
---

# Fluxo Clínico

Diagrama de estados e transições do modelo clínico. Cada coluna representa uma fase da doença; as setas indicam as transições possíveis, com a condição e a probabilidade associada. Passe o mouse sobre um estado para ver a descrição completa.

<iframe id="flow-graph" src="../fluxo.html" style="width: 100%; border: none; overflow: hidden;" scrolling="no"></iframe>

<script>
  window.addEventListener('DOMContentLoaded', () => {
    const iframe = document.getElementById('flow-graph');
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

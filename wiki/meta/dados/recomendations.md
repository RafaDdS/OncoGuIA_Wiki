---
exclude_from_data: true
tags:
  - "meta"
  - "dados"
---

# Recomendações

Recomendações clínicas por fase, subtipo e cenário. Use a busca para localizar tratamentos específicos ou filtre por fase clínica, nível de evidência e força de recomendação.

<iframe id="recs-table" src="../recomendations.html" style="width: 100%; border: none; overflow: hidden;" scrolling="no"></iframe>

<script>
  window.addEventListener('DOMContentLoaded', () => {
    const iframe = document.getElementById('recs-table');
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

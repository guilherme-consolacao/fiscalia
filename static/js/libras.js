(function () {
    var loadButton = document.querySelector('[data-libras-load]');
    var hideButton = document.querySelector('[data-libras-hide]');
    var status = document.querySelector('[data-libras-status]');
    var script = null;
    var timer = null;
    var observer = null;
    if (!loadButton || !hideButton || !status) { return; }

    function placeAccessButton() {
        var support = document.querySelector('.libras-support');
        var host = document.getElementById('vlibras-access-wrapper');
        if (!host) { return; }
        // The player keeps its own viewport positioning and browsing context.
        if (host.parentElement !== support) { support.appendChild(host); }
        if (!host.shadowRoot || host.shadowRoot.querySelector('[data-fiscalia-layout]')) { return; }
        var style = document.createElement('style');
        style.setAttribute('data-fiscalia-layout', '');
        style.textContent = ':host > div { position: relative !important; inset: auto !important; transform: none !important; translate: none !important; animation: none !important; max-width: 100% !important; } :host > div > div { max-width: 100% !important; }';
        host.shadowRoot.appendChild(style);
    }

    function fail() {
        status.textContent = 'O VLibras está indisponível no momento. Você pode continuar usando o portal e tentar novamente mais tarde.';
        loadButton.disabled = false;
        document.body.classList.add('libras-hidden');
        if (script) { script.onload = null; script.onerror = null; script.remove(); script = null; }
        window.clearTimeout(timer);
    }

    loadButton.addEventListener('click', function () {
        if (script) {
            document.body.classList.remove('libras-hidden');
            hideButton.hidden = false;
            status.textContent = 'VLibras disponível pelo botão de Libras na página.';
            return;
        }
        loadButton.disabled = true;
        status.textContent = 'Carregando o apoio em Libras…';
        script = document.createElement('script');
        script.src = 'https://vlibras.gov.br/app/vlibras-plugin.js';
        script.async = true;
        script.referrerPolicy = 'no-referrer';
        script.onerror = fail;
        script.onload = function () {
            window.clearTimeout(timer);
            loadButton.disabled = false;
            hideButton.hidden = false;
            document.body.classList.remove('libras-hidden');
            if (!observer) {
                observer = new MutationObserver(placeAccessButton);
                observer.observe(document.body, {childList: true, subtree: true});
            }
            placeAccessButton();
            status.textContent = 'VLibras carregado. Use o botão de Libras para iniciar a tradução. Você pode ocultá-lo a qualquer momento.';
        };
        timer = window.setTimeout(fail, 15000);
        document.body.appendChild(script);
    });

    hideButton.addEventListener('click', function () {
        document.body.classList.add('libras-hidden');
        hideButton.hidden = true;
        status.textContent = 'Apoio em Libras oculto.';
        loadButton.focus();
    });
}());

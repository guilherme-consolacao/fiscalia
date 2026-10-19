(function () {
    var loadButton = document.querySelector('[data-libras-load]');
    var hideButton = document.querySelector('[data-libras-hide]');
    var status = document.querySelector('[data-libras-status]');
    var script = null;
    var timer = null;
    var observer = null;
    var observedRoots = new WeakSet();
    if (!loadButton || !hideButton || !status) { return; }

    function placeWidget() {
        var support = document.querySelector('.libras-support');
        ['vlibras-access-wrapper', 'vlibras-app-root'].forEach(function (id) {
            var host = document.getElementById(id);
            if (!host) { return; }
            // Moving a live iframe detaches its browsing context. Keep the
            // translator where VLibras creates it; only relocate its button.
            if (id === 'vlibras-access-wrapper' && host.parentElement !== support) { support.appendChild(host); }
            if (!host.shadowRoot) { return; }
            if (!observedRoots.has(host.shadowRoot)) {
                observer.observe(host.shadowRoot, {childList: true, subtree: true});
                observedRoots.add(host.shadowRoot);
            }
            if (!host.shadowRoot.querySelector('[data-fiscalia-layout]')) {
                var style = document.createElement('style');
                style.setAttribute('data-fiscalia-layout', '');
                style.textContent = ':host > div { position: relative !important; inset: auto !important; transform: none !important; translate: none !important; animation: none !important; max-width: 100% !important; } :host > div > div { max-width: 100% !important; }';
                host.shadowRoot.appendChild(style);
            }
        });
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
            document.body.classList.add('libras-layout');
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
            document.body.classList.add('libras-layout');
            if (!observer) {
                observer = new MutationObserver(placeWidget);
                observer.observe(document.body, {childList: true, subtree: true});
            }
            placeWidget();
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

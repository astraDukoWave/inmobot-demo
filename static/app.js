// InmoBot UI. Regla: ningún dato del servidor o del usuario entra como HTML; todo va con textContent.
(function () {
    'use strict';
    var sessionId = null;  // lo asigna el servidor (UUID4); se pierde al recargar
    var busy = false;
    var win = document.getElementById('chat-window');
    var messages = document.getElementById('chat-messages');
    var typing = document.getElementById('typing-indicator');
    var input = document.getElementById('chat-input');
    var sendBtn = document.getElementById('send-button');
    var fmt = new Intl.NumberFormat('es-MX');

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = String(text);
        return node;
    }
    function insert(node) { messages.insertBefore(node, typing); messages.scrollTop = messages.scrollHeight; }
    function openChat() { win.hidden = false; input.focus(); }
    function closeChat() { win.hidden = true; document.getElementById('chat-button').focus(); }

    function addMessage(text, kind) {
        var wrap = el('div', 'message ' + kind);
        wrap.appendChild(el('div', 'message-content', text));
        insert(wrap);
    }

    function addCard(p) {
        var card = el('article', 'property-card');
        var img = document.createElement('img');
        if (typeof p.image_url === 'string' && p.image_url.indexOf('https://') === 0) img.src = p.image_url;
        img.alt = 'Imagen ilustrativa de ' + p.name;
        img.loading = 'lazy';
        card.appendChild(img);
        var info = el('div', 'property-info');
        if (p.alternative) info.appendChild(el('span', 'tag', 'Alternativa cercana'));
        info.appendChild(el('h3', null, p.name));
        info.appendChild(el('div', 'price', '$' + fmt.format(p.price_mxn) + ' MXN'));
        info.appendChild(el('div', 'details', '📍 ' + p.zone + ' · ' + p.type));
        info.appendChild(el('div', 'details', '🛏️ ' + p.bedrooms + ' recámaras · 🚿 ' + p.bathrooms + ' baños · 📏 ' + p.area_m2 + ' m²'));
        var btn = el('button', 'card-action', 'Quiero visitarla');
        btn.type = 'button';
        btn.addEventListener('click', function () { send('Quiero agendar una visita a ' + p.name); });
        info.appendChild(btn);
        card.appendChild(info);
        insert(card);
    }

    function addAction(a) {
        if (a.type === 'visit_requested') {
            var when = a.preferred_date ? ' · preferencia: ' + a.preferred_date : '';
            insert(el('div', 'action-note', '📅 Solicitud de visita registrada: ' + a.property_name + when +
                '. Un asesor la confirmará.'));
        } else if (a.type === 'whatsapp' && typeof a.url === 'string' && a.url.indexOf('https://wa.me/') === 0) {
            var link = el('a', 'whatsapp-button', '💬 ' + (a.label || 'Continuar por WhatsApp'));
            link.href = a.url;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            insert(link);
        }
    }

    function errorText(status) {
        if (status === 429) return 'Vas muy rápido. Espera un momento e inténtalo de nuevo.';
        if (status === 422) return 'Tu mensaje es muy largo o está vacío (máximo 1,000 caracteres).';
        if (status === 409) return 'Espera la respuesta anterior.';
        return 'Lo siento, hubo un error de conexión. Inténtalo de nuevo.';
    }

    function setBusy(value) {
        busy = value;
        sendBtn.disabled = value;
        typing.classList.toggle('active', value);
    }

    function send(text) {
        text = (text || '').trim();
        if (!text || busy) return;
        var chips = document.getElementById('chips');
        if (chips) chips.remove();
        addMessage(text, 'user');
        input.value = '';
        setBusy(true);
        fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId, message: text })
        }).then(function (res) {
            return res.json().catch(function () { return {}; }).then(function (data) { return { res: res, data: data }; });
        }).then(function (r) {
            setBusy(false);
            if (!r.res.ok) { addMessage(r.data.detail || errorText(r.res.status), 'error'); return; }
            sessionId = r.data.session_id;
            addMessage(r.data.reply, 'bot');
            (r.data.cards || []).forEach(addCard);
            (r.data.actions || []).forEach(addAction);
        }).catch(function () {
            setBusy(false);
            addMessage(errorText(0), 'error');
        });
    }

    document.getElementById('open-chat').addEventListener('click', openChat);
    document.getElementById('chat-button').addEventListener('click', function () {
        if (win.hidden) { openChat(); } else { closeChat(); }
    });
    document.getElementById('close-chat').addEventListener('click', closeChat);
    document.getElementById('chat-input-area').addEventListener('submit', function (e) {
        e.preventDefault();
        send(input.value);
    });
    Array.prototype.forEach.call(document.querySelectorAll('.chip'), function (chip) {
        chip.addEventListener('click', function () { send(chip.textContent); });
    });
})();

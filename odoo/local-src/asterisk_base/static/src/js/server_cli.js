odoo.define('asterisk.server_cli', function(require) {
    "use strict";

    var core = require('web.core');
    var common = require('web.form_common');
    var ajax = require('web.ajax');
    var dom_utils = require('web.dom_utils');
    var Widget = require('web.Widget');

    var ServerCli = common.AbstractField.extend({
      className: 'terminal-container',
      id: _.uniqueId('terminal-container-'),

      renderElement: function() {
        this._super();
        var self = this;
        console.log('render');
        this.term = new Terminal({
          cols: 100,
          rows: 24
        });
        var button = document.createElement('button');
        button.setAttribute('class', 'btn btn-info bt-lg');
        button.innerHTML = 'Launch Console';
        button.onclick = function() {
          self.term.open(self.el, focus=true);
          self.set_dimensions('100%', '100%');
          button.onclick = undefined;
          self.el.removeChild(button);
        }
        this.el.appendChild(button);
      },

      start: function() {
        this._super();
        var self = this;
        var socketURL = self.get('value');
        var sock = new WebSocket(socketURL);
        sock.addEventListener('open', function () {
          self.term.terminadoAttach(sock);
        });
      },
    });

    core.form_widget_registry.add('server_cli', ServerCli);

  });

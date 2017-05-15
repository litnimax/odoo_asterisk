odoo.define('asterisk.server_cli', function(require) {
    "use strict";

    var core = require('web.core');
    var common = require('web.form_common');
    var ajax = require('web.ajax');
    var dom_utils = require('web.dom_utils');
    var Widget = require('web.Widget');

    var ServerCli = common.AbstractField.extend({

      willStart: function() {
        console.log('ajax');
        if (!this.loadJS_def) {
          this.loadJS_def = ajax.loadJS(
            '/asterisk_base/static/lib/xterm/dist/xterm.js').then(function() {
                return $.when(
                  ajax.loadJS('/asterisk_base/static/lib/xterm/dist/addons/terminado/terminado.js')
                )
              });
        }
        return $.when(this._super(), this.loadJS_def);
      },

      renderElement: function() {
        this._super();
        this.$el.append('<div id="terminal-container" class="terminal-container"></div>');
        this.term = new Terminal({
          cols: 100,
          rows: 24
        });
      },

      start: function() {
        var socketURL = this.get('value');
        var sock = new WebSocket(socketURL);
        var self = this;
        sock.addEventListener('open', function () {
          self.term.terminadoAttach(sock);
        });
        // Now it need some time to load correctly.
        setTimeout(function() {
          self.term.open(document.getElementById('terminal-container'), focus=true);
          self.set_dimensions('100%', '100%');
        }, 3000);

      },

    });

    core.form_widget_registry.add('server_cli', ServerCli);

  });

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
        this.$el.append('<div class="terminal-container"/>');
        var self = this;
        self.term = new Terminal({
          cols: 80,
          rows: 24
        });

        console.log('term created.')
        self.term.open(self.$('.terminal-container')[0], focus=true);
      },


      start: function() {
        console.log('start');
        var socketURL = this.get('value');
        var sock = new WebSocket(socketURL);
        var self = this;
        sock.addEventListener('open', function () {
          self.term.terminadoAttach(sock);
        });

      },

    });

    core.form_widget_registry.add('server_cli', ServerCli);

  });

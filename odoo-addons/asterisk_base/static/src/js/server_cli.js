odoo.define('asterisk.server_cli', function(require) {
    "use strict";

    var core = require('web.core');
    var common = require('web.form_common');
    var ajax = require('web.ajax');

    var ServerCli = common.AbstractField.extend(common.ReinitializeFieldMixin, {
      template: 'ServerCli',

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

      initialize_content: function() {
        console.log('init');
        var self = this;
        var value = this.get('value');
        if (!value || !$('.terminal-container').is(':visible')) return
        if (!this.myTerminal && !this.get('effective_readonly')) {
          console.log('new term');
          this.myTerminal = new Terminal();
          var protocol = (location.protocol === 'https:') ? 'wss://' : 'ws://';
          //socketURL = protocol + location.hostname + ((location.port) ? (':' + location.port) : '') + "/websocket";
          var socketURL = value;
          var sock = new WebSocket(socketURL);
          sock.addEventListener('open', function () {
            self.myTerminal.terminadoAttach(sock);
          });
          this.myTerminal.open(document.getElementById('terminal-container'), focus=true);
          this.$el.css({
            width: '100%',
            minHeight: '100%',
          });
          console.log('init complete', this.myTerminal);
        }
      },

      destroy_content: function() {
        console.log('destroy');
        delete this.myTerminal;
      },

    });
    core.form_widget_registry.add('server_cli', ServerCli);

  });

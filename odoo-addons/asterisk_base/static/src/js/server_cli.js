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
        var sup = this._super();
        console.log('render');
        var self = this;
        self.term = new Terminal({
          cols: 100,
          rows: 24
        });
      },

      start: function() {
        this._super();
        var self = this;
        console.log(this);
        this.el.parentNode.onclick = function() {
          self.term.open(self.el, focus=false);
          self.set_dimensions('100%', '100%');
          this.onclick = undefined;
        }
        var socketURL = self.get('value');
        var sock = new WebSocket(socketURL);
        sock.addEventListener('open', function () {
          self.term.terminadoAttach(sock);
        });
        setTimeout(function() {
                  //self.term.open(self.el, focus=false);
                  //self.set_dimensions('100%', '100%');
                }, 3000);
        //self.term.open(this.el, focus=false);
        //self.set_dimensions('100%', '100%');

      },

    });

    core.form_widget_registry.add('server_cli', ServerCli);

  });

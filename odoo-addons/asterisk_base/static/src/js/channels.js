odoo.define("asterisk.channels", function (require) {
  "use strict";

  var core = require('web.core');
  var ListView = require('web.ListView');
  var bus = require('bus.bus').bus;

  var bus_channel = 'asterisk_channels'; //JSON.stringify(['odoo10_asterisk', 'asterisk.base', 1]);
  bus.add_channel(bus_channel);
  bus.start_polling();

  var ChannelList = ListView.include({

      init: function() {
        this._super.apply(this, arguments);
        var self = this;
        if (this.model == 'asterisk.channel') {
          bus.on("notification", this, function() {
            self.reload();
          });
        }
      },
    });
  });

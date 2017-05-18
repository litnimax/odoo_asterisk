odoo.define("asterisk.channels", function (require) {
  "use strict";

  var common = require('web.form_common');
  var core = require('web.core');
  var Widget = require('web.Widget');
  var QWeb = core.qweb;
  var bus = require('bus.bus').bus;

  var bus_channel = 'asterisk_channels'; //JSON.stringify(['odoo10_asterisk', 'asterisk.base', 1]);
  bus.add_channel(bus_channel);
  bus.start_polling();

  var ChannelList = Widget.extend({
      template: 'channels',

      start: function() {
          this._super();
          var self = this;
          bus.on("notification", this, function() {
            console.log(self);
            self.do_action('asterisk_base.asterisk_channels_action', {});
          });


          $.ajax("http://192.168.56.102:8088/ari/channels?api_key=asterisk_admin:admin-secret", {
              type: "GET",
              dataType: "json",
              contentType: "application/json",
          }).then(function(channels) {
              $('.channels_list').html(
                  $(QWeb.render('channels.list', {'channels': channels})));
              console.log("channels:", channels);
          });
      },

    });

    core.action_registry.add('asterisk.channels', ChannelList);

  });

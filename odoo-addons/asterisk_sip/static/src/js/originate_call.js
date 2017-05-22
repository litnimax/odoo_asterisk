odoo.define('asterisk_sip.originate_call_widget', function (require) {
  "use strict";

  var core = require('web.core');
  var common = require('web.form_common');
  var ajax = require('web.ajax');
  var dom_utils = require('web.dom_utils');
  var formats = require('web.formats');
  var FieldChar = core.form_widget_registry.get('char');
  var Model = require('web.Model');

  var OriginateCall = FieldChar.extend({

    template: 'OriginateCallFieldChar',

    render_value: function() {
      console.log('render');
      var show_value = this.format_value(this.get('value'), '');
      if (this.$input) {
            this.$input.val(show_value);
      }
      else {
        this.$el.find('.originate_call').text(show_value);
        this.$el.find('.originate_call_button').click(function(){
          var Partner = new Model('res.partner');
          Partner.call('originate_call', [show_value], {context: this._context});
        });
      }
    },


  });

  core.form_widget_registry.add('originate_call', OriginateCall);

});

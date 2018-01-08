odoo.define('asterisk_base.form_widgets', function (require) {
  "use strict";

  var core = require('web.core');
  var common = require('web.form_common');
  var ajax = require('web.ajax');
  var dom_utils = require('web.dom_utils');
  var formats = require('web.formats');
  var TextField = core.form_widget_registry.get('text');

  var AsteriskConfField = common.AbstractField.extend(common.ReinitializeFieldMixin, {
    template: 'AsteriskConf',

    events: {
        'change': 'store_value',
    },

    willStart: function() {
      console.log('ajax');
      if (!this.loadJS_def) {
        this.loadJS_def = ajax.loadJS(
          '/asterisk_base/static/lib/codemirror/lib/codemirror.js').then(function() {
              return $.when(
                ajax.loadJS('/asterisk_base/static/lib/codemirror/mode/asterisk/asterisk.js'),
                ajax.loadJS('/asterisk_base/static/lib/codemirror/addon/display/autorefresh.js'),
                ajax.loadJS('/asterisk_base/static/lib/codemirror/addon/scroll/simplescrollbars.js'),
              )
            });
      }
      return $.when(this._super(), this.loadJS_def);
    },

    initialize_content: function() {
      var self = this;
      //console.log('init', this.myCodeMirror);
      if (!this.myCodeMirror) {
        console.log('CodeMirror not found, creating.');
        this.myCodeMirror = CodeMirror(function(elt) {
          self.$el[0].parentNode.replaceChild(elt, self.$el[0]);
          },
          {
            'readOnly': 'nocursor',
            'mode': 'asterisk',
            'autofocus': false,
            'autoRefresh': true,
            //'viewportMargin': Infinity,
            'theme': 'blackboard',
            'scrollbarStyle': 'overlay',
          });
        var value = formats.format_value(this.get('value'), this, '');
        this.myCodeMirror.setValue(value);
        //this.myCodeMirror.setSize({width: '100%', hight: '100%'});

        this.myCodeMirror.on("blur", function() {
          if (self.myCodeMirror) {
            self.set_value($('.CodeMirror')[0].CodeMirror.getValue());
          }
        });
      }
    },

    store_value: function() {
      console.log('store');
      this.internal_set_value(formats.parse_value(this.$el.val(), this));
    },

    
    render_value: function() {
      this._super();
      if (!this.get('effective_readonly')) {
        var value = formats.format_value(this.get('value'), this, '');
        this.myCodeMirror.setValue(value);
        this.myCodeMirror.setOption('readOnly', false);
      }
      else {
        var value = formats.format_value(this.get('value'), this, '');
        if ($('.CodeMirror')[0]) {
          $('.CodeMirror')[0].CodeMirror.setValue(value);
          $('.CodeMirror')[0].CodeMirror.setOption('readOnly', 'nocursor');
        }
         var show_value = formats.format_value(this.get('value'), this, '');
         this.$el.val(show_value);
         //dom_utils.autoresize(this.$el, {parent: this});
      }

    },

  });

  core.form_widget_registry.add('asterisk_conf', AsteriskConfField);

});

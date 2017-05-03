
odoo.define('asterisk_base.form_widgets', function (require) {
  "use strict";

  var core = require('web.core');
  var form_common = require('web.form_common');
  var TextField = core.form_widget_registry.get('text');

  var AsteriskConfTextField = TextField.include({
      template: 'CodeMirror',
  });

  core.form_widget_registry.add('asterisk_conf', AsteriskConfTextField);

});

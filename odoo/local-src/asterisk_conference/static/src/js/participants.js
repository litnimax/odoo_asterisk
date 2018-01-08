openerp.asterisk_conference = function(instance) {
    var _t = instance.web._t,
        _lt = instance.web._lt;
    var QWeb = instance.web.qweb;

    instance.asterisk_conference = {};

    instance.asterisk_conference.Participants = instance.web.Widget.extend({
        template: 'asterisk_conference.participants',
        
        start: function() {
                console.log("participants");
        },

        ir_actions_act_reload_view: function (action, options) {
            this.inner_widget.views[this.inner_widget.active_view].controller.reload();
            return $.when();
        },

        
    });
    
    instance.web.client_actions.add('asterisk_conference.participants',
        'instance.asterisk_conference.Participants');
}

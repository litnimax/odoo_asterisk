# -*- coding: utf-8 -*-

from datetime import datetime
from openerp import models, fields, api
from asterisk import *


class conference_contact(models.Model):
    _name = 'asterisk_conference.contact'

    phone = fields.Char(required=True)
    name = fields.Char()


class conference(models.Model):
    _name = 'asterisk_conference.conference'
    _description = 'Asterisk Conference'
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    number = fields.Char(required=True)
    name = fields.Char(required=True)
    is_public = fields.Boolean()
    conference_profile = fields.Many2one(
        comodel_name='asterisk_conference.conference_profile')
    public_participant_profile = fields.Many2one(
        comodel_name='asterisk_conference.participant_profile')
    participants = fields.One2many(comodel_name='asterisk_conference.participant',
                                   inverse_name='conference')
    last_synced = fields.Datetime(default=fields.Datetime.now)

    _sql_constraints = [
        ('number_uniq', 'UNIQUE(number)', 'Number must be unique!')
    ]

    @api.one
    def sync_participants(self):
        if (datetime.now() - datetime.strptime(self.last_synced,
                                               '%Y-%m-%d %H:%M:%S')).seconds < 200:
            print 'Not syncing.'
            return
        self.participants.unlink()
        for conf in confbridge_list2():
            self.env['asterisk_conference.participant'].create({
                'conference': self.id,
                'phone': conf,
                'name': conf,
                'is_admin': True,
                'is_marked': False,
                'is_muted': False,
            })
            self.last_synced = datetime.now()





class conference_log(models.Model):
    _name = 'asterisk_conference.log'

    conference = fields.Many2one('asterisk_conference.conference')
    message = fields.Char()


class member(models.Model):
    _name = 'asterisk_conference.member'

    conference = fields.Many2one(comodel_name='asterisk_conference.conference')
    phone = fields.Char(index=True, required=True)
    name = fields.Char()
    is_invited = fields.Boolean(default=True)
    profile = fields.Many2one('asterisk_conference.participant_profile')

    _sql_constraints = [
        ('conference_phone_uniq', 'UNIQUE(conference, phone)', 'Phones are unique in a conference!')
    ]



class participant(models.Model):
    _name = 'asterisk_conference.participant'

    conference = fields.Many2one(comodel_name='asterisk_conference.conference')
    phone = fields.Char(index=True, required=True)
    name = fields.Char()
    is_admin = fields.Boolean()
    is_muted = fields.Boolean()
    is_marked = fields.Boolean()

    @api.one
    def onoff_admin(self):
        self.is_admin = not self.is_admin

    @api.one
    def onoff_mute(self):
        self.is_muted = not self.is_muted

    @api.one
    def kick(self):
        from random import random
        open('/tmp/confbridge_list2','w').write('%s\n%s' % (random(), random()))
        self.conference.last_synced = datetime.now()
        return {
            'type': 'ir.actions.client',
            'tag': 'asterisk_conference.participants'
        }



class conference_profile(models.Model):
    _name = 'asterisk_conference.conference_profile'
    name = fields.Char(required=True)
    max_members = fields.Integer(default=50, help="""Limits the number of participants for a single conference to a specific number. By default, conferences have no participant limit. After the limit is reached, the conference will be locked until someone leaves. Admin-level users are exempt from this limit and will still be able to join otherwise-locked, because of limit, conferences.""")
    record_conference = fields.Boolean(help="""Records the conference call starting when the first user enters the room, and ending when the last user exits the room. The default recorded filename is 'confbridge-<name of conference bridge>-<start time>.wav' and the default format is 8kHz signed linear. By default, this option is disabled. This file will be located in the configured monitoring directory as set in conf""")
    internal_sample_rate = fields.Selection(selection=[
                                ('auto','auto'), ('8000', '8000'),
                                ('12000', '12000'), ('16000', '16000'),
                                ('24000', '24000'), ('32000', '32000'),
                                ('44100', '44100'), ('48000', '48000'),
                                ('96000', '96000'), ('192000', '192000')],
                                default='20',
                                help="""Sets the internal native sample rate at which to mix the conference. The "auto" option allows Asterisk to adjust the sample rate to the best quality / performance based on the participant makeup. Numbered values lock the rate to the specified numerical rate. If a defined number does not match an internal sampling rate supported by Asterisk, the nearest sampling rate will be used instead.""")
    mixing_interval = fields.Selection(selection=[
                                            ('10', '10'), ('20', '20'),
                                            ('40', '40'), ('80','80')],
                                        default='20',
                                        help="""Sets, in milliseconds, the internal mixing interval. By default, the mixing interval of a bridge is 20ms. This setting reflects how "tight" or "loose" the mixing will be for the conference. Lower intervals provide a "tighter" sound with less delay in the bridge and consume more system resources. Higher intervals provide a "looser" sound with more delay in the bridge and consume less resources""")
    video_mode = fields.Selection(selection=[('none', 'none'), ('follow_talker', 'follow_talker'),
                                            ('last_marked', 'last_marked'),
                                            ('first_marked', 'first_marked')],
                                  default='none',
                                  help="""Configured video (as opposed to audio) distribution method for conference participants. Participants must use the same video codec. Confbridge does not provide MCU functionality. It does not transcode, scale, transrate, or otherwise manipulate the video. Options are "none," where no video source is set by default and a video source may be later set via AMI or DTMF actions; "follow_talker," where video distrubtion follows whomever is talking and providing video; "last_marked," where the last marked user with video capabilities to join the conference will be the single video source distributed to all other participants - when the current video source leaves, the marked user previous to the last-joined will be used as the video source; and "first-marked," where the first marked user with video capabilities to join the conference will be the single video source distributed to all other participants - when the current video source leaves, the marked user that joined next will be used as the video source. Use of video in conjunction with the jitterbuffer results in the audio being slightly out of sync with the video - because the jitterbuffer only operates on the audio stream, not the video stream. Jitterbuffer should be disabled when video is used.""")


class participant_profile(models.Model):
    _name = 'asterisk_conference.participant_profile'

    name = fields.Char(required=True)
    admin = fields.Boolean(index=True)
    marked = fields.Boolean(index=True)
    startmuted = fields.Boolean()
    music_on_hold_when_empty = fields.Boolean()
    music_on_hold_class = fields.Char(default='default')
    quiet = fields.Boolean()
    announce_user_count = fields.Boolean()
    announce_user_count_all = fields.Char()
    announce_only_user = fields.Boolean()
    announcement = fields.Char()
    wait_marked = fields.Boolean()
    end_marked = fields.Boolean()
    dsp_drop_silence = fields.Boolean()
    dsp_talking_threshold = fields.Integer(default=160)
    dsp_silence_threshold = fields.Integer(default=2500)
    talk_detection_events = fields.Boolean()
    denoise = fields.Boolean()
    jitterbuffer = fields.Boolean()
    pin = fields.Char(index=True)
    announce_join_leave = fields.Boolean()
    dtmf_passthrough = fields.Boolean()
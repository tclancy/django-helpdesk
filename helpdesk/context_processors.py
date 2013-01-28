from helpdesk import settings as helpdesk_settings


def helpdesk_setting_provider(context):
    return {'helpdesk_settings': helpdesk_settings}

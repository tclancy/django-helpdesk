"""
django-helpdesk - A Django powered ticket tracker for small enterprise.

(c) Copyright 2008 Jutda. All Rights Reserved. See LICENSE for details.

views/public.py - All public facing views, eg non-staff (no authentication
                  required) views.
"""

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _

from helpdesk import settings as helpdesk_settings
from helpdesk.forms import PublicTicketForm
from helpdesk.lib import text_is_spam
from helpdesk.models import Ticket, Queue, UserSettings, KBCategory


def homepage(request):
    if not request.user.is_authenticated() and helpdesk_settings.HELPDESK_REDIRECT_TO_LOGIN_BY_DEFAULT:
        return HttpResponseRedirect(reverse('login'))

    if request.user.is_staff:
        try:
            if getattr(request.user.usersettings.settings, 'login_view_ticketlist', False):
                return HttpResponseRedirect(reverse('helpdesk_list'))
            else:
                return HttpResponseRedirect(reverse('helpdesk_dashboard'))
        except UserSettings.DoesNotExist:
            return HttpResponseRedirect(reverse('helpdesk_dashboard'))

    knowledgebase_categories = KBCategory.objects.all()

    open_tickets = None
    closed_tickets = None
    if request.user.is_authenticated():
        open_tickets = Ticket.objects.filter(status=Ticket.OPEN_STATUS)
        if not request.user.is_staff:
            open_tickets = open_tickets.filter(submitter_email=request.user.email)
            closed_tickets = Ticket.objects.filter(status=Ticket.CLOSED_STATUS,
                                                   submitter_email=request.user.email)

    return render_to_response('helpdesk/public_homepage.html',
        RequestContext(request, {
            'kb_categories': knowledgebase_categories,
            'open_tickets': open_tickets,
            'closed_tickets': closed_tickets
        }))


def view_ticket(request):
    ticket_req = request.GET.get('ticket', '')
    ticket = False
    email = request.GET.get('email', '')
    error_message = ''

    if ticket_req and email:
        parts = ticket_req.split('-')
        queue = '-'.join(parts[0:-1])
        ticket_id = parts[-1]

        try:
            ticket = Ticket.objects.get(id=ticket_id, queue__slug__iexact=queue, submitter_email__iexact=email)
        except:
            ticket = False
            error_message = _('Invalid ticket ID or e-mail address. Please try again.')

        if ticket:

            if request.user.is_staff:
                redirect_url = reverse('helpdesk_view', args=[ticket_id])
                if request.GET.has_key('close'):
                    redirect_url += '?close'
                return HttpResponseRedirect(redirect_url)

            if request.GET.has_key('close') and ticket.status == Ticket.RESOLVED_STATUS:
                from helpdesk.views.staff import update_ticket
                # Trick the update_ticket() view into thinking it's being called with
                # a valid POST.
                request.POST = {
                    'new_status': Ticket.CLOSED_STATUS,
                    'public': 1,
                    'title': ticket.title,
                    'comment': _('Submitter accepted resolution and closed ticket'),
                    }
                if ticket.assigned_to:
                    request.POST['owner'] = ticket.assigned_to.id
                request.GET = {}

                return update_ticket(request, ticket_id, public=True)

            # redirect user back to this ticket if possible.
            redirect_url = ''
            if helpdesk_settings.HELPDESK_NAVIGATION_ENABLED:
                redirect_url = reverse('helpdesk_view', args=[ticket_id])

            return render_to_response('helpdesk/public_view_ticket.html',
                RequestContext(request, {
                    'ticket': ticket,
                    'next': redirect_url,
                }))

    return render_to_response('helpdesk/public_view_form.html',
        RequestContext(request, {
            'ticket': ticket,
            'email': email,
            'error_message': error_message,
        }))

def change_language(request):
    return_to = ''
    if request.GET.has_key('return_to'):
        return_to = request.GET['return_to']

    return render_to_response('helpdesk/public_change_language.html',
        RequestContext(request, {'next': return_to}))

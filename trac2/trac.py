"""
interface to trac
"""
from __future__ import absolute_import

from collections import defaultdict

from trac.env import Environment
from trac.ticket.model import Ticket
from trac.ticket.query import Query
from trac.wiki.api import WikiSystem
from trac.wiki.model import WikiPage as TracWikiPage


class TracTicket(object):
    """
    internal representation of a track ticket
    """
    def __init__(self, adaptor, ticket):
        self._adaptor = adaptor
        self._ticket = ticket

    def __repr__(self):
        return "Ticket({})".format(self._ticket.id)

    def as_dict(self):
        """
        produce ticket representation as a dictionary
        """
        tempo = self._ticket.values.copy()

        contributors = defaultdict(set)

        reporter = tempo.pop('reporter', None)
        if reporter:
            contributors[self._adaptor.user(reporter)].add('reporter')

        owner = tempo.pop('owner', None)
        if owner:
            contributors[self._adaptor.user(owner)].add('owner')

        for item in tempo.pop('cc', '').split(','):
            item = item.strip()
            if not item:
                continue

            contributors[item].add('watcher')
        comments = []
        for time, author, field, oldvalue, newvalue, permanent in self._ticket.get_changelog():
            if field == 'comment':
                comments.append(dict(author=author, message=newvalue, time=time))
            contributors[self._adaptor.user(author)].add('commenter')

        tempo['comments'] = comments
        tempo['contributors'] = dict(contributors)
        tempo['id'] = self._ticket.id
        tempo['url'] = self._adaptor.env.abs_href.ticket(self._ticket.id)

        return tempo

    def mark_exported(self, issue, url):
        """
        mark the ticket as exported
        """
        if url:
            self._ticket.save_changes(comment="migrated to " + url)


class WikiPage(TracWikiPage):
    def as_dict(self):
        return dict(
            name=self.name,
            text=self.text
        )


class TracAdaptor(object):
    """
    interface b/w a trac instance and the converter
    """
    def __init__(self, config, dry_run=False):
        self._dry_run = dry_run

        self._milestones = config['milestones']
        self._min_year = config['min_year']

        self._env = Environment(config['env'])
        self._users = { key: value.strip() for key, _, value in self._env.get_known_users() if value}

    @property
    def env(self):
        """
        Trac environment
        """
        return self._env

    def ticket(self, data):
        """
        create a wrapper over a Trac ticket
        """
        return TracTicket(self, Ticket(self._env, data['id']))

    def normalise_list(self, user_list):
        """
        normalise user list
        """
        return [self.user(user) for user in user_list.replace(',', ' ').split()]

    def user(self, user):
        """
        normalise user's email
        """
        return self._users.get(user, user)

    @staticmethod
    def trac2md(text):
        """
        somewhat convert trac markup to markdown one
        """

    def get_tickets(self):
        """
        yield all the tickets per self._env and self._milestones
        """
        query = [
            'status!=closed'
        ]

        if self._milestones:
            query.append('milestone={}'.format(
                '|'.join(mstone for mstone in self._milestones)))
        print "query: ", query
        q = Query.from_string(self._env, '&'.join(query))
        q.max = 10000000
        res = q.execute()
        res = filter(lambda ticket:(ticket['time'].year >= self._min_year), res)
        for i, ticket in enumerate(res):
            ticket = self.ticket(ticket)
            print "handling ticket", ticket, i, "/", len(res)
            yield ticket

    def get_wikipages(self):
        """
        yield all the tickets per self._env and self._milestones
        """
        w = WikiSystem(self._env)
        for page in w.pages:
            page = WikiPage(self._env, page)
            yield page

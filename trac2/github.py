"""
interface to GitHub
"""
from json import load, dump
import os
from pprint import pprint

from github3 import GitHub


class GitHubAdaptor(object):
    """
    thin wrapper over github3 with the purpose of importin [trac] tickets
    """
    def __init__(self, config, dry_run=False):
        self._dry_run = dry_run
        self._mapping = config['mapping']
        self._template = config['template']

        self._gh = GitHub(token=config['token'])

        # Everything is done via _repo
        self._repo = self._gh.repository(config['owner'], config['repository'])

        # get current set of available milestones
        self._milestones = dict({
            milestone.title: milestone.number
            for milestone in self._repo.iter_milestones()
        })

        self._users = dict()

        self._user_cache = config.get('user_cache', None)

        self._load_user_cache()

    def __del__(self):
        """
        save currently known user mapping
        """
        if self._user_cache is not None:
            with open(self._user_cache, 'w') as user_cache:
                dump(self._users, user_cache)

    def _load_user_cache(self):
        """
        load users that are already handled in a previous attempt
        """
        if self._user_cache is not None and os.path.isfile(self._user_cache):
            with open(self._user_cache) as user_cache:
                tempo = load(user_cache)

                assert isinstance(tempo, dict)

                self._users = tempo

    def ensure_milestone(self, name):
        """
        check if the given milestone is known already and if it's not create it
        """
        num = self._milestones.get(name, None)

        if num is None:
            milestone = self._repo.create_milestone(name)

            num = self._milestones[name] = milestone.number

        return num

    def get_user(self, user):
        """
        transform the given id to a github username if it's an public e-mail

        cache results
        take into account provided mapping
        """
        if user is None:
            return user

        gh_user = self._users.get(user, None)

        if gh_user is None:
            gh_user = self._mapping.get(user, user)

            if gh_user.find('@') > 0:
                result = list(self._gh.search_users('{} in:email'.format(gh_user)))

                if len(result) == 1:
                    gh_user = '@{}'.format(result[0].user.login)

            self._users[user] = gh_user

        return gh_user

    def _convert_contributors(self, contributors):
        """
        represent the list of contributors in Markdown
        """
        result = list()

        for user, contributions in contributors.items():
            gh_user = self.get_user(user)

            if not gh_user:     # what this would be?
                continue

            if gh_user[0] == '@':
                display_user = gh_user  # this will result in a mention
            else:
                parts = gh_user.split('@')

                assert len(parts) in (1, 2), 'Special case, needs handling'

                if len(parts) == 2:     # only first part of the e-mail
                    display_user = '`{}@...`'.format(parts[0])
                else:                   # use as is
                    display_user = '`{}`'.format(gh_user)

            result.append('{} ({})'.format(display_user,
                                           ', '.join(contributions)))
        return ', '.join(result)

    def create_issue(self, ticket):
        """
        create an issue in the given project
        """
        assert isinstance(ticket, dict)

        pprint(ticket)

        self._repo.create_issue(
            ticket['summary'],
            body=self._template.format(
                trac_id=ticket['id'], trac_url=ticket['url'],
                users=self._convert_contributors(ticket['contributors']),
                body=ticket['description']),
            milestone=self.ensure_milestone(ticket['milestone']))

        # stub
        return None, None

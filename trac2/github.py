"""
interface to GitHub
"""
import datetime
import os
import time
from json import dump, load
from pprint import pprint

from github3 import GitHub

from trac2.convert import convert_text


def format_date(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%b %d %Y")


class GitHubAdaptor(object):
    """
    thin wrapper over github3 with the purpose of importin [trac] tickets
    """
    def __init__(self, config, dry_run=False, only_from_cache=False, mention_people=False):
        self._dry_run = dry_run
        self._only_from_cache = only_from_cache
        self._mention_people = mention_people
        self._mapping = config['mapping']
        self._template = config['template']

        self._gh = GitHub(token=config['token'])
        # Everything is done via _repo
        self._repo = self._gh.repository(config['owner'], config['repository'])
        self._upstream_repo = self._gh.repository(config['upstream_owner'], config['upstream_repository'])

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
                self._users.update(self._mapping)

    def ensure_milestone(self, name):
        """
        check if the given milestone is known already and if it's not create it
        """
        num = self._milestones.get(name, None)
        if num is None:
            milestone = self._repo.create_milestone(name)

            num = self._milestones[name] = milestone.number

        return num

    def find_user_in_commits(self, email):
        """
            find a user using the commit api.
            This helps to find more users, as the email is not always public for search api

            also this helps with rate limits on search api
        """
        if email in self._users:
            return self._users[email]

        gh_user = None
        for commit in self._upstream_repo.iter_commits(author=email, number=1):
            if commit.author is None:
                print email, commit.commit.author, "https://github.com/buildbot/buildbot/commit/" + commit.sha
                q = 'fullname:"{}"'.format(commit.commit.author['name'])
                result = list(self._gh.search_users(q))
                if len(result) == 1:
                    gh_user = result[0].user.login
                else:
                    print " ".join([r.user.login for r in result]), "possibilities"
                self.wait_rate_limits()
            else:
                gh_user = commit.author.login
        if gh_user is not None:
            print "found mapping for", email, ":", gh_user
            self._users[email] = gh_user
            return gh_user
        print "email not found in repositorie's authors", email
        return None

    def find_users(self, emails):
        not_mapped_users = []
        for email in emails:
            q = '{} in:email'.format(email)
            result = list(self._gh.search_users(q))
            if len(result) == 1:
                gh_user = result[0].user.login
                self._users[email] = gh_user
            else:
                not_mapped_users.append(email)
            self.wait_rate_limits()
        return not_mapped_users

    def wait_rate_limits(self):
        for k,v in self._gh.rate_limit()['resources'].items():
            if v['remaining'] < 2:
                print("waiting one minute for rate limiting reasons..", k)
                time.sleep(60)

    def get_user(self, user):
        """
        transform the given id to a github username if it's an public e-mail

        cache results
        take into account provided mapping
        """
        if user is None:
            return user

        gh_user = self._users.get(user, None)

        if gh_user is None and not self._only_from_cache:
            gh_user = self._mapping.get(user, user)

            if gh_user.find('@') > 0:
                result = list(self._gh.search_users('{} in:email'.format(gh_user)))
                if len(result) == 1:
                    gh_user = '@{}'.format(result[0].user.login)

            self._users[user] = gh_user

        return gh_user

    def _user_display(self, user):
        gh_user = self.get_user(user)

        if not gh_user:
            gh_user = "unknown_contributor"

        if gh_user[0] == '@':
            if self._mention_people:
                display_user = gh_user  # this will result in a mention
            else:
                display_user = gh_user[1:]
        else:
            parts = gh_user.split('@')

            if len(parts) > 1:     # only first part of the e-mail
                display_user = '`{}@...`'.format(parts[0])
            else:                   # use as is
                if self._mention_people:
                    display_user = '@{}'.format(gh_user) # this will result in a mention
                else:
                    display_user = '`{}`'.format(gh_user)
        return display_user

    def _convert_contributors(self, contributors):
        """
        represent the list of contributors in Markdown
        """
        result = list()

        for user, contributions in contributors.items():
            display_user = self._user_display(self.get_user(user))
            result.append(display_user)
        return ', '.join(result)

    def _format_comments(self, comments):
        comments_text = []
        for comment in comments:
            if comment.get('message'):
                if "Ticket retargeted after milestone closed" not in comment['message']:
                    text = ""
                    text += "_Comment from_: " + self._user_display(self.get_user(comment['author'])) + "\n"
                    text += "_Date_: `" + format_date(comment['time']) + "`\n"
                    text += "\n"
                    text += convert_text(self.get_user(comment['message']))
                    comments_text.append(text)
        return "\n---\n".join(comments_text).encode("ascii", errors='ignore')

    def create_issue(self, ticket):
        """
        create an issue in the given project
        """
        assert isinstance(ticket, dict)
        if self._dry_run:
            return None, None
        res = self._repo.create_issue(
            ticket['summary'],
            body=self._template.format(
                trac_id=ticket['id'], trac_url=ticket['url'],
                users=self._convert_contributors(ticket['contributors']),
                body=ticket['description'],
                creation_date=format_date(ticket['time']),
                modification_date=format_date(ticket['changetime']),
                comments=self._format_comments(ticket['comments'])),
            milestone=self.ensure_milestone(ticket['milestone']))
        return res, res.html_url

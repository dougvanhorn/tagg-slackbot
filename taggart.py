#!/usr/bin/env python3
"""A small bot service to post links in our Slack.
"""

import os
import re
import time
import traceback

from slackclient import SlackClient

import local_settings

# Ticket patterns to watch for.
TT_RE = re.compile(r'(?<!/)TT-\d+', flags=re.IGNORECASE)
DESK_RE = re.compile(r'(?<!/)DESK-\d+', flags=re.IGNORECASE)
JIRA_URL = 'https://tagglogistics.atlassian.net/browse/%s'


BOT_ID = local_settings.BOT_ID
BOT_NAME = local_settings.BOT_NAME
BOT_TOKEN = local_settings.BOT_TOKEN
AT_BOT = '<@%s>' % BOT_ID


def get_bot_data(users=None):
    """Utility to find User IDs.

    Arguments:
        users: [None] a single or list of usernames to lookup

    Returns:
        None
    """
    print('Token: %s' % BOT_TOKEN)

    # Allow for a single user.
    if type(users) == str:
        users = [users]

    if users:
        users = set(users)
    else:
        users = set()

    client = SlackClient(BOT_TOKEN)

    # Get the list of users and print the IDs of the ones requested.
    call = client.api_call('users.list')

    if not call.get('ok'):
        # Meekly submit in the face of failure.
        return

    # Find the bot users.
    slack_users = call.get('members')

    if users:
        # Filter down to the users we're interested in.
        slack_users = (u for u in slack_users if u.get('name', None) in users)

    for user in filtered_users:
        try:
            print('{name}: {id}'.format(**user))

        except KeyError as exc:
            # In case 'name', or 'id' aren't on the user dictionary.
            print('Unexpected user data: %s' % user)

        except Exception as exc:
            # Whaaa?
            traceback.print_exc()


def listener():
    """WebSocket listener main loop.
    """
    READ_WEBSOCKET_DELAY = 1  # 1 second delay reading from the firehose

    client = SlackClient(BOT_TOKEN)

    if not client.rtm_connect():
        print('Connection failed.  Invalid Slack Token or Bot ID.')
        return

    print('Taggart is listening.')
    while True:
        responses = parse_slack_output(client.rtm_read())

        for tickets, channel in responses:
            urls = [JIRA_URL % ticket for ticket in tickets]
            client.api_call('chat.postMessage', channel=channel, text='\n'.join(urls), as_user=True)

        time.sleep(READ_WEBSOCKET_DELAY)



def parse_slack_output(rtm_messages):
    """The Slack Real Time Messaging (RTM) API is an events firehose.

    Loop over the list of RTM messages and return a list of tuples.

    Arguments:
        rtm_messages: a list of RTM dictionaries that are the messages

    Returns:
        A list of 2-tuples containing the found tickets and the channel.  E.g.,

            [(['TT-123'], 'channel_id')]
    """
    messages = (msg for msg in rtm_messages if msg['type'] == 'message' and 'text' in msg)
    responses = []
    for message in messages:
        text = message['text']
        found = []
        found.extend(TT_RE.findall(text))
        found.extend(DESK_RE.findall(text))
        found = [s.upper() for s in found]
        found.sort()

        responses.append((found, message['channel']))

    return responses


def main():
    #get_bot_data(BOT_NAME)
    listener()


if __name__ == '__main__':
    main()


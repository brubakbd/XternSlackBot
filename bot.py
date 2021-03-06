import os
import time
from slackclient import SlackClient
from external_apis import external_api_router
from scrabblebot import scrabblebot
from oyapls import oyapls
from random import randint
from foaas import foaas

from dotenv import load_dotenv, find_dotenv
from heypizza import pizza_bot

load_dotenv(find_dotenv())
BOT_ID = os.environ.get("BOT_ID")
AT_BOT = "<@" + BOT_ID + ">"
admin_id = os.environ.get('ADMIN_TOKEN')

slack_client = SlackClient(os.environ.get('SLACK_API_TOKEN'))
if admin_id:
    admin = SlackClient(admin_id)

team_id = "Not defined yet"

def handle_command(command, channel, send_user, ts):
    scrabble_result = scrabblebot.handle_command(command, channel, send_user, ts, slack_client, admin, admin_id)
    if scrabble_result is None:
        external_result = external_api_router.handle_message(command, channel, send_user, slack_client)
        if external_result is None:
            foaas_result = foaas.handle_command(command, channel, send_user, slack_client, admin, ts)
            if foaas_result is None:
                oya_result = oyapls.handle_message(slack_client, command, channel, send_user)
                if oya_result is None:
                    if command == 'help':
                        display_help(channel)
                    else:
                        slack_client.api_call('chat.postMessage', channel=channel, text = "What?", as_user=True)

def parse_slack_output(slack_rtm_output):
    """
        The Slack Real Time Messaging API is an events firehose.
        this parsing function returns None unless a message is
        directed at the Bot, based on its ID.
    """
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and 'user' in output:
                if BOT_ID == output['user']:
                    return None, None
                if AT_BOT in output['text']:
                    if randint(0,100) == 42:
                        name = ""
                        members = slack_client.api_call('users.list')['members']
                        for member in members:
                            if member['id'].lower() == output['user'].lower():
                                print(member)
                                name = member['profile']['first_name'].title()
                        slack_client.api_call('chat.postMessage', channel=output['channel'], text = "No, fuck off " + name + ".", as_user=True)
                        return None, None
                    # return text after the @ mention, whitespace removed
                    return output['text'].split(AT_BOT)[1].strip().lower(), output['channel'], output['user'], output['ts']
                elif "@" in output['text'] and (":oya" in output['text'] or ":nsfw_oya:" in output['text']):
                    return output['text'].strip().lower(), output['channel'], output['user'], output['ts']
    return None, None

def display_help(channel):
    message = ("```" + 
               "OYA PLS\n" +
                "\toyapls - gives the user a random oya, up to 3 a day.\n" +
                "\t@user_to_check oyas - gives info on how many oyas it has.\n"
                "\t@user_to_gift #ofOyas :oyatype: ... - gift oyas to another user\n"
                "FOAAS\n" +
                "\tfoaas help - Returns a list of unique foaas requests\n" +
                "\tfoaas (foaas command) ... - Utilizes the foaas api and fred says the response\n" +
                "OTHER FEATURES\n" +
                "\tscrabblify - change text to scrabble tiles\n" +
                "\t!trump - get Trump's most recent tweet\n" +
                "\t!puppy - get a random picture from reddit.com/r/puppies\n" + 
                "\t!kitten - get a random picture from reddit.com/r/kittens\n" +
                "\t!cute - get a random picture from reddit.com/r/aww\n" + 
                "\t!love - get a random scenic picture from one of various subreddits\n" +
                "```"
                )
    slack_client.api_call("chat.postMessage", channel=channel, text=message, as_user=True)


if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1  # 1 second delay between reading from firehose
    if slack_client.rtm_connect():
        print("StarterBot connected and running!")
        team_id = slack_client.api_call("team.info")['team']['id']
        while True:
            read_output = slack_client.rtm_read()
            stuff = parse_slack_output(read_output)
            if stuff[0] and stuff[1] and stuff[2] and stuff[3]:
                handle_command(stuff[0], stuff[1], stuff[2], stuff[3])
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")

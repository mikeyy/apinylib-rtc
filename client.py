import logging
import sys
import asyncio
import pinylib

log = logging.getLogger(__name__)


def main():
    room_name = input('Enter room name: ').strip()
    if pinylib.CONFIG.ACCOUNT and pinylib.CONFIG.PASSWORD:
        client = pinylib.TinychatRTCClient(room=room_name, account=pinylib.CONFIG.ACCOUNT,
                                           password=pinylib.CONFIG.PASSWORD)
    else:
        client = pinylib.TinychatRTCClient(room=room_name)

    client.nickname = input('Enter nick name: (optional) ').strip()
    do_login = input('Login? [enter=no] ')

    if do_login:
        if not client.account:
            client.account = input('Account: ').strip()
        if not client.password:
            client.password = input('Password: ')

        is_logged_in = client.login()
        while not is_logged_in:
            client.account = input('Account: ').strip()
            client.password = input('Password: ')
            if client.account == '/' or client.password == '/':
                main()
                break
            elif client.account == '//' or client.password == '//':
                do_login = False
                break
            else:
                is_logged_in = client.login()
        if is_logged_in:
            client.console_write(pinylib.COLOR['bright_green'], f'Logged in as: {client.account}')
        if not do_login:
            client.account = None
            client.password = None

    loop = asyncio.get_event_loop()
    loop.run_until_complete(client.connect())

    while not client.is_connected:
        asyncio.sleep(1)
    # TODO input... :(
    '''
    while client.is_connected:
        chat_msg = input()
        if chat_msg.startswith('/'):
            msg_parts = chat_msg.split(' ')
            cmd = msg_parts[0].lower().strip()
            if cmd == '/q':
                client.disconnect()
            elif cmd == '/a':
                if len(client.users.signed_in) == 0:
                    print ('No signed in users in the room.')
                else:
                    for user in client.users.signed_in:
                        print ('%s:%s' % (user.nick, user.account))
            elif cmd == '/u':
                for user in client.users.all:
                    print ('%s: %s' % (client.users.all[user].nick, client.users.all[user].user_level))
            elif cmd == '/m':
                if len(client.users.mods) == 0:
                    print ('No moderators in the room.')
                else:
                    for mod in client.users.mods:
                        print (mod.nick)
            elif cmd == '/n':
                if len(client.users.norms) == 0:
                    print ('No normal users in the room.')
                else:
                    for norm in client.users.norms:
                        print (norm.nick)
            elif cmd == '/l':
                if len(client.users.lurkers) == 0:
                    print ('No lurkers in the room.')
                else:
                    for lurker in client.users.lurkers:
                        print (lurker.nick)
            elif cmd == '/p':
                if len(msg_parts) >= 2:
                    bot.send_room_password_msg(msg_parts[1])
        else:
            client.send_chat_msg(chat_msg)
        '''


if __name__ == '__main__':
    if pinylib.CONFIG.DEBUG_TO_FILE:
        formater = '%(asctime)s : %(levelname)s : %(filename)s : %(lineno)d : %(funcName)s() : %(name)s : %(message)s'
        logging.basicConfig(filename=pinylib.CONFIG.DEBUG_FILE_NAME,
                            level=pinylib.CONFIG.DEBUG_LEVEL, format=formater)
        log.info('Starting pinylib webrtc version: %s' % pinylib.__version__)
    else:
        log.addHandler(logging.NullHandler())
    # TODO this sucks, ew
    if sys.version_info[:2] != (3,6):
        print(f'apinylib requires Python 3.6.5+, you are using {sys.version}\nEXITING')
        sys.exit()
    else:
        main()

import logging
import asyncio
import pinylib

log = logging.getLogger(__name__)


async def main():
    room_name = input("Enter room name: ").strip()
    if pinylib.CONFIG.ACCOUNT and pinylib.CONFIG.PASSWORD:
        client = pinylib.TinychatRTCClient(
            room=room_name,
            account=pinylib.CONFIG.ACCOUNT,
            password=pinylib.CONFIG.PASSWORD,
            solve_captchas=pinylib.CONFIG.SOLVE_CAPTCHAS
        )
    else:
        client = pinylib.TinychatRTCClient(
            room=room_name,
            solve_captchas=pinylib.CONFIG.SOLVE_CAPTCHAS
        )

    client.nickname = input("Enter nick name: (optional) ").strip()
    do_login = input("Login? [enter=no] ")

    if do_login:
        if not client.account:
            client.account = input("Account: ").strip()
        if not client.password:
            client.password = input("Password: ")

        is_logged_in = await client.login()
        while not is_logged_in:
            client.account = input("Account: ").strip()
            client.password = input("Password: ")
            if client.account == "/" or client.password == "/":
                main()
                break
            elif client.account == "//" or client.password == "//":
                do_login = False
                break
            else:
                is_logged_in = await client.login()
        if is_logged_in:
            print("Logged in as: " + client.account)
        if not do_login:
            client.account = None
            client.password = None

    await client.connect()


if __name__ == "__main__":
    if pinylib.CONFIG.DEBUG_TO_FILE:
        formater = "%(asctime)s : %(levelname)s : %(filename)s : %(lineno)d : %(funcName)s() : %(name)s : %(message)s"
        logging.basicConfig(
            filename=pinylib.CONFIG.DEBUG_FILE_NAME,
            level=pinylib.CONFIG.DEBUG_LEVEL,
            format=formater,
        )
        log.info("Starting pinylib webrtc version: %s" % pinylib.__version__)
    else:
        log.addHandler(logging.NullHandler())
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

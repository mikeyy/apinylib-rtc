import json
import asyncio
import traceback
import logging
import time
import websockets
from colorama import init, Fore, Style
import config

import apis.tinychat
import user
import handler

from page import acc
from util import string_util

# Attempt to follow https://semver.org/
__version__ = "0.2.2"

CONFIG = config
init(autoreset=True)
log = logging.getLogger(__name__)

# TODO make optional
#  Console colors.
COLOR = {
    "white": Fore.WHITE,
    "green": Fore.GREEN,
    "bright_green": Style.BRIGHT + Fore.GREEN,
    "yellow": Fore.YELLOW,
    "bright_yellow": Style.BRIGHT + Fore.YELLOW,
    "cyan": Fore.CYAN,
    "bright_cyan": Style.BRIGHT + Fore.CYAN,
    "red": Fore.RED,
    "bright_red": Style.BRIGHT + Fore.RED,
    "magenta": Fore.MAGENTA,
    "bright_magenta": Style.BRIGHT + Fore.MAGENTA,
}


class TinychatRTCClient(object):
    def __init__(self, room, nickname="", account=None, password=None):
        self.room_name = room
        self.nickname = nickname
        self.account = account
        self.password = password
        self.client_id = 0
        self.is_client_mod = False
        self.is_client_owner = False
        self._init_time = time.time()

        self.handler = handler.Handler()
        self.is_green_room = False
        self.is_connected = False
        self.active_user = None
        self.users = user.Users()
        # JSON string from tinychat.get_connect_info(), contains room token and ws address
        self.connect_info = {}
        self._ws = None
        self._req = 1
        self.is_published = False

    def console_write(self, color, message):
        """
        Writes message to console.

        :param color: the colorama color representation.
        :param message: str the message to write.
        """
        if config.USE_24HOUR:
            ts = time.strftime("%H:%M:%S")
        else:
            ts = time.strftime("%I:%M:%S:%p")
        if config.CONSOLE_COLORS:
            # TODO bit gross this
            msg = f"{COLOR['white']}[{ts}]{Style.RESET_ALL}{color} {message}"
        else:
            msg = f"[{ts}] {message}"
        try:
            print(msg)
        except UnicodeEncodeError as ue:
            log.error(ue, exc_info=True)
            if config.DEBUG_MODE:
                traceback.print_exc()
        # TODO
        # if config.CHAT_LOGGING:
        #    write_to_log('[' + ts + '] ' + message, self.room_name)

    def login(self):
        """
        Login to tinychat.

        :return: True if logged in, else False.
        :rtype: bool
        """
        # TODO this can handle errors better
        account = acc.Account(account=self.account, password=self.password)
        if self.account and self.password:
            if account.is_logged_in():
                return True
            account.login()
        return account.is_logged_in()

    async def connect(self):
        tc_header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-WebSocket-Protocol": "tc",
            "Sec-WebSocket-Extensions": "permessage-deflate",
        }
        # TODO probably move this to its own function?
        self.connect_info = apis.tinychat.get_connect_info(self.room_name)
        # TODO websockets debugging
        async with websockets.connect(
            self.connect_info["endpoint"],
            # TODO extra_headers=tc_header,
            origin="https://tinychat.com",
        ) as self._ws:
            if self._ws.open:
                log.info(f"connecting to: {self.room_name}")
                await self.send_join_msg()
                self.is_connected = True
                await self.__callback()

    async def disconnect(self):
        self.is_connected = False
        await self._ws.close(status=1001, reason="GoingAway")
        self._req = 1
        # TODO this works? don't think so
        sockclosed = await self._ws.closed
        if sockclosed:
            self._ws = None

    async def __callback(self):
        while self.is_connected:
            # I'm ok with this
            # https://github.com/aaugustin/websockets/blob/master/docs/cheatsheet.rst#keeping-connections-open
            try:
                data = await asyncio.wait_for(self._ws.recv(), timeout=30)
            except asyncio.TimeoutError:
                try:
                    pong_waiter = await self._ws.ping()
                    await asyncio.wait_for(pong_waiter, timeout=10)
                except asyncio.TimeoutError:
                    break
            else:
                json_data = json.loads(data)
                log.debug(f"DATA: {data}")
                event = json_data["tc"]
                await self.handler.fire(self, event, json_data)

    async def on_closed(self, code):
        """
        This gets sent when ever the connection gets closed by the server for what ever reason.

        :param code: The close code as integer.
        :type code: int
        """
        self.is_connected = False
        if code == 4:
            self.console_write(
                COLOR["bright_red"], "You have been banned from the room."
            )
        elif code == 5:
            self.console_write(COLOR["bright_red"], f"Reconnect code? {code}")
            # TODO self.reconnect()
        elif code == 6:
            self.console_write(COLOR["bright_red"], "Double account sign in.")
        elif code == 8:
            self.console_write(COLOR["bright_red"], f"Timeout error? {code}")
        elif code == 12:
            self.console_write(
                COLOR["bright_red"], "You have been kicked from the room."
            )
        else:
            self.console_write(
                COLOR["white"], f"Connection was closed, code: {code}"
            )

    async def on_joined(self, client_info):
        """
        Received when the client have joined the room successfully.

        :param client_info: This contains info about the client, such as user role and so on.
        :type client_info: dict
        """
        log.info(f"client info: {client_info}")
        self.client_id = client_info["handle"]
        self.is_client_mod = client_info["mod"]
        self.is_client_owner = client_info["owner"]
        client = self.users.add(client_info)
        client.user_level = 0
        self.console_write(
            COLOR["bright_green"],
            f"Client joined the room: {client.nick}, {client.id}",
        )

        # Not sure if this is the right place for this.
        if self.is_client_mod:
            await self.send_banlist_msg()

    async def on_room_info(self, room_info):
        """
        Received when the client have joined the room successfully.

        :param room_info: This contains information about the room such as about, profile image and so on.
        :type room_info: dict
        """
        if config.DEBUG_MODE:
            # roughly centered for no reason
            self.console_write(
                COLOR["white"], "{:<50}".format("## Room Information ##")
            )
            for k in room_info:
                self.console_write(COLOR["white"], f"{k}, {room_info[k]}")

    async def on_room_settings(self, room_settings):
        """
        Received when a change has been made to the room settings(privacy page).

        Not really sure what role this plays, but it happens when
        a change has been made to the privacy page.

        :param room_settings: The room room settings.
        :type room_settings: dict
        """
        if config.DEBUG_MODE:
            self.console_write(COLOR["white"], "## Room Settings Change ##")
            for k in room_settings:
                self.console_write(COLOR["white"], f"{k}: {room_settings[k]}")

    async def on_userlist(self, user_info):
        """
        Received upon joining a room.

        This contains all the users present in the room when joining.

        :param user_info: A users information such as role.
        :type user_info: dict
        """
        if user_info["handle"] != self.client_id:
            _user = self.users.add(user_info)
            if _user.is_owner:
                _user.user_level = 1
                self.console_write(
                    COLOR["red"],
                    f"Joins room owner: {_user.nick}:{_user.id}:{_user.account}",
                )
            elif _user.is_mod:
                _user.user_level = 3
                self.console_write(
                    COLOR["bright_red"],
                    f"Joins moderator: {_user.nick}:{_user.id}:{_user.account}",
                )
            elif _user.account:
                self.console_write(
                    COLOR["bright_yellow"],
                    f"Joins: {_user.nick}:{_user.id}:{_user.account}",
                )
            else:
                self.console_write(
                    COLOR["cyan"], f"Joins: {_user.nick}:{_user.id}"
                )

    async def on_join(self, join_info):
        """
        Received when a user joins the room.

        :param join_info: This contains user information such as role, account and so on.
        :type join_info: dict
        """
        _user = self.users.add(join_info)
        if _user.account:
            tc_info = apis.tinychat.user_info(_user.account)

            if tc_info is not None:
                _user.tinychat_id = tc_info["tinychat_id"]
                _user.last_login = tc_info["last_active"]

            if _user.is_owner:
                _user.user_level = 1
                self.console_write(
                    COLOR["red"],
                    f"Room owner: {_user.nick}:{_user.id}:{_user.account}",
                )

            elif _user.is_mod:
                _user.user_level = 3
                self.console_write(
                    COLOR["bright_red"],
                    f"Moderator: {_user.nick}:{_user.id}:{_user.account}",
                )
            else:
                self.console_write(
                    COLOR["bright_yellow"],
                    f"{_user.nick}:{_user.id} has account: {_user.account}",
                )
        else:
            self.console_write(
                COLOR["cyan"], f"{_user.nick}:{_user.id} joined the room"
            )

    async def on_nick(self, uid, nick):
        """
        Received when a user changes nick name.

        :param uid: The ID (handle) of the user.
        :type uid: int
        :param nick: The new nick name.
        :type nick: str
        """
        _user = self.users.search(uid)
        old_nick = _user.nick
        _user.nick = nick
        self.console_write(
            COLOR["bright_cyan"], f"{old_nick}:{uid} Changed nick to: {nick}"
        )

    async def on_quit(self, uid):
        """
        Received when a user leaves the room.

        :param uid: The ID (handle) of the user leaving.
        :type uid: int
        """
        _user = self.users.delete(uid)
        if _user is not None:
            self.console_write(
                COLOR["cyan"], f"{_user.nick}:{uid} Left the room."
            )

    async def on_ban(self, ban_info):
        """
        Received when the client bans someone.

        :param ban_info: The ban information such as, if the ban was a success or not.
        :type ban_info: dict
        """
        if ban_info["success"]:
            banned_user = self.users.add_banned_user(ban_info)
            if banned_user.account:
                self.console_write(
                    COLOR["bright_red"],
                    f"{banned_user.nick}:{banned_user.account} was banned from the room.",
                )
            else:
                self.console_write(
                    COLOR["bright_red"],
                    f"{banned_user.nick} was banned from the room.",
                )

    async def on_unban(self, unban_info):
        """
        Received when the client un-bans a user.

        :param unban_info: The un-ban information such as ID (handle) and if un-banned successfully.
        :type unban_info: dict
        """
        unbanned = self.users.delete_banned_user(unban_info)
        if unbanned is not None:
            self.console_write(
                COLOR["green"], f"{unbanned.nick} was unbanned."
            )

    async def on_banlist(self, banlist_info):
        """
        Received when a request for the ban list has been made.

        :param banlist_info: The ban list information such as whether it was a success or not.
        :type banlist_info: dict
        """
        if not banlist_info["success"]:
            self.console_write(COLOR["bright_red"], banlist_info["reason"])
        else:
            if len(banlist_info["items"]) > 0:
                for item in banlist_info["items"]:
                    self.users.add_banned_user(item)
            else:
                self.console_write(COLOR["green"], "The banlist is empty.")

    async def on_msg(self, uid, msg):
        """
        Received when a message is sent to the room.

        :param uid: The message sender's ID (handle).
        :type uid: int
        :param msg: The chat message.
        :type msg: str
        """
        ts = time.time()
        if uid != self.client_id:
            self.active_user = self.users.search(uid)
            await self.message_handler(msg)
            self.active_user.msg_time = ts

    async def message_handler(self, msg):
        """
        A basic handler for chat messages.

        :param msg: The chat message.
        :type msg: str
        """
        # meh
        _msg = msg.replace("\n", " ")
        self.console_write(
            COLOR["bright_green"], f"{self.active_user.nick}: {_msg}"
        )

    async def on_pvtmsg(self, uid, msg):
        """
        Received when a user sends the client a private message.

        :param uid: The ID (handle) of the private message sender.
        :type uid: int
        :param msg: The private message.
        :type msg: str
        """
        ts = time.time()
        if uid != self.client_id:
            self.active_user = self.users.search(uid)
            await self.private_message_handler(msg)
            self.active_user.msg_time = ts

    async def private_message_handler(self, private_msg):
        """
        A basic handler for private messages.

        :param private_msg: The private message.
        :type private_msg: str
        """
        self.console_write(
            COLOR["green"],
            f"Private message from {self.active_user.nick}: {private_msg}",
        )

    async def on_publish(self, uid):
        """
        Received when a user starts broadcasting.

        :param uid: The ID (handle) of the user broadcasting.
        :type uid: int
        """
        _user = self.users.search(uid)
        _user.is_broadcasting = True
        if _user.is_waiting:
            _user.is_waiting = False
        self.console_write(
            COLOR["yellow"], f"{_user.nick}:{uid} is broadcasting."
        )

    async def on_unpublish(self, uid):
        """
        Received when a user stops broadcasting.

        :param uid: The ID (handle) of the user who stops broadcasting.
        :type uid: int
        """
        _user = self.users.search(uid)
        if _user is not None:
            _user.is_broadcasting = False
            self.console_write(
                COLOR["yellow"], f"{_user.nick}:{uid} stopped broadcasting."
            )

    async def on_sysmsg(self, msg):
        """
        System messages sent from the server to all clients (users).

        These messages are notifications about special events, such as ban, kick and possibly others.

        :param msg: The special notifications message.
        :type msg: str
        """
        self.console_write(COLOR["white"], msg)
        if "banned" in msg and self.is_client_mod:
            self.users.clear_banlist()  # eh
            await self.send_banlist_msg()
        if "green room enabled" in msg:
            self.is_green_room = True
        if "green room disabled" in msg:
            self.is_green_room = False

    async def on_password(self):
        """ Received when a room is password protected. """
        self.console_write(
            COLOR["bright_red"],
            "Password protected room. "
            "Use /p to enter password. E.g. /p password123",
        )

    async def on_pending_moderation(self, pending):
        """ Received when a user is waiting in the green room. """
        if not self.is_green_room:
            self.is_green_room = True

        _user = self.users.search(pending["handle"])
        if _user is not None:
            _user.is_waiting = True
            self.console_write(
                COLOR["bright_yellow"],
                f"{_user.nick}:{_user.id} is waiting in the green room.",
            )
        else:
            log.error(
                f"failed to find user info for green room pending user ID: {pending['handle']}"
            )

    async def on_stream_moder_allow(self, moder_data):
        """
        Received when a user has been allowed by the client, to broadcast in a green room.

        :param moder_data: Contains information about the allow request.
        :type moder_data: dict
        """
        _user = self.users.search(moder_data["handle"])
        if _user is not None and config.DEBUG_MODE:
            self.console_write(
                COLOR["bright_yellow"],
                f"{_user.nick}:{_user.id} was allowed to broadcast.",
            )

    async def on_stream_moder_close(self, moder_data):
        """
        Received when a user has their broadcast closed by the client.

        :param moder_data: Contains information about the close request.
        :type moder_data: dict
        """
        if moder_data["success"]:
            _user = self.users.search(moder_data["handle"])
            if _user is not None and config.DEBUG_MODE:
                self.console_write(
                    COLOR["bright_yellow"],
                    f"{_user.nick}:{_user.id}'s broadcast was closed.",
                )
        else:
            log.error(f"failed to close a broadcast: {moder_data['reason']}")

    async def on_captcha(self, key):
        log.debug(f"captcha key: {key}")
        self.console_write(COLOR["bright_red"], "Captcha required!")

    async def on_yut_playlist(self, playlist_data):  # TODO: Needs more work.
        """
        Received when a request for the playlist has been made.

        The playlist is as, one would see if being a moderator
        and using a web browser.

        :param playlist_data: The data of the items in the playlist.
        :type playlist_data: dict
        """
        if not playlist_data["success"]:
            self.console_write(COLOR["red"], playlist_data["reason"])
        else:
            print(playlist_data)

    async def on_yut_play(self, yt_data):
        """
        Received when a youtube gets started or time searched.

        This also gets received when the client starts a youtube, the information is
        however ignored in that case.

        :param yt_data: The event information contains info such as the ID (handle) of the user
        starting/searching the youtube, the youtube ID, youtube time and so on.
        :type yt_data: dict
        """
        user_nick = "n/a"
        if "handle" in yt_data:
            if yt_data["handle"] != self.client_id:
                _user = self.users.search(yt_data["handle"])
                user_nick = _user.nick

        if yt_data["item"]["offset"] == 0:
            # the video was started from the start.
            self.console_write(
                COLOR["bright_magenta"],
                f"{user_nick} started youtube video ({yt_data})",
            )
        elif yt_data["item"]["offset"] > 0:
            # the video was searched while still playing.
            self.console_write(
                COLOR["bright_magenta"],
                f"{user_nick} searched the youtube video to: {int(round(yt_data['item']['offset']))}",
            )

    async def on_yut_pause(self, yt_data):
        """
        Received when a youtube gets paused or searched while paused.

        This also gets received when the client pauses or searches while paused, the information is
        however ignored in that case.

        :param yt_data: The event information contains info such as the ID (handle) of the user
        pausing/searching the youtube, the youtube ID, youtube time and so on.
        :type yt_data: dict
        """
        user_nick = "n/a"
        if "handle" in yt_data:
            if yt_data["handle"] != self.client_id:
                _user = self.users.search(yt_data["handle"])
                user_nick = _user.nick

        self.console_write(
            COLOR["bright_magenta"],
            f"{user_nick} paused the video at {int(round(yt_data['item']['offset']))}",
        )

    async def on_yut_stop(self, yt_data):
        """
        Received when a youtube stops, e.g when its done playing.

        :param yt_data: The event information contains the ID of the video, the time and so on.
        :type yt_data: dict
        """
        self.console_write(
            COLOR["bright_magenta"],
            f"The youtube ({yt_data['item']['id']}) was stopped.",
        )

    async def send_join_msg(self):
        """
        The initial connect message to the room.

        The client sends this after the websocket handshake has been established.

        :return: Returns True if the connect message has been sent, else False.
        :rtype: bool
        """
        if not self.nickname:
            self.nickname = string_util.create_random_string(3, 20)
        rtc_version = apis.tinychat.rtc_version(self.room_name)
        log.info(f"tinychat rtc version: {rtc_version}")
        if rtc_version is None:
            rtc_version = config.FALLBACK_RTC_VERSION
            log.info(
                f"failed to parse rtc version, using fallback: {config.FALLBACK_RTC_VERSION}"
            )

        token = self.connect_info["result"]
        if token is not None:
            payload = {
                "tc": "join",
                "useragent": f"tinychat-client-webrtc-undefined_win32-{rtc_version}",
                "token": token,
                "room": self.room_name,
                "nick": self.nickname,
            }
            await self.send(payload)
            return True
        else:
            log.info(f"Token request failed\ntoken={token}")
            return False

    async def set_nick(self):
        """ Send a nick message. """
        payload = {"tc": "nick", "nick": self.nickname}
        await self.send(payload)

    async def send_chat_msg(self, msg):
        """
        Send a chat message to the room.

        :param msg: The message to send.
        :type msg: str
        """
        payload = {"tc": "msg", "text": msg}
        await self.send(payload)

    async def send_private_msg(self, uid, msg):
        """
        Send a private message to a user.

        :param uid: The Id (handle) of the user to send the message to.
        :type uid: int
        :param msg: The private message to send.
        :type msg: str
        """
        payload = {"tc": "pvtmsg", "text": msg, "handle": uid}
        await self.send(payload)

    async def send_kick_msg(self, uid):
        """
        Send a kick message to kick a user out of the room.

        :param uid: The ID (handle) of the user to kick.
        :type uid: int
        """
        payload = {"tc": "kick", "handle": uid}
        await self.send(payload)

    async def send_ban_msg(self, uid):
        """
        Send a ban message to ban a user from the room.

        :param uid: The ID (handle) of the user to ban.
        :type uid: int
        """
        payload = {"tc": "ban", "handle": uid}
        await self.send(payload)

    async def send_unban_msg(self, ban_id):
        """
        Send a un-ban message to un-ban a banned user.

        :param ban_id: The ban ID of the user to un-ban.
        :type ban_id: int
        """
        payload = {"tc": "unban", "id": ban_id}
        await self.send(payload)

    async def send_banlist_msg(self):
        """ Send a banlist request message. """
        payload = {"tc": "banlist"}
        await self.send(payload)

    async def send_room_password_msg(self, password):
        """
        Send a room password message.

        :param password: The room password.
        :type password: str
        """
        payload = {"tc": "password", "password": password}
        await self.send(payload)

    async def send_cam_approve_msg(self, uid):
        """
        Allow a user to broadcast in green room enabled room.

        :param uid: The ID of the user.
        :type uid: int
        """
        payload = {"tc": "stream_moder_allow", "handle": uid}
        await self.send(payload)

    async def send_close_user_msg(self, uid):
        """
        Close a users broadcast.

        :param uid: The ID of the user.
        :type uid: int
        """
        payload = {"tc": "stream_moder_close", "handle": uid}
        await self.send(payload)

    async def send_captcha(self, token):
        """
        Send the captcha token.

        :param token: The captcha response token.
        :type token: str
        """
        payload = {"tc": "captcha", "token": token}
        await self.send(payload)

    # Media.
    async def send_yut_playlist(self):
        """ Send a youtube playlist request. """
        payload = {"tc": "yut_playlist"}
        await self.send(payload)

    async def send_yut_playlist_add(self, video_id, duration, title, image):
        """
        Add a youtube to the web browser playlist.

        I haven't explored this yet.

        :param video_id: the ID of the youtube video.
        :type video_id: str
        :param duration: The duration of the youtube video (in seconds).
        :type duration: int
        :param title: The title of the youtube video.
        :type title: str
        :param image: The thumbnail image url of the video.
        :type image: str
        """
        payload = {
            "tc": "yut_playlist_add",
            "item": {
                "id": video_id,
                "duration": duration,
                "title": title,
                "image": image,
            },
        }
        await self.send(payload)

    async def send_yut_playlist_remove(self, video_id, duration, title, image):
        """
        Remove a playlist item from the web browser based playlist.

        I haven't explored this yet.

        :param video_id: The ID of the youtube video to remove.
        :type video_id: str
        :param duration: The duration of the youtube video to remove.
        :type duration: int | float
        :param title: The title of the youtube video to remove.
        :type title: str
        :param image: The thumbnail image url of the youtube video to remove.
        :type image: str
        """
        payload = {
            "tc": "yut_playlist_remove",
            "item": {
                "id": video_id,
                "duration": duration,
                "title": title,
                "image": image,
            },
        }
        await self.send(payload)

    async def send_yut_playlist_mode(self, random_=False, repeat=False):
        """
        Set the mode of the web browser based playlist.

        I haven't explored this yet.

        :param random_: Setting this to True will make videos play at random i assume.
        :type random_: bool
        :param repeat: Setting this to True will make the playlist repeat itself i assume.
        :type repeat: bool
        """
        payload = {
            "tc": "yut_playlist_mode",
            "mode": {"random": random_, "repeat": repeat},
        }
        await self.send(payload)

    async def send_yut_play(self, video_id, duration, title, offset=0):
        """
        Start or search a youtube video.

        :param video_id: The ID of the youtube video to start or search.
        :type video_id: str
        :param duration: The duration of the video in seconds.
        :type duration: int | float
        :param title: The title of the youtube.
        :type title: str
        :param offset: The offset seconds to start the video at in the case of doing a search.
        :type offset: int | float
        """
        payload = {
            "tc": "yut_play",
            "item": {
                "id": video_id,
                "duration": duration,
                "offset": offset,
                "title": title,
            },
        }
        # TODO what
        if offset != 0:
            del payload["item"]["title"]
            payload["item"]["playlist"] = False
            payload["item"]["seek"] = True

        await self.send(payload)

    async def send_yut_pause(self, video_id, duration, offset=0):
        """
        Pause, or search while a youtube video is paused .

        :param video_id: The ID of the youtube video to pause or search.
        :type video_id: str
        :param duration: The duration of the video in seconds.
        :type duration: int |float
        :param offset: The offset seconds to pause the video at in case of doing seach while in pause.
        :type offset: int |float
        """
        payload = {
            "tc": "yut_pause",
            "item": {"id": video_id, "duration": duration, "offset": offset},
        }
        await self.send(payload)

    async def send_yut_stop(self, video_id, duration, offset=0):
        """
        Stop a youtube video that is currently playing.

        As far as i see, this is not yet officially supported by tinychat.
        There simply is no button to stop a youtube with in the browser based client. (as of version 2.0.10-296)

        :param video_id: The ID of the youtube to stop.
        :type video_id: str
        :param duration: The duration of the youtube video in seconds.
        :type duration: int | float
        :param offset: The offset seconds when the youtube gets stopped.
        :type offset: int |float
        """
        payload = {
            "tc": "yut_stop",
            "item": {"id": video_id, "duration": duration, "offset": offset},
        }
        await self.send(payload)

    async def send(self, payload):
        _payload = json.dumps(payload)
        await self._ws.send(_payload)
        self._req += 1
        log.debug(f"{_payload}")

    def get_runtime(self, as_milli=False):
        """
        Get the time the connection has been alive.

        :param as_milli: True return the time as milliseconds, False return seconds.
        :type as_milli: bool
        :return: Seconds or milliseconds.
        :rtype: int
        """
        up = int(time.time() - self._init_time)
        if as_milli:
            return up * 1000
        return up

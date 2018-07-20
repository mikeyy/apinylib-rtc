#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Chat events handler module"""

import time


class UnhandledEvent(Exception):
    pass


class EventHandler(object):
    async def fire(self, client, event, var=None):
        if hasattr(self, event):
            await getattr(self, event)(client, var)
        else:
            print(UnhandledEvent(f"{event} not handled"))


class Handler(EventHandler):

    async def ping(self, client, var):
        await client.send({'tc': 'pong'})

    async def closed(self, client, var):
        await client.on_closed(var['error'])

    async def joined(self, client, var):
        await client.on_joined(var['self'])
        await client.on_room_info(var['room'])

    async def room_settings(self, client, var):
        await client.on_room_settings(var['room'])
    
    async def userlist(self, client, var):
        for _user in var['users']:
            await client.on_userlist(_user)

    async def join(self, client, var):
        await client.on_join(var)
    
    async def nick(self, client, var):
        await client.on_nick(var['handle'], var['nick'])

    async def quit(self, client, var):
        await client.on_quit(var['handle'])

    async def ban(self, client, var):
        await client.on_ban(var)
        
    async def unabn(self, client, var):
        await client.on_unban(var)

    async def banlistmsg(self, client, var):
        await client.on_banlist(var)
    
    async def msg(self, client, var):
        await client.on_msg(var['handle'], var['text'])

    async def pvtmsg(self, client, var):
        await client.on_pvtmsg(var['handle'], var['text']) 
   
    async def publish(self, client, var):
        await client.on_publish(var['handle'])

    async def unpublish(self, client, var):
        await client.on_unpublish(var['handle'])

    async def sysmsg(self, client, var):
        await client.on_sysmsg(var['text'])

    async def password(self, client, var):
        await client.on_password()

    async def pending_moderation(self, client, var):
        await client.on_pending_moderation(var)

    async def stream_moder_allow(self, client, var):
        await client.on_stream_moder_allow(var)
    
    async def captcha(self, client, var):
        await client.on_captcha(var['key'])

    async def yut_playlist(self, client, var):
        await client.on_yut_playlist(var)

    async def yut_play(self, client, var):
        await client.on_yut_play(var)

    async def yut_pause(self, client, var):
        await client.on_yut_pause(var)

    async def yut_stop(self, client, var):
        await client.on_yut_stop(var)

    async def iceservers(self, client, var):
        pass
        
    async def stream_connected(self, client, var):
        pass
        
    async def stream_closed(self, client, var):
        pass
    
    async def sdp(self, client, var):
        pass


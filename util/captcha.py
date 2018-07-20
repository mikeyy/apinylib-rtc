#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Captcha solving module"""

import asyncio
import aiohttp
import json
import time

# I couldn't force myself to use utl.web - sorry 
async def post_request(url, data=None, json=None, timeout=180):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(
                url, data=data, json=json, timeout=timeout
            ) as r:
                return await r.text()
        except BaseException as e:
            raise e


async def get_request(url, data=None, json=None, timeout=180):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(
                url, data=data, json=json, timeout=timeout
            ) as r:
                return await r.text()
        except BaseException as e:
            raise e


class AntiCaptcha(object):
    def __init__(self, api_key):
        self.api_url = "http://api.anti-captcha.com/"
        self.api_key = api_key

    async def get_balance(self):
        fields = {"clientKey": self.api_key}
        response = await post_request(
            f"{self.api_url}/getBalance", json=fields
        )
        errorId = int(response["errorId"])
        if errorId > 1:
            return
        balance = response["balance"]
        return balance

    async def solve_captcha(self, sitekey, pageurl):
        payload = {
            "clientKey": self.api_key,
            "task": {
                "type": "NoCaptchaTaskProxyless",
                "websiteURL": pageurl,
                "websiteKey": sitekey,
            },
            "softId": 0,
            "languagePool": "en",
        }
        response = await post_request(
            f"{self.api_url}/createTask", json=payload
        )
        j = json.loads(response)
        errorId = int(j["errorId"])
        if errorId > 1:
            return
        taskId = j["taskId"]
        payload = {"clientKey": self.api_key, "taskId": taskId}
        await asyncio.sleep(10)
        while 1:
            response = await post_request(
                f"{self.api_url}/getTaskResult", json=payload
            )
            j = json.loads(response)
            if j["status"] == "processing":
                await asyncio.sleep(5)
            elif errorId > 1:
                return
            else:
                break
            await asyncio.sleep(1)
        return j["solution"]["gRecaptchaResponse"]

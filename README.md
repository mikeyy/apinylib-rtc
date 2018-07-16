## aPinylib-RTC

WebRTC module for tinychat chat rooms.

This is a fork of [pinylib-rtc](https://github.com/nortxort/pinylib-rtc/)
using [a library](https://github.com/aaugustin/websockets) developed *on top of* 
[asyncio](https://docs.python.org/3.6/library/asyncio.html); Python's asynchronous framework.

The goal of this project is to alleviate some existing issues with the previous pinylib-rtc library.
Hopefully gaining a decent increase in performance along the way.
This is also a learning experience for myself to get familiarized with some of the features in 
Python 3.6.5+ (including asyncio).

## Bit of Info
This has been tested on Windows 10 64bit using Python 3.6.5, and GNU/Linux using Python 3.6.6.

Atleast **Python 3.6.5 is required**.
Besides the changes needed for [websockets](https://github.com/aaugustin/websockets),
a few other things of note have changed that either update to work with
Tinychat today or to take advantage of Python 3.
* Updated to Python 3
* [`get_connect_token()`](https://github.com/nortxort/pinylib-rtc/blob/master/apis/tinychat.py#L22) has been
replaced by `get_connect_info()`, this now returns just the JSON
* Usage of string formating with `f'{somevariable} and some text'`
* We now just `pong` immediately
    ```py
    if event == 'ping':
        await self.send({'tc': 'pong'})
    ```
* request count sent in each payload was removed. Doesn't appear to be needed

Alot of functions outside of `pinylib.py` are unchanged, for now.


## Known issues
This is in the very early stages and there are a ton of things that do not play nicely with asyncio
and need to be reimplemented.  
* **No console input!  ...yet**
* Chat logging to file disabled
* Header to send to TC's websocket server is not implemented
* Disconnect probably doesn't work :D
* Reconnect is not implemented
* No idea how external requests are effecting the event loop (probably not well)
* `https://tinychat.com/api/tcinfo?username=`?

### Requirements
* Python 3.6.5+
* [websockets](https://github.com/aaugustin/websockets)
* [requests](https://github.com/kennethreitz/requests)
* [colorama](https://github.com/tartley/colorama)
* [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)

`pipenv install`  
Alternatively: `pip3 install websockets requests colorama beautifulsoup4`

## License
```
The MIT License (MIT)
Copyright (c) 2017 Notnola
Copyright (c) 2017 Nortxort
Copyright (c) 2018 Aida

Permission is hereby granted, free of charge, to any person obtaining a copy of this software
and associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice
shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, 
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. 
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, 
DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, 
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

## Acknowledgments
*Thanks to the following people who did 98% of the work*

* [**notnola** *But Probably Nola*](https://github.com/notnola)
* [**Nortxort The Beautiful**](https://github.com/nortxort/)



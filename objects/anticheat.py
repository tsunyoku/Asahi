from . import glob
from constants.regexes import osu_ver
from .player import Player

class Anticheat:
    __slots__ = ('ver', 'adapters', 'player', 'headers', 'stream')
    def __init__(self, **kwargs) -> None:
        self.ver: int = kwargs.get('osuver')
        self.adapters: dict = kwargs.get('adapters')
        self.player: Player = kwargs.get('player')
        self.headers: dict = kwargs.get('headers')

        self.stream: str = 'stable40' # will be default stream if not ce etc.

    async def multi_check(self) -> None:
        if not self.adapters:
            return # no adapters??

        mac = self.adapters['mac_address']
        uninstall = self.adapters['uninstall_id']
        disk = self.adapters['disk_serial']
        ip = self.adapters['ip']

        mac_check = await glob.db.fetchval('SELECT uid FROM user_hashes WHERE mac_address = %s AND uid != %s', [mac, self.player.id])
        if mac_check:
            og = await Player.from_sql(mac_check)

            await self.player.ban(reason=f'Multiaccount of user {og.name}', fr=glob.bot)
            await og.ban(reason=f'Multiaccounting (user {self.player.name})', fr=glob.bot)

        uid_check = await glob.db.fetchval('SELECT uid FROM user_hashes WHERE uninstall_id = %s AND uid != %s', [uninstall, self.player.id])
        if uid_check:
            og = await Player.from_sql(uid_check)

            await self.player.ban(reason=f'Multiaccount of user {og.name}', fr=glob.bot)
            await og.restrict(reason=f'Multiaccounting (user {self.player.name})', fr=glob.bot)

        disk_check = await glob.db.fetchval('SELECT uid FROM user_hashes WHERE disk_serial = %s AND uid != %s', [disk, self.player.id])
        if disk_check and disk != 'runningunderwine':
            og = await Player.from_sql(disk_check)

            await self.player.ban(reason=f'Multiaccount of user {og.name}', fr=glob.bot)
            await og.restrict(reason=f'Multiaccounting (user {self.player.name})', fr=glob.bot)

        ip_check = await glob.db.fetchval('SELECT uid FROM user_hashes WHERE ip = %s AND uid != %s', [ip, self.player.id])
        if ip_check:
            og = await Player.from_sql(ip_check)

            await self.player.flag(reason=f'Flagged with same IP as {og.name}', fr=glob.bot)
            await og.flag(reason=f'Flagged with same IP as {self.player.name}', fr=glob.bot)

        await glob.db.execute(
            'INSERT INTO user_hashes (uid, mac_address, uninstall_id, disk_serial, ip) '
            'VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE occurrences = occurrences + 1',
            [self.player.id, mac, uninstall, disk, ip]
        )

    async def client_check(self) -> bool:
        if not self.ver or any(v in self.ver for v in ('ainu', 'skooter')) or 'ainu' in self.headers:
            return await self.player.restrict(reason='Modified client', fr=glob.bot)

        matched_ver = osu_ver.match(self.ver)

        if not matched_ver:
            return await self.player.restrict(reason='Modified client', fr=glob.bot)

        self.ver = matched_ver

        if (stream := self.ver['stream']):
            self.stream = stream

        if not (real_md5 := glob.cache['vers'].get(self.ver)):
            subver = self.ver.get('subver')

            async with glob.web.get(f'https://osu.ppy.sh/api/v2/changelog') as update_req:
                data = await update_req.json()

                for file_info in data:
                    if file_info['name'] == self.stream: # found osu client's info, let's check it
                        latest_ver = ver['latest_build']['version']
                        break

            glob.cache['latest_ver'][self.stream] = latest_ver
            if (self.ver['ver'] + self.ver.get('subver', '')) != latest_ver: return False
            return True

    async def version_check(self) -> bool: # only for update check
        return self.ver['ver'] + self.ver.get('subver', '') != glob.cache['latest_ver'][self.stream]

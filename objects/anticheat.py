from . import glob
from constants.regexes import osu_ver
from .player import Player

class Anticheat:
    def __init__(self, **info):
        self.ver: int = info.get('osuver')
        self.adapters: dict = info.get('adapters')
        self.player: Player = info.get('player')
        self.headers: dict = info.get('headers')
        
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
            self.stream = self.ver['stream']

        if not (real_md5 := glob.cache['vers'].get(self.ver)):
            year = self.ver['ver'][0:4]
            month = self.ver['ver'][4:6]
            day = self.ver['ver'][6:8]
            formatted_date = f'{year}-{month}-{day}' # we need this to match date against the api

            async with glob.web.get(f'https://osu.ppy.sh/web/check-updates.php?stream={self.stream}&action=check') as update_req:
                data = await update_req.json()

                for file_info in data:
                    if file_info['filename'] == 'osu!.exe': # found osu client's info, let's check it
                        latest_md5 = file_info['file_hash'] # we know this will be the latest version for this stream
                        date = file_info['timestamp'].split(' ')[0] # we don't want the time, only the date
                        latest_ver = date.replace('-', '') # we know this will be the latest version for this stream

                        if date == formatted_date:
                            real_md5 = file_info['file_hash']

                        break

            glob.cache['latest_ver'][self.stream] = {'md5': latest_md5, 'ver': latest_ver}
            if not real_md5: # not latest version, we'll just return False so it can enforce an update
                return False

            glob.cache['vers'][self.ver] = real_md5 # even if they aren't on latest, let's store the md5 for the version they're running

        if self.adapters['osu_md5'] != real_md5:
            await self.player.restrict(reason='Modified client', fr=glob.bot)
            return True # we'll skip version check if they are restricted from this, else they won't be notified and end up in infinite loop
        
        return False # nothing found
            
    async def version_check(self) -> bool: # only for update check, modified client check above
        # oooooooooooo this is ugly!
        latest_md5 = self.adapters['osu_md5'] == glob.cache['latest_ver'][self.stream]['md5']
        latest_ver = self.ver['ver'] == glob.cache['latest_ver'][self.stream]['ver']

        if not latest_md5 or not latest_ver:
            return True
        
        return False
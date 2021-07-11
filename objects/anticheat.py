from . import glob
from constants.regexes import osu_ver
from .player import Player

class Anticheat:
    def __init__(self, **info):
        self.ver: int = info.get('osuver', None)
        self.adapters: dict = info.get('adapters', None)
        self.player: Player = info.get('player', None)
        self.headers: dict = info.get('headers', None)
        
        self.stream: str = ''
        
    async def multi_check(self):
        if not self.adapters:
            return # no adapters??
        
        mac = self.adapters['mac_address']
        uninstall = self.adapters['uninstall_id']
        disk = self.adapters['disk_serial']
        ip = self.adapters['ip']
        
        mac_check = await glob.db.fetchval('SELECT uid FROM user_hashes WHERE mac_address = $1 AND uid != $2', mac, self.player.id)
        if mac_check:
            og = await Player.from_sql(mac_check)
            
            await self.player.ban(reason=f'Multiaccount of user {og.name}', fr=glob.bot)
            await og.ban(reason=f'Multiaccounting (user {self.player.name})', fr=glob.bot)

        uid_check = await glob.db.fetchval('SELECT uid FROM user_hashes WHERE uninstall_id = $1 AND uid != $2', uninstall, self.player.id)
        if uid_check:
            og = await Player.from_sql(uid_check)

            await self.player.ban(reason=f'Multiaccount of user {og.name}', fr=glob.bot)
            await og.restrict(reason=f'Multiaccounting (user {self.player.name})', fr=glob.bot)

        disk_check = await glob.db.fetchval('SELECT uid FROM user_hashes WHERE disk_serial = $1 AND uid != $2', disk, self.player.id)
        if disk_check and disk != 'runningunderwine':
            og = await Player.from_sql(disk_check)

            await self.player.ban(reason=f'Multiaccount of user {og.name}', fr=glob.bot)
            await og.restrict(reason=f'Multiaccounting (user {self.player.name})', fr=glob.bot)

        ip_check = await glob.db.fetchval('SELECT uid FROM user_hashes WHERE ip = $1 AND uid != $2', ip, self.player.id)
        if ip_check:
            og = await Player.from_sql(ip_check)

            await self.player.flag(reason=f'Flagged with same IP as {og.name}', fr=glob.bot)
            await og.flag(reason=f'Flagged with same IP as {self.player.name}', fr=glob.bot)
            
        try:
            await glob.db.execute(
                f'INSERT INTO user_hashes ("uid", "mac_address", "uninstall_id", "disk_serial", "ip") '
                'VALUES ($1, $2, $3, $4, $5)',
                self.player.id, mac, uninstall, disk, ip
            )
        except Exception:
            await glob.db.execute(
                f'UPDATE user_hashes SET occurrences = occurrences + 1 WHERE '
                'mac_address = $1 AND uninstall_id = $2 AND disk_serial = $3 AND ip = $4 AND uid = $5',
                mac, uninstall, disk, ip, self.player.id
            )

    async def client_check(self):
        if any(v in self.ver for v in ('ainu', 'skooter')) or 'ainu' in self.headers or not osu_ver.match(self.ver):
            return await self.player.restrict(reason='Modified client', fr=glob.bot)

        int_ver = self.ver.replace('b', '') # not int if cuttingedge, but we want stream anyways
        try:
            extra_ver = int_ver.split('.')[1] # jfc
            release_ver = extra_ver[1:]
        except IndexError: # no extra ver
            extra_ver = 0
            release_ver = int_ver[8:] # version has to be 8 in length

        if not release_ver:
            release_ver = 'stable40'

        self.stream = release_ver

        if not (true_md5 := glob.cache['vers'].get(self.ver)):
            year = int_ver[:4]
            month = int_ver[4:6]
            day = int_ver[6:8]

            formatted_date = f'{year}-{month}-{day}'

            async with glob.web.get(f'https://osu.ppy.sh/web/check-updates.php?stream={release_ver}&action=check') as update_req:
                data = await update_req.json()

                for finfo in data:
                    if finfo['filename'] == 'osu!.exe':
                        latest_md5 = finfo['file_hash']
                        date = finfo['timestamp'].split(' ')[0]
                        if date == formatted_date:
                            true_md5 = finfo['file_hash']

                        break
                else:
                    true_md5 = self.adapters['osu_md5'] # gonna have to trust the client i guess, this shouldn't happen as asahi will force the latest version anyways

            glob.cache['vers'][self.ver] = true_md5
            glob.cache['latest_ver'][self.stream] = latest_md5

        if self.adapters['osu_md5'] != true_md5:
            await self.player.restrict(reason='Modified client', fr=glob.bot)
            return True # we'll skip version check if they are restricted from this, else they won't be notified and end up in infinite loop
        
        return False # nothing found
            
    async def version_check(self): # only for update check, modified client check above
        if self.adapters['osu_md5'] != glob.cache['latest_ver'][self.stream]:
            return True
        
        return False
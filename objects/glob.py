import config # indirect use of config

db: 'AsyncSQLPool' # type hinting
version: 'Version' # once again, type hinting
web: 'ClientSession'

packets: dict['Packets', 'BanchoPacket']

# cache some things like bcrypt for speeeeeeeeeeeeeeeeeed hours
cache = {
    'bcrypt': {} # store bcrypt pws for speed hours
}

players = {} # player dict | player[token] = player
players_name = {} # playername dict | player[name] = player
players_id = {} # playerid dict | player[id] = player

bot: 'Player'
reader = None

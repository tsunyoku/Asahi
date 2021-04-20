import config # indirect use of config

db: 'AsyncSQLPool' # type hinting
version: 'Version' # once again, type hinting

packets: dict['Packets', 'BanchoPacket']

# cache some things like bcrypt for speeeeeeeeeeeeeeeeeed hours
cache = {
    'bcrypt': {} # store bcrypt pws for speed hours
}

players = {} # player dict | player[token] = player
players_name = {} # playername dict | player[name] = token

bot: 'Player'

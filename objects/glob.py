import config # indirect use of config

db: 'AsyncSQLPool' # type hinting
version: 'Version' # once again, type hinting

packets: dict['Packets', 'BanchoPacket']

# cache some things like bcrypt for speeeeeeeeeeeeeeeeeed hours
cache = {
    'bcrypt': {}, # store bcrypt pws for speed hours
    'user': {} # temporarily used to cache tokens until we have a player object
}
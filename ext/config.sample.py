# postgres auth info
postgres = {
    'db': 'asahi',
    'host': 'localhost',
    'password': 'ape',
    'user': 'tsunyoku'
}

# redis auth info
redis = {
    'host': 'localhost',
    'db': 0, # there's no reason why this shouldn't be 0, only change it if you are certain
    'password': '' # unless you manually edited the config, this will always be blank
}

# where the socket (unix or inet4) should be stored (for nginx & asahi to communicate, you will need to edit this in your nginx config also)
socket = '/tmp/asahi.sock' # ('localhost', port) if you want to use ports over unix sockets

debug = False # debug is used to print more info & help to debug if you are experiencing issues with the server

domain = 'tsunyoku.xyz' # domain for accepting requests
menu_url = 'https://tsunyoku.xyz' # url to redirect to when clicking menu image
menu_image = 'https://a.iteki.pw/1' # change link to image you'd like to display on the main menu; must be jpg/jpeg or png

menu_bgs = [] # list of seasonal backgrounds to display on osu menu | you can list as many as you want like so ['url1', 'url2', 'etc...'] and it will cycle through

api_key = '' # osu api key for map info, can be obtained at https://old.ppy.sh/p/api

# prefix for ingame cmds
prefix = '!'

# prefix for discord bot cmds
bot_prefix = '!'

# discord bot token
token = ''

# NOTE: i would recommend not disabling this unless you are using asahi for a cheat server as this removes any form of anticheat (client checks, replay checks, pp cap etc.)
anticheat = True

webhooks = { # you can leave the urls empty if you don't want to use them!
    'logs': '', # server-related logs
    'anticheat': '' # anticheat-related logs (user bans/flags from client/replay checks, pp cap or hardware matches) - only used if anticheat option is enabled
}

pp_caps = (
    600, # vanilla std
    None, # vanilla taiko
    None, # vanilla catch
    None, # mania
    
    1400, # rx std
    None, # rx taiko
    None, # rx catch

    1200 # autopilot std
)

# these are used for osu!direct mirror. i understand some people may find this sketchy but the entire code is open source so you can see what is using it.
# the only place these are used are in endpoints/web.py, but feel free to check if you are worried.
# obviously, if you don't want to provide these then you can just edit the code to use a beatmap mirror instead
bancho_username = ''
bancho_hashed_password = '' # md5 hash of your password, you can generate an md5 hash here: https://www.md5hashgenerator.com/

# if you have switched to asahi from another source with asahi's migrator, you will need to enable this.
# other server sources use bcrypt, while we dont: this will handle conversion from bcrypt to our format for you if it is enabled.
server_migration = False
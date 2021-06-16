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

# where the socket should be stored (for nginx & asahi to communicate, you will need to edit this in your nginx config also)
socket = '/tmp/asahi.sock'

debug = False # debug is used to print more info & help to debug if you are experiencing issues with the server

domain = 'tsunyoku.xyz' # domain for accepting requests
menu_url = 'https://tsunyoku.xyz' # url to redirect to when clicking menu image
menu_image = 'https://a.iteki.pw/1' # change link to image you'd like to display on the main menu; must be jpg/jpeg or png

menu_bgs = [] # list of seasonal backgrounds to display on osu menu | you can list as many as you want like so ['url1', 'url2', 'etc...'] and it will cycle through

api_key = '' # osu api key for map info, can be obtained at https://old.ppy.sh/p/api

# prefix for discord bot cmds
bot_prefix = '!'

# discord bot token
token = ''
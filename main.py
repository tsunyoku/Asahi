# external imports (some may require to be installed, install using ext/requirements.txt)
from quart import Quart, Response, request # web server :blobcowboi:
from cmyui import AsyncSQLPool, log # import console logger (cleaner than print) and database handler
import pyfiglet

# internal imports
from objects import glob # glob = global, server-wide objects will be stored here e.g database handler

app = Quart(__name__) # handler for webserver :D
glob.db = AsyncSQLPool() # define db globally

@app.before_serving
async def connect() -> None: # ran before server startup, used to do things like connecting to mysql :D | "-> None" to specify we don't want to return anything
    await glob.db.connect(glob.config.mysql) # connect to db using config :p

@app.route("/", methods=['GET']) # only accept GET requests as POST is for login method, see login method below
async def root():
    message = f"{pyfiglet.figlet_format('Asahi')}\n\ntsunyoku attempts bancho v2, gone right :sunglasses:"
    return Response(message, mimetype='text/plain')

if __name__ == '__main__':
    app.run(port=glob.config.port, debug=glob.config.debug) # start web server on port provided & with debug if necessary
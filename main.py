from aiohttp import web, BasicAuth
import asyncio
import aiofiles
import aiosqlite
from time import strftime, gmtime, sleep
import os
import config
import xmltodict
import code_builder


WORKDIR = os.getcwd()
ROOT = config.server_prop['base_dir']
PORT = config.server_prop['port']
TIMEOUT = config.server_prop['timeout']
def make_path(path):
    newpath = os.path.normpath(path)
    if newpath == ".":
        return "/"
    newpath = newpath.replace("\\", "/")
    if newpath.startswith("/"):
        return newpath
    return "/" + newpath


async def find_content_type(extension):
    async with aiofiles.open(WORKDIR + "/mime.xml") as mime:
        d = xmltodict.parse(await mime.read())
        for m in d["mime"]["mime-mapping"]:
            if "." + m["extension"] == extension:
                # print(m["mime-type"])
                return m["mime-type"]
        return "text/html"


def get_time():
    return strftime("%a, %d %b %Y %X GMT", gmtime())


def std_headers(l, typ="text/html"):
    return {"Date": get_time(), "Content-Length": str(l), "Content-type": typ,
            "charset": "utf-8", "Connection": "close"}


def std_page(data):
    data = """
    <!DOCTYPE html> 
               <html>
               <header>""" + data + """"</header> 
                    <body>
                            """ + data + """
                    </body> 
               </html>
    """
    return data


def error(status, data, additional_headers={}):
    os.write(2, (data + '\n').encode('utf-8'))
    page = std_page(data)
    headers = std_headers(len(page.encode('utf-8')))
    headers.update(additional_headers)
    return web.Response(body=data, headers=headers, status=status)


async def check_protection(path):  # check if protected returns realm if so else return none
    async with aiosqlite.connect(WORKDIR+"/user_auth.db") as dbconn:
        c = await dbconn.cursor()
        await c.execute(
            "SELECT * FROM Realms WHERE rootdir == ? OR ? LIKE REPLACE(REPLACE(rootdir,'%','-%'),'_','-_')||'/%' ESCAPE '-'"
            , [path, path])
        result = await c.fetchone()
        # print(result)
        await c.close()
        if not result:
            return result
        else:
            return result[0]


async def find_credentials(realm):
    async with aiosqlite.connect(WORKDIR + "/user_auth.db") as dbconn:
        c = await dbconn.cursor()
        # print(realm)
        await c.execute("SELECT username,password FROM Users WHERE realm=?", [realm])
        result = await c.fetchone()  # assume success and unique
        # print(result)
        await c.close()
        return result


async def handle_dynamic_page(path, params): #path starts with "./"
    for param in params.values():
        eval(param)
    code = code_builder.CodeBuilder(path, params)
    return code.get_globals()


async def handle_file(path, params):  # path starts with "./"
    ext = os.path.splitext(path)[1]
    if ext == ".j2":
        return "text/html", await handle_dynamic_page(path, params)
    else:
        async with aiofiles.open(path, "rb") as file:
            return await find_content_type(ext), await file.read()


def handle_dir(path):  # path starts with "/"
    parent, x = os.path.split(path)
    dirs = os.listdir("." + path)
    if path.endswith("/"):
        path = path[:-1]
    page = """
    <!DOCTYPE html> 
               <html lang="en">
               <head><title>"""+x+"""</title></head> 
               <body>
                    <ul>
    """
    page += '<li><a href="' + parent + '"> parent </a><ul>'
    for d in dirs:
        page += "  <li> <a href=\"" + path + "/" + d + "\">" + d + "</a> </li>"
    page += """       </ul>
                        </li>
                        </ul>
                        </body> 
                  </html>"""
    #print(page)
    return page


async def handler(request):
    try:
        typ = "text/html"
        data = ""
        if not request.method == "GET":
            return error(501, "not a get request")
        path = make_path(request.path)  # all paths starts with / and not having \
        realm = await check_protection(path)
        #print(path)
        if realm:
            #print("check if has auth head")
            if "Authorization" in request.headers:
                #print(request.headers["Authorization"])
                creds_in = BasicAuth.decode(request.headers["Authorization"])  # TODO: check if protocol is basic
                creds_needed = await find_credentials(realm)
                if not creds_in.login == creds_needed[0] or not creds_in.password == creds_needed[1]:
                    return error(403, "username or password incorrect")
            else:
                return error(401, "need credential of " + realm,
                             {"WWW-Authenticate": 'Basic realm="need credentials of ' + realm + '"'})
        if os.path.isdir("." + path):
            data = handle_dir(path)
        elif os.path.isfile("." + path):
            typ, data = await handle_file("." + request.path, request.query)  # TODO: catch exception here
        else:
            return error(404, "page not found")
        response = web.Response(body=data, status=200, headers=std_headers(len(data), typ))
        return response
    except Exception as e:
        #print(e)
        return error(500, "server exception")


async def main():
    try:
        server = web.Server(handler)
        runner = web.ServerRunner(server)
        await runner.setup()
        site = web.TCPSite(runner=runner, host="localhost", port=PORT, shutdown_timeout=TIMEOUT)
        await site.start()
    except Exception as e:
        error(500, "server exception")


os.chdir(ROOT)
loop = asyncio.get_event_loop()
future = asyncio.ensure_future(main())
loop.run_forever()
#/236369/Solutions
#text ="http://localhost:8888/.idea/my_dynamic.j2?user_name=Ilya&product_list=[[[0,1,2,3,4,5],[6,7,8,9,10]]]&product_num=1&product_price=1"
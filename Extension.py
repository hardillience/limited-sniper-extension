import pip 
try:
    import discord, json, aiohttp, httpx, os, time, subprocess, sys, requests, psutil, signal
    from discord.ext import commands
    from discord import Embed, Colour
    from urllib.parse import urlparse
except ModuleNotFoundError:
    os.system('pip install requests psutil discord.py aiohttp')
    os.execv(sys.executable, [sys.executable] + [sys.argv[0]] + sys.argv[1:])

def get_thumbnail(item_id) -> str:
    return requests.get(f'https://thumbnails.roblox.com/v1/assets?assetIds={item_id}&size=420x420&format=Png').json()['data'][0]['imageUrl']

def get_itemname(item_id) -> str:
    return requests.get(f'https://economy.roblox.com/v2/assets/{item_id}/details').json()['Name']

def getidfromurl(link):
    att1 = urlparse(link).path.split('/')[-2] 
    att2 = urlparse(link).path.split('/')[-3] 
    att3 = urlparse(link).path.split('/')[2]
    val = None

    if att1.isdigit():
        val = att1
    elif att2.isdigit():
        val = att2
    elif att3.isdigit():
        val = att3
    
    return val

def linkable(value):
    try:
        val = getidfromurl(value)
        if val == None:
            return False
        else:
            return True
    except IndexError:
        return False

#Load Settings
with open('config.json') as f:
    settings = json.load(f)

def read_settings():
    with open('config.json', 'r') as f:
        return json.load(f)

webhook_color = discord.Color.from_rgb(0,219,58)
start_time = None

# Setting up the bot
bot = commands.Bot(command_prefix="!",intents = discord.Intents.all())

#Events
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You are not authorized to use this command!")

def is_authorized(): 
    async def predicate(ctx):
        settings = read_settings()
        return ctx.author.id in [int(x) for x in settings["authorized"]]
    return commands.check(predicate)

def checkvariable(t, var):
    if t is dict:
        list = t.keys()
        for i in list:
            if i == var:
                return True
        return False
    else:
        if var in t:
            return True
        else:
            return False
        
def rbx_request(session, method, url, **kwargs):
    request = session.request(method, url, **kwargs)
    method = method.lower()
    if (method == "post") or (method == "put") or (method == "patch") or (method == "delete"):
        if "X-CSRF-TOKEN" in request.headers:
            session.headers["X-CSRF-TOKEN"] = request.headers["X-CSRF-TOKEN"]
            if request.status_code == 403:
                request = session.request(method, url, **kwargs)
    return request
    
def restart_sniper():
    global runningSession
    if runningSession:
        for proc in psutil.process_iter():
            if proc.name() == "python.exe":
                if "main.py" in proc.cmdline()[1]:
                    os.kill(proc.pid, signal.SIGTERM)
        runningSession = subprocess.Popen([sys.executable, "main.py"])
    else:
        print("Sniper Process was not found! Using old restarter!")
        for proc in psutil.process_iter():
            if proc.name() == "python.exe":
                if "main.py" in proc.cmdline()[1]:
                    os.kill(proc.pid, signal.SIGTERM)
        runningSession = subprocess.Popen([sys.executable, "main.py"])

async def check(cookie):
    async with httpx.AsyncClient() as client:
        res = await client.get("https://users.roblox.com/v1/users/authenticated", headers={"Cookie": f".ROBLOSECURITY={cookie}"})

    if res.status_code == 200:
        username = res.json()["name"]
        return True, username
    else:
        return False, None

def overwrite(new_settings):
    with open('config.json', 'w') as file:
        json.dump(new_settings, file, indent=4)


#Events
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        return await ctx.send(embed=Embed(title="You are not authorized to use this command!", description=None, color=Colour.red()))


@bot.event
async def on_ready():
    global start_time
    start_time = time.time()
    os.system("cls" if os.name == "nt" else "clear")

    print("Limited Sniper Extension is now running in the background!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="items for cheap resale!"))
    print(f"Logged in as bot: {bot.user.name}")

bot.remove_command("help")

#Commands:
#help command
@bot.command()
@is_authorized()
async def help(ctx):
    msg = """# COMMANDS LIST

**ITEMS**
!add / !a {item_id / item_link} {max_price} --- Add an item to watcher
!remove / !r {item_id / item_link} --- Remove an item from watcher
!removeall --- Remove all items from watcher
!focus / !f {item_id / item_link} {max_price} --- Removes all items and focuses on the specified item
!maxprice / !mp {item_id / item_link} {new_max_price} --- Change an item's max price

**BOT CONFIG**
!token {bot_token} --- Change the bot token [idk if this works tbh lmao]
!cookie {cookie} --- Change the ROBLOX cookie [idk if this also works lmaoaoao]
!speed {new_watch_speed} --- Change the watch speed to your desired value   

!adduser / !au {user_id} --- Authorize a person to use your bot
!removeuser / !ru {user_id} --- Remove an authorized person from using your bot
!authorized --- Returns a list of all authorized users

**OTHERS**
!watching / !w --- Returns a list of all the items you are currently watching.
!watchinginfo / !wi --- Returns extra info of all the items you are currently watching.
!info / !i --- Returns info about the prefix, current ROBLOX account being used, the watch speed, items being watched, and runtime."""
    await ctx.author.send(msg)
    await ctx.reply(embed=Embed(title="A list of commands has been sent to your DMs!",description=None,color=webhook_color))

#ping
@bot.command()
async def ping(ctx):
    message = f"Pong! {round(bot.latency * 1000)}ms"
    await ctx.send(message)

# view all watching items
@bot.command(name="watchinginfo")
@is_authorized()
async def watchinginfo(ctx):
    settings = read_settings()
    watchlist = settings["items"]["list"]

    try:
        cookie = settings["cookie"]
        dataToUse = {
            "items": [] 
        }

        for item in watchlist:
            dataToUse["items"].append({"itemType": 1,"id": item})

        s = requests.Session()
        s.cookies[".ROBLOSECURITY"] = cookie
        s.headers["accept"] = "application/json"
        s.headers["Content-Type"] = "application/json"

        request = rbx_request(session=s, method="POST", url="https://catalog.roblox.com/v1/catalog/items/details", data=json.dumps(dataToUse))
        item = request.json()
        listOfEmbeds = []

        if request.status_code == 200 and item.get("data"):
            for item_data in item["data"]:
               if checkvariable(item_data, "lowestResalePrice") or item_data["lowestResalePrice"] != 0 :
                    embedToAdd =  Embed(
                        title=f'Watching: {item_data["name"]}',
                        url=f"https://www.roblox.com/catalog/{str(item_data['id'])}/",
                        color=webhook_color,
                        description=f"Creator: `{item_data['creatorName']}`\nLowest Resale Price: `{str(item_data['lowestResalePrice'])}` \nID: `{str(item_data['id'])}`"
                    )
                    embedToAdd.set_thumbnail(url=get_thumbnail(str(item_data['id'])))
                    listOfEmbeds.append(embedToAdd)
               else:
                    embedToAdd =  Embed(
                        title=f'Watching: {item_data["name"]}',
                        url=f"https://www.roblox.com/catalog/{str(item_data['id'])}/",
                        color=webhook_color,
                        description=f"Creator: `{item_data['creatorName']}`\nPrice: `Not for sale` \nID: `{str(item_data['id'])}`"
                    )
                    embedToAdd.set_thumbnail(url=get_thumbnail(str(item_data['id'])))
                    listOfEmbeds.append(embedToAdd)

            if len(listOfEmbeds) == 0 or len(watchlist) == 0:
                return ctx.send(Embed(title="No items are currently being watched!",description=None,color=webhook_color))
            await ctx.send(embeds=listOfEmbeds)
        else:
            await ctx.send("Failed to get list and error has been received: " + item["errors"][0]["message"])
    except Exception as e:
        embed = Embed(
            title=f"An error occurred while trying to fetch your watch list: {str(e)}. This is most likely due to there being no items in the list or due to a wrongly input item.",
            desciption=None,
            color=Colour.red(),
        )
        await ctx.send(embed=embed)

# same as above omegalul
@bot.command(name="wi")
@is_authorized()
async def wi(ctx):
    ctx.command = bot.get_command("watchinginfo")
    await bot.invoke(ctx)

#add owner
@bot.command()
@is_authorized()
async def watching(ctx):
    settings = read_settings()
    items = settings["items"]["list"]
    items_str = ", ".join(map(str, items))
    await ctx.send(items_str)

# same as above omegalul
@bot.command(name="w")
@is_authorized()
async def w(ctx):
    ctx.command = bot.get_command("watching")
    await bot.invoke(ctx)

#add owner
@bot.command()
@is_authorized()
async def adduser(ctx, user_id: int):
    settings = read_settings()
    
    authorized_ids = settings["authorized"]
    
    if str(user_id) not in authorized_ids:
        authorized_ids.append(str(user_id))
        settings["authorized"] = authorized_ids
        
        overwrite(settings)
        
        await ctx.send(embed=Embed(title="User added!",description=f"<@{user_id}> ({user_id}) can now use your bot!",color=webhook_color))
    else:
        await ctx.send(embed=Embed(title="User input already authorized!",description=f"<@{user_id}> ({user_id}) is already an authorized user!", color=webhook_color))

# same as above omegalul
@bot.command(name="au")
@is_authorized()
async def au(ctx):
    ctx.command = bot.get_command("adduser")
    await bot.invoke(ctx)

#remove owner
@bot.command()
@is_authorized()
async def removeuser(ctx, user_id: int):
    settings = read_settings()
        
    authorized_ids = settings["authorized"]
    
    if str(user_id) in authorized_ids:

        authorized_ids.remove(str(user_id))
        settings["authorized"] = authorized_ids
        overwrite(settings)

        embed = Embed(title="User removed!",description=f"<@{user_id}> ({user_id}) can no longer use your bot!",color=webhook_color)
        await ctx.send(embed=embed)
    else:
        embed = Embed(title="User input unauthorized!",description=f"<@{user_id}> ({user_id}) is not an authorized user!",color=webhook_color)
        await ctx.send(embed=embed)

# same as above omegalul
@bot.command(name="ru")
@is_authorized()
async def ru(ctx):
    ctx.command = bot.get_command("removeuser")
    await bot.invoke(ctx)

#owners
@bot.command()
@is_authorized()
async def authorized(ctx):
    settings = read_settings()
    authorized_ids = settings["authorized"]

    owners_str = ""
    for ownerid in authorized_ids:
        owners_str = owners_str + f"<@{ownerid}>  ({ownerid})\n"
    
    embed = Embed(title="Authorized Users",description=owners_str,color=webhook_color)

    await ctx.send(embed=embed)

#restart command
@bot.command()
@is_authorized()
async def restart(ctx):
    try:
        restart_sniper()
        await ctx.send(embed=Embed(title="Successfully restarted the sniper.", description=None, color=webhook_color))
    except Exception as e:
        await ctx.send(embed=Embed(title="An error occurred while trying to restart the sniper: {}".format(str(e)), description=None, color=Colour.red()))

#More command
@bot.command(pass_context = True)
@is_authorized()
async def info(ctx):
    settings = read_settings()

    cookie = settings["cookie"]
    items = settings["items"]["list"]
    maxprice = settings["items"]["global_max_price"]
    watching = ', '.join(str(item) for item in items)

    valid, username = await check(cookie)

    if start_time is not None:
        runtime = int(time.time() - start_time)
        minutes, seconds = divmod(runtime, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)

        runtime = f"{days} days, {hours} hours, {minutes} minutes and {seconds} seconds"
    else:
        runtime = "Unknown"

    async with httpx.AsyncClient() as c:
        res = await c.get("https://users.roblox.com/v1/users/authenticated", headers={"Cookie": f".ROBLOSECURITY={cookie}"})

    if res.status_code == 200:
        user_id = res.json()["id"]

        img_api = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
        async with httpx.AsyncClient() as c:
            other_res = await c.get(img_api)
        img = other_res.json()["data"][0]["imageUrl"]

    embed = Embed(title=f"hi {ctx.message.author.name}!!!! (Prefix: {bot.command_prefix})", description=None, color=webhook_color, timestamp=ctx.message.created_at)
    # embed.add_field(name="Current owner ID(s):", value=owners,inline=True)
    embed.add_field(name="Current account:", value=username if valid else "Inactive (Update your cookie!)")
    embed.add_field(name="Watching:", value=watching if watching else "No Items")
    embed.add_field(name="Global Max Price:", value=maxprice)
    embed.add_field(name="Runtime:", value=runtime)
    embed.set_footer(text="hardish's extension for xolo's limited sniper")
    embed.set_thumbnail(url=img)
    await ctx.reply(embed=embed)

# same as above omegalul
@bot.command(name="i")
@is_authorized()
async def i(ctx):
    ctx.command = bot.get_command("info")
    await bot.invoke(ctx)

# focus command
@bot.command()
@is_authorized()
async def focus(ctx, item: str):

    if not item.isdigit() and linkable(item) == True:
        id = getidfromurl(item)
    elif linkable(item) == False and item.isdigit():
        id = item
    elif linkable(item) == False and not item.isdigit():
        id = None
    
    embed_title = None
    
    if id != None and id.isdigit():
        print("Adding new item...")

        settings = read_settings()
        settings["items"]["list"] = [int(id)]
        overwrite(settings)
        restart_sniper()  

        embed_title= f"Now focusing on {get_itemname(id)} ({id})."
    else:
        embed_title="You have not entered a valid ID or link!"

    e = Embed(title=embed_title, description=None, color=webhook_color, timestamp=ctx.message.created_at)
    e.set_footer(text="hardish's extension for xolo's limited sniper")

    await ctx.send(embed=e)

# same as above omegalul
@bot.command(name="f")
@is_authorized()
async def f(ctx):
    ctx.command = bot.get_command("focus")
    await bot.invoke(ctx)

# add item command
@bot.command()
@is_authorized()
async def add(ctx, item: str):
    if not item.isdigit() and linkable(item) == True:
        id = getidfromurl(item)
    elif linkable(item) == False and item.isdigit():
        id = item
    elif linkable(item) == False and not item.isdigit():
        id = None

    settings = read_settings()
    items = settings["items"]["list"]
    embed_title = None
    
    if id != None and id.isdigit():
        if int(id) in items:
            return await ctx.send(embed=Embed(title=f"{get_itemname(id)} ({id}) is already being watched!",description=None,color=webhook_color))
        else:           
            print("Adding new item...")
            items.append(int(id))
            overwrite(settings)
            restart_sniper()
            embed_title=f"{get_itemname(id)} ({id}) has been added."
    else:
        embed_title= f"You have not entered a valid link or ID!"

    e = Embed(title=embed_title, description=None, color=webhook_color, timestamp=ctx.message.created_at)
    e.set_footer(text="hardish's extension for xolo's limited sniper")
    await ctx.send(embed=e)

# same as above omegalul
@bot.command(name="a")
@is_authorized()
async def a(ctx):
    ctx.command = bot.get_command("add")
    await bot.invoke(ctx)

# max price command
@bot.command()
@is_authorized()
async def global_max_price(ctx, mp=None):
    try:
        if mp != None:
            int(mp)
    except ValueError:
        mp = None

    settings = read_settings()
    items = settings["items"]
    embed_title = None
    
    if mp != None and mp.isdigit():
            items["global_max_price"] = int(mp)   
            overwrite(settings)
            restart_sniper()
            embed_title = f"Updated global max price to {(mp)}."
    else:
        return await ctx.send(embed=Embed(title="You must specify an integer global max price!",description=None, color=webhook_color))

    e = Embed(title=embed_title, description=None, color=webhook_color, timestamp=ctx.message.created_at)
    e.set_footer(text="hardish's extension for xolo's limited sniper")
    await ctx.send(embed=e)

# same as above omegalul
@bot.command(name="gmp")
@is_authorized()
async def mp(ctx):
    ctx.command = bot.get_command("global_max_price")
    await bot.invoke(ctx)

# same as above omegalul
@bot.command(name="maxprice")
@is_authorized()
async def mp(ctx):
    ctx.command = bot.get_command("global_max_price")
    await bot.invoke(ctx)

# same as above omegalul
@bot.command(name="mp")
@is_authorized()
async def mp(ctx):
    ctx.command = bot.get_command("global_max_price")
    await bot.invoke(ctx)

# max price command
@bot.command()
@is_authorized()
async def remove(ctx, item: str):
    if not item.isdigit() and linkable(item) == True:
        id = getidfromurl(item)
    elif linkable(item) == False and item.isdigit():
        id = item
    elif linkable(item) == False and not item.isdigit():
        id = None

    settings = read_settings()
    items = settings["items"]["list"]
    embed_title = None
    
    if id != None and id.isdigit():
        if int(id) in items:
            print("Removing an item...")
            items.remove(int(id))  
            overwrite(settings)
            restart_sniper()

            embed_title = f"{get_itemname(int(id))} ({id}) has been removed."
        else:      
            return await ctx.send(embed=Embed(title=f"{get_itemname(id)} ({id}) is not being watched!",description=None,color=webhook_color))     
    else:
        embed_title= f"You have not entered a valid link or ID!"

    e = Embed(title=embed_title, description=None, color=webhook_color, timestamp=ctx.message.created_at)
    e.set_footer(text="hardish's extension for xolo's limited sniper")
    await ctx.send(embed=e)

# same as above omegalul
@bot.command(name="r")
@is_authorized()
async def r(ctx):
    ctx.command = bot.get_command("remove")
    await bot.invoke(ctx)

# removeall command
@bot.command()
@is_authorized()
async def removeall(ctx):
    settings = read_settings()
    settings["items"]["list"] = []
    overwrite(settings)
    restart_sniper()

    e = Embed(title="Removed all items successfully!", description=None, color=webhook_color, timestamp=ctx.message.created_at)
    e.set_footer(text="hardish's extension for xolo's limited sniper")
    await ctx.send(embed=e)

# same as above omegalul
@bot.command(name="ra")
@is_authorized()
async def ra(ctx):
    ctx.command = bot.get_command("removeall")
    await bot.invoke(ctx)

#token command
@bot.command()  
@is_authorized()
async def token(ctx, new_token: str):
    
    settings = read_settings()
    settings["token"] = new_token
    overwrite(settings)

    embed = Embed(title="Updated discord bot token successfully!",description=None,color=webhook_color)

    await ctx.send(embed=embed)

    if await restart_sniper():
            print("Bot restarted after updating the token.")
    else:
            print("Error while trying to restart the bot after updating the token.")

#cookie command
@bot.command()
@is_authorized()
async def cookie(ctx, cookie: str):
    
    async with httpx.AsyncClient() as c:
        res = await c.get("https://users.roblox.com/v1/users/authenticated", headers={"Cookie": f".ROBLOSECURITY={cookie}"})

    if res.status_code == 200:
        username = res.json()["name"]
        user_id = res.json()["id"]

        
        img_api = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=420x420&format=Png&isCircular=false"
        async with httpx.AsyncClient() as c:
            other_res = await c.get(img_api)
        img = other_res.json()["data"][0]["imageUrl"]

        settings = read_settings()
        settings["cookie"] = cookie    
        overwrite(settings)
        
        embed = Embed(title=f"Cookie changed to {username} successfully!",description=None,color=webhook_color)
        embed.set_thumbnail(url=img)

        await ctx.send(embed=embed)

        if await restart_sniper():
            print("Bot restarted after updating the cookie.")
        else:
            print("Error while trying to restart the bot after updating the cookie.")

    else:
        await ctx.send(embed=Embed(title="Provided cookie is invalid.",description=None,color=Colour.red()))

    
runningSession = subprocess.Popen([sys.executable, "main.py"])
bot_token = settings["token"]
bot.run(bot_token)

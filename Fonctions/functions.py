import asyncio
import discord
from pymongo import MongoClient
import random
import pymongo
import time
import datetime
from datetime import datetime, timedelta

Token = 'Non'
intents = discord.Intents.all()
intents.members = True
bot = discord.Client(intents=intents)
client = MongoClient("mongodb+srv://Alexandre:Valou140776@7ds.gctqp.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")

db = client["7ds"]
player = db.Players
shop = db.Shop
inv = db.Inventory
monster = db.Monster
area = db.Area
lvlup = db.Level
race = db.Race
rank = db.Rank
code = db.Codes
event = db.Events
boss = db.Boss
powe = db.Power
cooldowns = {}
quest = db.Quest
adventure_bosses_collection = db.Adventure
quest_collection = db["Quest"]

# Define a dictionary with area as keys and max values as sub-dictionaries
LOOT_MAX_VALUES = {
    1: {
        "MAX_GOLD": 250,
        "MAX_SPIN": 2,
        "MAX_EPIC_SPIN": 0,
        "MAX_RARE_SPIN": 0
    },
    2: {
        "MAX_GOLD": 500,
        "MAX_SPIN": 5,
        "MAX_EPIC_SPIN": 0,
        "MAX_RARE_SPIN": 2
    },
    # ... Define more areas as needed ...
}


def get_most_rich(n):
    x = 0
    r = []
    for doc in player.find().sort('lvl', pymongo.DESCENDING):
        r.append(doc)
        if x == n:
            break
        x += 1
    return r

def a_item(id, item):
    k = -1

    docs = inv.find_one({"id": id})

    r = False

    for i in docs["inventory"]:

        k += 1

        args = i.split(":")

        if args[0] == item and int(args[1]) > 0:
            r = True

            break

    return [r, k]


async def level(p, a, l, max_level=10):
    user = await bot.fetch_user(p)
    docs = player.find_one({"id": p})

    if docs["lvl"] >= max_level:
        # Check if the notification has already been sent for the current max level
        if docs.get("max_level_notified") != max_level:
            await user.create_dm()
            await user.dm_channel.send("**You have reached the maximum level. Await new updates.**")
            # Update the database to mark that the max level message has been sent for this level
            player.update_one({"id": p}, {"$set": {"max_level_notified": max_level}})
        return  # Stop further processing after reaching max level

    arg = l.split("/")
    xp = int(arg[0]) + a
    total = int(arg[1])

    if xp >= total:
        var = docs["life"].split("/")
        hp = var[0]
        var = xp - total
        if lvlup.count_documents({"lvl": docs["lvl"] + 1}) > 0:
            docs2 = lvlup.find_one({"lvl": docs["lvl"] + 1})
            await user.create_dm()
            await user.dm_channel.send("You just leveled up! Your stats increased by : " + str(docs2["attack"]) + " attack and " + str(docs2["defense"]) + " defense. You now have " + str(docs2["hp"]) + " HP, + " + str(docs2["spin"]) + " spin(s), + " + str(docs2["rareSpins"]) + " rare Spin(s)")
            for s in rank.find({"lvl": docs["lvl"] + 1}):
                if s["race"] == docs["race"]:
                    player.update_one({"id": p}, {"$set": {"rank": s["rank"]}})
                    await user.create_dm()
                    await user.dm_channel.send("You ranked up to **" + s["rank"] + "**!")
                    break
            for b in powe.find({"lvl": docs["lvl"] + 1}):
                if b["race"] == docs["race"]:
                    await user.create_dm()
                    await user.dm_channel.send("You obtained a new form, which is : **" + b["form"] + "**")
                    break
            total = docs2["XP"]
            player.update_one({"id": p}, {
                "$inc": {"lvl": 1, "attack": docs2["attack"], "defense": docs2["defense"], "spin": docs2["spin"],
                         "rareSpins": docs2["rareSpins"]},
                "$set": {"XP": str(var) + "/" + str(total), "life": hp + "/" + str(docs2["hp"])}})

            if var > total:
                docs = player.find_one({"id": p})
                await level(p, var, docs["XP"])
        else:
            total += 1000
            player.update_one({"id": p}, {"$inc": {"lvl": 1}, "$set": {"XP": "{}/{}".format(var, total)}})
            try:
                await user.create_dm()
                await user.dm_channel.send("You just leveled up,")
            except:
                ""

    player.update_one({"id": p}, {"$set": {"XP": "{}/{}".format(xp, total)}})
def separt(a):
    r = []
    for i in a:
        arg = i.split(":")
        r.append(arg[0])
    return r

async def cool(command: str,  cooldowns, cooldown_times): #Fonction for cooldowns

    if command not in cooldowns:
        cooldowns[command] = []  # Initialize cooldown list for the command if not present

    cooldown_time = cooldown_times[command]
    last_time = cooldowns[command]

    if last_time:
        last_command_time = last_time[-1]
        if isinstance(last_command_time, datetime):
            delta = datetime.utcnow() - last_command_time
            if delta < cooldown_time:
                remaining_time = cooldown_time - delta
                return False, remaining_time.seconds  # Command is still on cooldown

    # Add the current time to the cooldown list
    cooldowns[command].append(datetime.utcnow())
    return True, None  # Command is not on cooldown
cooldown_times = { #Dictionary cooldown.
    "cave": timedelta(minutes=5),
    "mine": timedelta(minutes=10),
    "hunt": timedelta(seconds=20),
    "form": timedelta(minutes=5),
    "rest": timedelta(seconds=30),
    "adventure": timedelta(minutes=15),
    "withdraw": timedelta(minutes=20)
    # Add more commands and their respective cooldown times as needed
}

async def show_commands_with_cooldowns(cooldowns, cooldown_times, message):
    embed = discord.Embed(title="**Commands' Cooldown**", color=0x00ff00)
    current_time = datetime.utcnow()  # Get the current time once for consistency

    for command, cooldown_time in cooldown_times.items():
        field_value = "No cooldown active"  # Default message

        if command in cooldowns and cooldowns[command]:  # Check if there are entries
            last_time = cooldowns[command][-1]
            delta = current_time - last_time

            if delta < cooldown_time:
                remaining_time = cooldown_time - delta
                hours, remainder = divmod(remaining_time.total_seconds(), 3600)
                minutes, seconds = divmod(remainder, 60)
                time_display = f"{int(hours)} hours {int(minutes)} minutes {int(seconds)} seconds"
                field_value = f"**Cooldown: {time_display}**"

        embed.add_field(name=command, value=field_value, inline=False)

    await message.channel.send(embed=embed)
async def list_commands(message, bot):  # Include the bot as a parameter if it's not globally available
    def create_embed():
        return discord.Embed(
            title="Available Commands",
            description="List of all available commands and their aliases. (There's always a space between ! (cmd))",
            color=discord.Color.blue()
        )

    commands = {
        "profile": ["p", "P"],
        "start": [],
        "spin": [],
        "hunt": [],
        "cave exploration": ["ce"],
        "mine": [],
        "cooldowns": ["cd", "Cooldowns"],
        "rare spin": ["rs", "Rare Spin"],
        "epic spin": ["es", "Epic Spin"],
        "help": [],
        "merge": [],
        "mergeEpic": ["me"],
        "leaderboard": ["l"],
        "use": [],
        "forms": [],
        "races": [],
        "rest": [],
        "quest": [],
        "cmds": [],
        "code": [],
        "shop": [],
        "inventory": ["i"],
        "equip": [],
        "uneq": [],
        "buy": [],
        "sell": [],
        "areas": [],
        "area": [],
        "heal": [],
        "boss": [],
        "adventure": ["adv"],
        "monsters": [],
        "bank": [],
        "deposit ": [],
        "withdraw": []
    }

    embeds = []
    current_embed = create_embed()
    field_count = 0

    for cmd, aliases in commands.items():
        if field_count >= 25:
            embeds.append(current_embed)
            current_embed = create_embed()
            field_count = 0

        cmd_text = f"`! {cmd}` ({', '.join(f'`! {alias}`' for alias in aliases)})" if aliases else f"`! {cmd}`"
        current_embed.add_field(name=cmd.capitalize(), value=cmd_text, inline=False)
        field_count += 1

    if field_count > 0:
        embeds.append(current_embed)

    def check(reaction, user):
        return user == message.author and str(reaction.emoji) in ["⬅️", "➡️"]

    current_page = 0
    msg = await message.channel.send(embed=embeds[current_page])

    await msg.add_reaction("⬅️")
    await msg.add_reaction("➡️")

    while True:
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(reaction.emoji) == "➡️" and current_page < len(embeds) - 1:
                current_page += 1
                await msg.edit(embed=embeds[current_page])
                await msg.remove_reaction(reaction, user)
            elif str(reaction.emoji) == "⬅️" and current_page > 0:
                current_page -= 1
                await msg.edit(embed=embeds[current_page])
                await msg.remove_reaction(reaction, user)
        except Exception as e:
                print(f"Caught an exception: {type(e).__name__} - {str(e)}")
                break

    await msg.clear_reactions()

    await message.clear_reactions()

async def show_profile(message, player, area):
    if player.count_documents({"id": message.author.id}) != 0:
        docs = player.find_one({"id": message.author.id})
        docs2 = area.find_one({"area": docs["area"]})
        power = docs["attack"] + docs["defense"] * 150
        embed = discord.Embed()
        luck = random.choice([1, 2, 3])
        embed.title = "Profile"
        embed.set_footer(text="**Version 0.5 (Beta)**")
        embed.set_thumbnail(url=message.author.avatar.url)
        embed.add_field(name="**Basic**:",
                        value="**Name**: " + message.author.name + "\n\n<:area:815314261701427272> **Area**: " +
                              docs2["name"] + "\n\n**HP**: " + docs[
                                  "life"] + "\n\n<:attention:815309696767361034> **Race**: " + docs[
                                  "race"] + "\n\n<:favoris:815309799872266270> **Spin**: " + str(
                            docs["spin"]) + "\n\n<:stare:1053706172470919278> **RareSpins: **" + str(
                            docs["rareSpins"]) + "\n\n<:stare:1053706172470919278> **EpicSpins: **" + str(
                            docs["epicSpins"]) + "\n\n<:setting:815309870567522344> **Rank**: **" + docs[
                                  "rank"] + "** " + "\n\n<:setting:815309870567522344> **Rank Bonus**: **" + str(
                            docs["rank+"]) + "** ", inline=False)
        embed.colour = discord.Colour.dark_blue()
        embed.add_field(name="**Stats**:", value="**Slot1**: " + docs["slot1"] + "\n\n**Slot2**: " + docs[
            "slot2"] + "\n\n**Level**: " + str(docs["lvl"]) + "\n\n**XP**: " + docs["XP"],)
        embed.add_field(name="**Stats2**:", value="\n\n<:shield:815215679354830858>**Defense**: " + str(
            docs["defense"]) + "\n\n<:sword:815214408758329354>**Attack**: " + str(
            docs["attack"]) + "\n\n<a:flame:819276019411320874> **Power level**: " + str(
            power) + "\n\n<:money:815310399754600530> **Gold**: " + str(docs["gold"]),)
        embed.add_field(name="**misc**", value="**Form** : " + docs["form"] + "\n\n\n" + "**Boss killed :** " + str(docs["area_cleared"]), inline=True)
        await message.channel.send(message.author.mention, embed=embed)

    else:
        await message.channel.send("You do not have a profile.")

async def rest_heal(message, player):
    if player.count_documents({"id": message.author.id}) != 0:
        is_cool, remaining_time = await cool("rest", cooldowns, cooldown_times)
        if not is_cool:
            await message.channel.send(f"You've already rested, try again in {remaining_time} seconds.")
            return

        # Get player's document
        player_doc = player.find_one({"id": message.author.id})
        var = player_doc["life"].split("/")
        current_life = int(var[0])
        max_life = int(var[1])

        # Check if the player already has max HP
        if current_life == max_life:
            await message.channel.send(message.author.mention + " You already have max HP.")
            return

        # Calculate new life points
        new_life = min(current_life + 20, max_life)

        # Update player's life points in the database
        player.update_one({"id": message.author.id}, {"$set": {"life": f"{new_life}/{max_life}"}})

        await message.channel.send(
            message.author.mention + f" You rest and feel better. You gained **{new_life - current_life}** :heart: HP. Your current is HP: {new_life}/{max_life}")
        await update_quest_progress(message, player, quest_collection, "Basic Resting", monster_name=None)
    else:
        await message.channel.send("You do not have a profile.")

async def show_User_Profile(message,player,area):
    try:
        user = message.mentions[0]
    except:
        await message.channel.send(" This user does not exist.")
        return
    if player.count_documents({"id": user.id}) != 0:
        docs = player.find_one({"id": user.id})
        docs2 = area.find_one({"area": docs["area"]})
        power = docs["attack"] + docs["defense"] * 150
        embed = discord.Embed()
        luck = random.choice([1, 2, 3])
        embed.title = "Profile"
        embed.set_footer(text="**Version 0.5 (Beta)**")
        embed.set_thumbnail(url=user.avatar.url)
        embed.add_field(name="**Basic**:",
                        value="**Name**: " + user.name + "\n\n<:area:815314261701427272> **Area**: " + docs2[
                            "name"] + "\n\n:heart: **HP**: " + docs[
                                  "life"] + "\n\n<:attention:815309696767361034> **Race**: " + docs[
                                  "race"] + "\n\n<:favoris:815309799872266270> **Spin**: " + str(
                            docs["spin"]) + + "\n\n<:stare:1053706172470919278> **RareSpins: **" + str(
                            docs["rareSpins"]) + "\n\n<:stare:1053706172470919278> **EpicSpins: **" + str(
                            docs["epicSpins"]) + "\n\n<:setting:815309870567522344> **Rank**: **" + docs[
                                  "rank"] + "** " + "\n\n<:setting:815309870567522344> **Rank Bonus**: **" +
                              docs["rank+"] + "** " + "\n\n<:stare:1053706172470919278> **RareSpins: **" + str(
                            docs["rareSpins"]), inline=False)
        embed.colour = discord.Colour.dark_blue()
        embed.add_field(name="**Stats**:", value="**Slot1**: " + docs["slot1"] + "\n\n**Slot2**: " + docs[
            "slot2"] + "\n\n**Level**: " + str(docs["lvl"]) + "\n\n**XP**: " + docs["XP"])
        embed.add_field(name="**Stats2**:", value="\n\n<:shield:815215679354830858>**Defense**: " + str(
            docs["defense"]) + "\n\n<:sword:815214408758329354>**Attack**: " + str(
            docs["attack"]) + "\n\n<a:flame:819276019411320874> **Power level**: " + str(
            power) + "\n\n<:money:815310399754600530> **Gold**: " + str(docs["gold"]))
        embed.add_field(name="**misc**", value="**Form** :" + docs["form"], inline=True)

        await message.channel.send(message.author.mention, embed=embed)

    else:
        await message.channel.send(" This user does not have a profile.")

async def start_game(message, player):
    if player.count_documents({"id": message.author.id}) == 0:
        player.insert_one(
            {"id": message.author.id, "lvl": 1, "XP": "1/1000", "attack": 15, "defense": 5, "gold": 500,
             "power": "None", "race": "None", "rank": "None", "rank+": "None", "form": "None", "spin": 5,
             "rareSpins": 0, "epicSpins": 0, "area": 1,
             "slot1": "None", "slot2": "None", "life": "100/100", "codes": [], "bank": {"bank_level": 1, "gold_in_bank": 0, "bank_capacity": 2500, "total_deposited": 0},  "last_claim": None, "streak": 0})
        inv.insert_one({"id": message.author.id, "inventory": []})
        player.update_many({"area_cleared": {"$exists": False}}, {"$set": {"area_cleared": 0}})
        await message.channel.send(
            message.author.name + " You successfully created your account. Welcome to Magius ! (**Type ! p to see your profile, and ! spin to spin your first race, and of course ! help if needed, ! cmds to see all actual commands.**) As for now the current lvl max is 10.")
        await list_commands(message, bot)
    else:
        await message.channel.send("You already own an account.")

async def spin_race(message,player,race):
    if player.count_documents({"id": message.author.id}) != 0:
        var = player.find_one({"id": message.author.id})
        if var["spin"] > 0:
            b = [3, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 2, 2, 1, 1, 1, 1, 1, 1, 1,
                 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 3, 3, 4, 4, 1, 1, 1, 1, 5, 1, 1,
                 2, 2, 3, 1, 6, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 2, 1, 2, 1, 2, 1, 3, 4, 1, 2, 1, 2, 5, 1, 2,
                 3, 1]
            b = random.choice(b)
            c = []
            for i in race.find({}):
                if i["rare"] != b:
                    continue
                c.append(i["name"])
            g = random.choice(c)
            e = race.find_one({"name": g})
            rarity12 = "A common race !"
            rarity3 = "A **rare** race ! Congrats"
            rarity4 = "A **legendary race** !!! Epic ! "
            rarity5 = "A **Mythical race** !!! Wow! "
            rarity6 = "**A Exodia race.... Damn. Lucky !** "
            if var["race"] == "None":
                player.update_one({"id": message.author.id}, {"$set": {"race": g, "rank": e["rank"]},
                                                              "$inc": {"defense": e["defense"],
                                                                       "attack": e["attack"], "spin": - 1}})
                if b == 1 or b == 2:
                    await message.channel.send(
                        message.author.mention + "You rolled for a race and you got **(" + g + ")** which is " + rarity12 + ". And you now have <:favoris:815309799872266270> " + str(
                            var["spin"] - 1) + " spin(s) remaining, and gained " + str(
                            e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                            e["attack"]) + "**<:sword:815214408758329354>attack.**")
                else:
                    if b == 3:
                        await message.channel.send(
                            message.author.mention + "You rolled for a race and you got **(" + g + ")** which is " + rarity3 + ". And you now have <:favoris:815309799872266270> " + str(
                                var["spin"] - 1) + " spin(s) remaining, and gained " + str(
                                e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                e["attack"]) + "**<:sword:815214408758329354>attack.**")
                    else:
                        if b == 4:
                            await message.channel.send(
                                message.author.mention + "You rolled for a race and you got **(" + g + ")** which is " + rarity4 + ". And you now have <:favoris:815309799872266270> " + str(
                                    var["spin"] - 1) + " spin(s) remaining, and gained " + str(
                                    e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                    e["attack"]) + "**<:sword:815214408758329354>attack.**")
                        else:
                            if b == 5:
                                await message.channel.send(
                                    message.author.mention + "You rolled for a race and you got **(" + g + ")** which is " + rarity5 + ". And you now have <:favoris:815309799872266270> " + str(
                                        var["spin"] - 1) + " spin(s) remaining, and gained " + str(
                                        e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                        e["attack"]) + "**<:sword:815214408758329354>attack.**")
                                channel = bot.get_channel(1053697149751263314)
                                await channel.send(
                                    message.author.name + "Got " + rarity5 + "Which is " + "**(" + g + ")**")
                            else:
                                if b == 6:
                                    await message.channel.send(
                                        message.author.mention + "You rolled for a race and you got **(" + g + ")** which is " + rarity6 + ". And you now have <:favoris:815309799872266270> " + str(
                                            var["spin"] - 1) + " spin(s) remaining, and gained " + str(
                                            e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                            e["attack"]) + "**<:sword:815214408758329354>attack.**")
                                    channel = bot.get_channel(1053697149751263314)
                                    await channel.send(
                                        message.author.name + "Got " + rarity6 + "Which is " + "**(" + g + ")**")
                                else:
                                    await message.channel.send(
                                        message.author.mention + "It seems like the spin broke, contact a mod or try again.")

            else:
                t = race.find_one({"name": var["race"]})
                player.update_one({"id": message.author.id}, {"$set": {"race": g, "rank": e["rank"]},
                                                              "$inc": {"defense": e["defense"] - t["defense"],
                                                                       "attack": e["attack"] - t["attack"],
                                                                       "spin": - 1}})
                if b == 1 or b == 2:
                    await message.channel.send(
                        message.author.mention + "You rolled for a race and you got **(" + g + ")** which is " + rarity12 + ". You now have <:favoris:815309799872266270> " + str(
                            var["spin"] - 1) + " spin(s) remaining, and gained " + str(
                            e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                            e["attack"]) + "**<:sword:815214408758329354>attack.**")
                else:
                    if b == 3:
                        await message.channel.send(
                            message.author.mention + "You rolled for a race and you got **(" + g + ")** which is " + rarity3 + ". You now have <:favoris:815309799872266270> " + str(
                                var["spin"] - 1) + " spin(s) remaining, and gained " + str(
                                e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                e["attack"]) + "**<:sword:815214408758329354>attack.**")
                    else:
                        if b == 4:
                            await message.channel.send(
                                message.author.mention + "You rolled for a race and you got **(" + g + ")** which is " + rarity4 + ". You now have <:favoris:815309799872266270> " + str(
                                    var["spin"] - 1) + " spin(s) remaining, and gained " + str(
                                    e["defense"]) + "**<:shield:815215679354830858>defense + **" + str(
                                    e["attack"]) + "**<:sword:815214408758329354>attack.**")
                        else:
                            if b == 5:
                                await message.channel.send(
                                    message.author.mention + "You rolled for a race and you got **(" + g + ")** which is " + rarity5 + ". You now have <:favoris:815309799872266270> " + str(
                                        var["spin"] - 1) + " spin(s) remaining, and gained " + str(
                                        e["defense"]) + "**<:shield:815215679354830858>defense + **" + str(
                                        e["attack"]) + "**<:sword:815214408758329354>attack.**")
                                channel = bot.get_channel(1053697149751263314)
                                await channel.send(
                                    message.author.name + "Got " + rarity5 + "Which is " + "**(" + g + ")**")
                            else:
                                if b == 6:
                                    await message.channel.send(
                                        message.author.mention + "You rolled for a race and you got **(" + g + ")** which is " + rarity6 + ". You now have <:favoris:815309799872266270> " + str(
                                            var["spin"] - 1) + " spin(s) remaining, and gained " + str(
                                            e["defense"]) + "**<:shield:815215679354830858>defense + **" + str(
                                            e["attack"]) + "**<:sword:815214408758329354>attack.**")
                                    channel = bot.get_channel(1053697149751263314)
                                    await channel.send(
                                        message.author.name + "Got " + rarity6 + "Which is " + "**(" + g + ")**")
                                else:
                                    await message.channel.send(
                                        message.author.mention + "It seems like the spin broke, contact a mod or try again.")

        else:
            await message.channel.send(message.author.mention + "You don't have enough spin.")

    else:
        await message.channel.send(message.author.mention + "You do not have a profile yet! Create one.")

async def hunt_adv(message,player,level,cooldowns):
    docs = player.find_one({"id": message.author.id})
    if player.count_documents({"id": message.author.id}) != 0:
        is_cool, remaining_time = await cool("hunt", cooldowns, cooldown_times)
        if not is_cool:
            await message.channel.send(f"**You've already explored the surrounding come back in {remaining_time} seconds.**")
            return
        if int(docs["life"].split("/")[0]) <= 0:
            await message.channel.send(message.author.name + ", Did you really try to stand??? but you're dead. ")
            return
    luck = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 1, 1,
            1, 1, 4, 5, 5]
    luck = random.choice(luck)
    m = await message.channel.send(message.author.mention + " You went on a journey around the area...")
    await asyncio.sleep(5)
    r = []

    for i in monster.find({}):
        if i["area"] != docs["area"]:
            continue
        elif i["rare"] != luck:
            continue
        if i["level"] <= docs["lvl"]:
            r.append(i["name"])

    if not r:
        await message.channel.send("**You didn't find a monsters they are for sure hidding... Try later.**")
        return

    rand = random.randint(0, len(r) - 1)  # Subtract 1 to avoid IndexError
    name = r[rand]
    docs2 = monster.find_one({"name": name})
    var = docs["life"].split("/")
    life = int(var[0])
    life2 = docs2["life"]
    a = max(docs["attack"] - docs2["defense"], 0)
    if a <= 0:
        a = 0
    a1 = max(docs2["attack"] - docs["defense"], 0)
    if a1 <= 0:
        a1 = 0
    r = []
    var1 = a1
    var2 = a1
    for loop in range(5):
        var1 += 1
        var2 -= 1
        r.append(var1)
        if var2 < 0:
            continue
        r.append(var2)
    if a < 0:
        a = 0
    if a1 < 0:
        a1 = 0
    if a1 + a == 0:
        await message.channel.send(message.author.mention + " You both fought at equals strenght... No ones won.")
        return
    battle_description = f"**The battle begins with {name}!**\n\n"
    await m.edit(content=battle_description)
    await asyncio.sleep(3)
    while True:
        life2 -= max(a, 0)  # Ensure damage doesn't make life negative
        battle_description += f"**{message.author.mention} attacks {name}! Damage dealt: {a} HP. {name}'s remaining life: {max(life2, 0)}\n**"
        await m.edit(content=battle_description)
        await asyncio.sleep(4)
        if life2 <= 0:
            win = "p"
            battle_description += f"\n**Victory! {name} has been defeated!**"
            await m.edit(content=battle_description)
            await asyncio.sleep(3)
            break

        await asyncio.sleep(4)

        life -= max(a1, 0)  # Ensure damage doesn't make life negative
        battle_description += f"**{name} attacks {message.author.mention}! Damage dealt: {a1} HP. Your remaining life: {max(life, 0)}\n**"
        await m.edit(content=battle_description)
        await asyncio.sleep(4)
        if life <= 0:
            win = "m"
            battle_description += f"\n**Defeat! {message.author.mention} has been defeated by {name}.**"
            await m.edit(content=battle_description)
            await asyncio.sleep(3)
            break

    if win == "p":
        # Player wins

        lost = int(var[0]) - life
        a = docs2["XP"]

        r = []
        var1 = a
        var2 = a
        for loop in range(10):
            var1 += 1
            var2 -= 1
            r.append(var1)
            r.append(var2)

        a = random.choice(r)

        b = docs2["gold"]

        r = []
        var1 = b
        var2 = b
        for loop in range(10):
            var1 += 1
            var2 -= 1
            r.append(var1)
            r.append(var2)

        b = random.choice(r)
        player.update_one({"id": message.author.id},{"$set": {"life": str(life) + "/" + var[1]}, "$inc": {"gold": b}})

        await level(message.author.id, a, docs["XP"])
        await m.edit(content=message.author.mention + " you killed a **" + name + "**, and won " + str(a) + " Xp, \n" + str(b) + " gold and you lost " + str(lost) + " hp ! You now have **" + str( life) + "** :heart:")
        active_quests = quest_collection.find({"player_progress": {"$exists": True}})
        for quest in active_quests:
            required_monster = quest.get("monster_name")
            if name == required_monster:  # Use the name of the defeated monster
                # Update quest progress for the player
                await update_quest_progress(message, player, quest_collection, quest["name"], name)

        docs = player.find_one({"id": message.author.id})
        player_area = docs["area"]  # Assuming this gives you the numerical area
        max_values = LOOT_MAX_VALUES.get(player_area,
                                         LOOT_MAX_VALUES[1])  # Default to area 1 values if area is not defined

        docs2 = monster.find_one({"name": name, "area": docs["area"], "loot": "yes"})  # Check if monster is lootable
        if not docs2:
            await message.channel.send(message.author.mention + "**This monster has no loot on him.**")
            return

        # Decide if loot is awarded (random chance, e.g., 70%)
        if random.random() < 0.2:
            # Get the monster's base loot values
            base_gold = int(docs2.get("gold", 1))
            base_spin = int(docs2.get("spin", {"$numberLong": "1"})["$numberLong"])
            base_epic_spins = int(docs2.get("epicSpins", {"$numberLong": "0"})["$numberLong"])
            base_rare_spins = int(docs2.get("rareSpins", {"$numberLong": "0"})["$numberLong"])

            # Determine loot amounts
            gold_loot = random.randint(base_gold, max_values['MAX_GOLD']) if base_gold > 0 else 0
            spin_loot = random.randint(base_spin, max_values['MAX_SPIN']) if base_spin > 0 else 0
            epic_spin_loot = random.randint(base_epic_spins, max_values['MAX_EPIC_SPIN']) if base_epic_spins > 0 else 0
            rare_spin_loot = random.randint(base_rare_spins, max_values['MAX_RARE_SPIN']) if base_rare_spins > 0 else 0

            # Update the player's inventory with the new loot except XP
            player.update_one({"id": message.author.id}, {"$inc": {
                "gold": gold_loot,
                "spin": spin_loot,
                "epicSpins": epic_spin_loot,
                "rareSpins": rare_spin_loot
            }})
            loot_message = f"**You looted: {gold_loot} gold, {spin_loot} spins, {epic_spin_loot} epic spins, and {rare_spin_loot} rare spins" + f" on the {docs2['name']}.**"

            # Weapon loot chance
            if random.random() < 0.05:  # Weapon drop chance
                monster_area = int(docs2.get("area", 1))
                if shop.count_documents({"area": monster_area, "loot": "yes"}) > 0:
                    area_weapons = shop.find({"area": monster_area, "loot": "yes"})
                    chosen_weapon = random.choice(list(area_weapons))
                    player_inventory = inv.find_one({"id": message.author.id})
                    weapon_name = chosen_weapon['item']

                    # Check if weapon already exists in inventory
                    found = False
                    for index, item in enumerate(player_inventory["inventory"]):
                        item_name, quantity = item.split(":")
                        if item_name == weapon_name:
                            new_quantity = str(int(quantity) + 1)
                            player_inventory["inventory"][index] = f"{item_name}:{new_quantity}"
                            found = True
                            break

                    # If weapon not found in inventory, append new weapon
                    if not found:
                        player_inventory["inventory"].append(f"{weapon_name}:1")

                    # Update the player's inventory in the database
                    inv.update_one({"id": message.author.id}, {"$set": {"inventory": player_inventory["inventory"]}})

                    # Append weapon info to the loot message
                    loot_message += f"**, and a {weapon_name}**"

                # Send loot message
                await message.channel.send(loot_message)
        else:
            await message.channel.send("**You didn't find any loot this time, this monster was probably poor.**")



    else:
        # Player loses
        lost = docs["gold"] / 2
        lost = int(lost)
        player.update_one({"id": message.author.id}, {"$set": {"life": "0/" + var[1], "gold": lost}})
        await message.channel.send(content=message.author.mention + "By dying you lost " + str(lost) + " gold." + "it had" + docs2["life"] + "remaining")

async def cave_explo(message, player, cooldowns):
    if player.count_documents({"id": message.author.id}) != 0:
        is_cool, remaining_time = await cool("cave", cooldowns, cooldown_times)
        if not is_cool:
            await message.channel.send(f"You've already explored the cave come back in {remaining_time} seconds.")
            return
        r = []
        docs = player.find_one({"id": message.author.id})
        gold = docs["gold"]
        gold = int(gold)
        luck = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 1,
                1, 1, 1, ]
        luck = random.choice(luck)
        if luck == 1:
            await message.channel.send(message.author.mention + "You didn't find any gold. Try again later")

        if luck == 2:
            player.update_one({"id": message.author.id}, {"$set": {"gold": gold + 2500}})
            await message.channel.send(
                message.author.mention + "By going into the cave you found **2500 gold**<:money:815310399754600530>")
            await update_quest_progress(message, player, quest_collection, "Cave Exploration Quest", monster_name=None)

        if luck == 3:
            player.update_one({"id": message.author.id}, {"$set": {"gold": gold + 5000}})
            await message.channel.send(
                message.author.mention + "You found a deep hole, and went into it, you found **5000 gold** <:money:815310399754600530> !! Awesome!")
            await update_quest_progress(message, player, quest_collection, "Cave Exploration Quest", monster_name=None)
    else:
        await message.channel.send("You do not have a profile, create one by typing < ! start >")

async def mine_explo(message, player, cooldowns):
    if player.count_documents({"id": message.author.id}) != 0:
        is_cool, remaining_time = await cool("mine", cooldowns, cooldown_times)
        if not is_cool:
            await message.channel.send(f"You've already explored the mine come back in {remaining_time} seconds.")
            return
        r = []
        docs = player.find_one({"id": message.author.id})
        gold = docs["gold"]
        gold = int(gold)
        luck = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 3, 1,
                1, 1, 1, ]
        luck = random.choice(luck)
        if luck == 1:
            await message.channel.send(message.author.mention + "You didn't find any gold. Try again later")

        if luck == 2:
            player.update_one({"id": message.author.id}, {"$set": {"gold": gold + 250}})
            await message.channel.send(
                message.author.mention + "you just found **250 gold**<:money:815310399754600530>")

        if luck == 3:
            player.update_one({"id": message.author.id}, {"$set": {"gold": gold + 500}})
            await message.channel.send(
                message.author.mention + "you just found **500 gold** <:money:815310399754600530> !! Awesome!")
    else:
        await message.channel.send("You do not have a profile, create one by typing < ! start >")

async def spin_RareRace(message, player, race):
    if player.count_documents({"id": message.author.id}) != 0:
        var = player.find_one({"id": message.author.id})
        if var["rareSpins"] > 0:
            b = [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 6, 6, 6, 3, 3, 3, 3, 3,
                 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 5, 6, 3, 3, 3, ]
            b = random.choice(b)
            c = []
            for i in race.find({}):
                if i["rare"] != b:
                    continue
                c.append(i["name"])
            g = random.choice(c)
            e = race.find_one({"name": g})
            rarity3 = "A **rare** race ! Congrats"
            rarity4 = "A **legendary race** !!! Epic ! "
            rarity5 = "A **Mythical race** !!! Wow! "
            rarity6 = "**A Exodia race.... Damn. Lucky !** "
            rarity7 = "**Well you broke the game, congrats.**"
            if var["race"] == "None":
                player.update_one({"id": message.author.id}, {"$set": {"race": g, "rank": e["rank"]},
                                                              "$inc": {"defense": e["defense"],
                                                                       "attack": e["attack"],
                                                                       "rareSpins": - 1}})
                if b == 3:
                    await message.channel.send(
                        message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity3 + ". And you now have <:stare:1053706172470919278> " + str(
                            var["rareSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                            e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                            e["attack"]) + "**<:sword:815214408758329354>attack.**")
                else:
                    if b == 4:
                        await message.channel.send(
                            message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity4 + ". And you now have <:stare:1053706172470919278> " + str(
                                var["rareSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                                e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                e["attack"]) + "**<:sword:815214408758329354>attack.**")
                    else:
                        if b == 5:
                            await message.channel.send(
                                message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity5 + ". And you now have <:stare:1053706172470919278> " + str(
                                    var["rareSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                                    e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                    e["attack"]) + "**<:sword:815214408758329354>attack.**")
                            channel = bot.get_channel(1053697149751263314)
                            await channel.send(
                                message.author.name + "Got " + rarity5 + "Which is " + "**" + g + "**")
                        else:
                            if b == 6:
                                await message.channel.send(
                                    message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity6 + ". And you now have <:stare:1053706172470919278> " + str(
                                        var["rareSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                                        e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                        e["attack"]) + "**<:sword:815214408758329354>attack.**")
                                channel = bot.get_channel(1053697149751263314)
                                await channel.send(
                                    message.author.name + "Got " + rarity6 + "Which is " + "**(" + g + ")**")

                            else:
                                await message.channel.send(message.author.mention + "It seems like the spin broke, contact a mod or try again.")

            else:
                t = race.find_one({"name": var["race"]})
                player.update_one({"id": message.author.id}, {"$set": {"race": g, "rank": e["rank"]},
                                                              "$inc": {"defense": e["defense"] - t["defense"],
                                                                       "attack": e["attack"] - t["attack"],
                                                                       "rareSpins": - 1}})
                if b == 3:
                    await message.channel.send(
                        message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity3 + ". And you now have <:stare:1053706172470919278> " + str(
                            var["rareSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                            e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                            e["attack"]) + "**<:sword:815214408758329354>attack.**")
                else:
                    if b == 4:
                        await message.channel.send(
                            message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity4 + ". And you now have <:stare:1053706172470919278> " + str(
                                var["rareSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                                e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                e["attack"]) + "**<:sword:815214408758329354>attack.**")
                    else:
                        if b == 5:
                            await message.channel.send(
                                message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity5 + ". And you now have <:stare:1053706172470919278> " + str(
                                    var["rareSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                                    e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                    e["attack"]) + "**<:sword:815214408758329354>attack.**")
                            channel = bot.get_channel(1053697149751263314)
                            await channel.send(
                                message.author.name + "Got " + rarity5 + "Which is " + "**" + g + "**")
                        else:
                            if b == 6:
                                await message.channel.send(
                                    message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity6 + ". And you now have <:stare:1053706172470919278> " + str(
                                        var["rareSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                                        e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                        e["attack"]) + "**<:sword:815214408758329354>attack.**")
                                channel = bot.get_channel(1053697149751263314)
                                await channel.send(
                                    message.author.name + "Got " + rarity6 + "Which is " + "**" + g + "**")
                            else:
                                await message.channel.send(message.author.mention + "It seems like the spin broke, contact a mod or try again.")


        else:
            await message.channel.send(
                message.author.mention + "You don't have enough **Rare Spins **, They are harder to get. ( Obtainable at lvl 5, 10, 20, or through merge.)")

    else:
        await message.channel.send(message.author.mention + "You do not have a profile yet! Create one.")

async def spin_EpicRace(message, player, race):
    if player.count_documents({"id": message.author.id}) != 0:
        var = player.find_one({"id": message.author.id})
        if var["epicSpins"] > 0:
            b = [5, 5, 5, 6, 6, 6, 5, 6, 5, 5, 5, 5, 5, 6, 6, 6, 5, 6, 5, 6, 7, 7]
            b = random.choice(b)
            c = []
            for i in race.find({}):
                if i["rare"] != b:
                    continue
                c.append(i["name"])
            g = random.choice(c)
            e = race.find_one({"name": g})
            rarity5 = "A **Mythical race** !!! Wow! "
            rarity6 = "**A Exodia race.... Damn. Lucky !** "
            rarity7 = "**Well you broke the game, congrats.**"
            if var["race"] == "None":
                player.update_one({"id": message.author.id}, {"$set": {"race": g, "rank": e["rank"]},
                                                              "$inc": {"defense": e["defense"],
                                                                       "attack": e["attack"],
                                                                       "epicSpins": - 1}})
                if b == 5:
                    await message.channel.send(message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity5 + ". And you now have <:stare:1053706172470919278> " + str(
                            var["epicSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                            e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                            e["attack"]) + "**<:sword:815214408758329354>attack.**")
                    channel = bot.get_channel(1053697149751263314)
                    await channel.send(message.author.name + "Got " + rarity5 + "Which is " + "**" + g + "**")

                else:
                    if b == 6:
                        await message.channel.send(
                            message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity6 + ". And you now have <:stare:1053706172470919278> " + str(
                                var["epicSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                                e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                e["attack"]) + "**<:sword:815214408758329354>attack.**")
                        channel = bot.get_channel(1053697149751263314)
                        await channel.send(
                            message.author.name + "Got " + rarity6 + "Which is " + "**" + g + "**")
                        if b == 7:
                            await message.channel.send(
                                message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity7 + ". And you now have <:stare:1053706172470919278> " + str(
                                    var["epicSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                                    e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                    e["attack"]) + "**<:sword:815214408758329354>attack.**")
                            channel = bot.get_channel(1053697149751263314)
                            await channel.send(
                                message.author.name + "Got " + rarity7 + "Which is " + "**" + g + "**")

                    else:
                        await message.channel.send(message.author.mention + "It seems like the spin broke, contact a mod or try again.")

            else:
                t = race.find_one({"name": var["race"]})
                player.update_one({"id": message.author.id}, {"$set": {"race": g, "rank": e["rank"]},
                                                              "$inc": {"defense": e["defense"] - t["defense"],
                                                                       "attack": e["attack"] - t["attack"],
                                                                       "epicSpins": - 1}})
                if b == 5:
                    await message.channel.send(message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity5 + ". And you now have <:stare:1053706172470919278> " + str(
                            var["epicSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                            e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                            e["attack"]) + "**<:sword:815214408758329354>attack.**")
                    channel = bot.get_channel(1053697149751263314)
                    await channel.send(message.author.name + "Got " + rarity5 + "Which is " + "**" + g + "**")

                else:
                    if b == 6:
                        await message.channel.send(
                            message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity6 + ". And you now have <:stare:1053706172470919278> " + str(
                                var["epicSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                                e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                e["attack"]) + "**<:sword:815214408758329354>attack.**")
                        channel = bot.get_channel(1053697149751263314)
                        await channel.send(
                            message.author.name + "Got " + rarity6 + "Which is " + "**" + g + "**")
                        if b == 7:
                            await message.channel.send(
                                message.author.mention + "You used a rare spin and rolled for a race,to obtain **(" + g + ")** which is " + rarity7 + ". And you now have <:stare:1053706172470919278> " + str(
                                    var["epicSpins"] - 1) + " rare spin(s) remaining, and gained " + str(
                                    e["defense"]) + "**<:shield:815215679354830858>defense  + **" + str(
                                    e["attack"]) + "**<:sword:815214408758329354>attack.**")
                            channel = bot.get_channel(1053697149751263314)
                            await channel.send(
                                message.author.name + "Got " + rarity7 + "Which is " + "**" + g + "**")

                        else:
                            await message.channel.send(message.author.mention + "It seems like the spin broke, contact a mod or try again.")


        else:
            await message.channel.send(
                message.author.mention + "You don't have enough **Epic Spins **, They are harder to get. ( Obtainable only through Epic merge)")

    else:
        await message.channel.send(message.author.mention + "You do not have a profile yet! Create one.")

async def help_please(message, player):
    if player.count_documents({"id": message.author.id}) != 0:
        docs = player.find_one({"id": message.author.id})
        embed = discord.Embed()
        embed.title = "Help"
        embed.set_thumbnail(url=message.author.avatar.url)
        embed.set_footer(text="**Version 0.5 (Beta)**")
        embed.add_field(name="<:stare:1053706172470919278> Really important : ",
                        value="\n\n ** ! spin** to spin for your first race. \n\n **! rare spin** to spin for a race with higher chances to get a good on, it's for sure over common. (can be obtained at lvl **5, 10, 20** for now)",
                        inline=False)
        embed.add_field(name="<:setting:815309870567522344> _basic commands_ :",
                        value="\n\n** <! profile >, <! p >, or < ! P >**: To see your profile. \n\n**! start**:  To start your adventure\n and of course <! hunt> to win exp and gold... \n\n < **! mine(50 seconds cooldown), and ! cave exploration(1800 seconds)** to find gold.",
                        inline=True)
        embed.add_field(name="<:setting:815309870567522344> _Other commands_ :",
                        value="\n\n**! buy**:   To buy equipements, <:attention:815309696767361034> don't forget to write (! buy (number) Heal Potion for example) \n\n**! equip/uneq**: To equip an item or unequip, just write (!equip <name of the item with caps if needed>). \n\n**! areas**: To watch all areas that exist in the game. \n\n**! leaderboard or l**: used to see the players of the server. \n\n ** !races** To see all available races in the game. (With the rarities) ",
                        inline=False)
        await message.channel.send(message.author.mention, embed=embed)
    else:
        await message.channel.send("You do not have a profile, create one by typing < ! start >")

async def merge_spins(message, player):
    if player.count_documents({"id": message.author.id}) != 0:
        docs = player.find_one({"id": message.author.id})
        spin = docs["spin"]
        lost = docs["spin"] - 50
        spin_needed = 50 - spin
        rare = docs["rareSpins"] + 1
        if docs["spin"] > 49:
            player.update_one({"id": message.author.id}, {"$set": {"rareSpins": rare, "spin": lost}})
            await message.channel.send(
                message.author.mention + "You successfully crafted** 1 **rare ticket by merging **50 spins**." + "You now have **" + str(
                    rare) + "** rare spin(s) and **" + str(lost) + "** spin(s) left.")
        else:
            await message.channel.send("**You don't have enough spins, you need " + str(spin_needed) + " spins to merge into a rare spin.**")
    else:
        await message.channel.send("You do not have a profile, create one by typing < ! start >")

async def merge_epic(message, player):
    if player.count_documents({"id": message.author.id}) != 0:
        docs = player.find_one({"id": message.author.id})
        spin = docs["rareSpins"]
        lost = docs["rareSpins"] - 50
        spin_needed = 50 - spin
        epic = docs["epicSpins"] + 1
        if docs["rareSpins"] > 49:
            player.update_one({"id": message.author.id}, {"$set": {"epicSpins": epic, "spin": lost}})
            await message.channel.send(
                message.author.mention + "You successfully crafted** 1 **epic ticket by merging **50 rare spins**." + "You now have **" + str(
                    epic) + "** epic spin(s) and **" + str(lost) + "** rare spin(s) left.")
        else:
            await message.channel.send("**You don't have enough spins, you need " + str(spin_needed) + " rare spins to merge into a epic spin.**")
    else:
        await message.channel.send("You do not have a profile, create one by typing < ! start >")

async def del_user(message, player, main):
    b = message.guild.get_role(815214258937397248)
    if b in message.author.roles:
        ID = int(main.replace("del ", ""))
        if player.count_documents({"id": ID}) != 0:
            player.delete_one({"id": ID})
            inv.delete_one({"id": ID})
            await message.channel.send(message.author.mention + " Account succefully deleted.")
            user = await bot.fetch_user(ID)
            try:
                await user.create_dm()
                await user.dm_channel.send(
                    " Your account has been deleted. Dm a Modo, or an Admin for further help.")
            except:
                await message.channel.send(" Couldn't send the message")
        else:
            await message.channel.send(message.author.mention + " Wrong id.")

    else:
        await message.channel.send(message.author.mention + " You are not Admin.")

async def show_leaderboard(message, player):
    if player.count_documents({"id": message.author.id}) != 0:
        n = ""
        nb = 1
        a = get_most_rich(10)
        for s in a:
            try:
                user = await bot.fetch_user(s["id"])
            except:

                continue
            n += "{} - {} **Who is level {}** \n\n".format(nb, discord.utils.escape_markdown(user.name),s["lvl"])
            nb += 1

        embed = discord.Embed()
        embed.title = "Magius's LeaderBoard"
        embed.colour = discord.Colour.red()
        embed.description = n

        await message.channel.send(message.author.mention, embed=embed)

    else:
        await message.channel.send(message.author.mention + " You do not have a profile yet! create one.")

async def use_form(message, player, race, main):
    if player.count_documents({"id": message.author.id}):
        d = player.find_one({"id": message.author.id})
        dc = main.replace("use ", "")
        docs = powe.find_one({"form": dc})
        a = docs["attack"] + d["attack"]
        b = docs["defense"] + d["defense"]
        c = d["attack"]
        g = d["defense"]
        if d["race"] == docs["race"]:
            if d["lvl"] >= docs["lvl"]:
                is_cool, remaining_time = await cool("form", cooldowns, cooldown_times)
                if not is_cool:
                    await message.channel.send(
                        f"You've used your form, try again in {remaining_time} seconds.")
                    return
                li = [message.author.id]
                r = ""
                r += " You used** " + docs["form"] + "** and gained " + str(
                    docs["attack"]) + " **attack**, and " + str(docs["defense"]) + " **defense.**"
                await message.channel.send(r)
                player.update_one({"id": message.author.id},
                                  {"$set": {"attack": a, "defense": b, "form": docs["form"]}})
                await asyncio.sleep(120)
                await message.channel.send(message.author.mention + " Your " + docs["form"] + " runs out.")
                player.update_one({"id": message.author.id}, {"$set": {"attack": c, "defense": g, "form": d["form"]}})
            else:
                await message.channel.send(
                    message.author.mention + "You do not meet the required lvl for this power, which is " + str(
                        docs["lvl"]))
        else:
            await message.channel.send(
                message.author.mention + " You do not meet the required race for this power, which is " + docs[
                    "race"])
    else:
        await message.channel.send(message.author.mention + " You do not have a profile yet! Create one.")

async def show_forms(message, player):
    docs = player.find_one({"id": message.author.id})
    result = ""
    embed = discord.Embed()
    forme = {}
    for c in powe.find({}):
        check = []
        try:
            check = forme[c["race"]]
        except:
            ""
        check.append(
            f'\n **{c["form"]}** ({c["race"]}) Gives ** {c["attack"]} ** Attack and ** {c["defense"]} ** defense.** \n at lvl ** {c["lvl"]} ** \n')
        forme[c["race"]] = check

    for s in forme:

        for a in forme[s]:
            result += a

    embed.title = "Forms (All forms have a 2 minutes uses, and a 5 minutes cooldown)"
    embed.colour = discord.Colour.red()
    embed.description = result
    await message.channel.send(message.author.mention, embed=embed)

async def show_races(message, player):
    docs = player.find_one({"id": message.author.id})
    result = ""
    embed = discord.Embed()
    racen = {}
    for b in race.find({}):
        racen[b["name"]] = {"name": str(b["name"]), "rare": b["rare"], "attack": b["attack"],
                            "defense": b["defense"]}
    racelist = sorted(racen)
    for s in racelist:
        b = racen[s]
        result += "\n**" + str(b["name"]) + " ** (" + str(b["rare"]) + ") Gives **" + str(
            b["attack"]) + " ** Strength and ** " + str(b["defense"]) + " defense **\n "
    embed.title = "Races"
    embed.add_field(name="Information",
                    value="The numbers next to the names of the races are the **rarities** \n\n" + " 1 and 2 are for **commons** \n" + "3 for **rare** \n" + "4 for **legendary**\n" + "5 for **Mythical** \n" + "6 for **exodia** (Only optainable by rare spins)\n" + "And 7 for **OUTWORLD** (Only obtainable by epic spins.)" ,
                    inline=True)
    embed.colour = discord.Colour.blue()
    embed.description = result
    await message.channel.send(message.author.mention, embed=embed)

async def show_quest_board(message, player, quest_collection):
    if player.count_documents({"id": message.author.id}) != 0:
        player_data = player.find_one({"id": message.author.id})

        if player_data:
            embed = discord.Embed(title="**TODAY'S QUEST BOARD**", color=discord.Color.blue())
            for quest in quest_collection.find():
                name = quest.get('name', 'Unknown Quest')
                description = quest.get('description', 'No description available')
                required_progress = int(quest.get('required_progress', 0))
                xp_reward = str(quest.get("XP"))
                gold_reward = str(quest.get("gold"))

                # Retrieve player's progress for the quest
                player_progress = quest.get('player_progress', {})
                if isinstance(player_progress, list):
                    # Initialize player's progress for the quest
                    player_progress = {"player_id": str(message.author.id), "progress": 0}
                elif not isinstance(player_progress, dict):
                    await message.channel.send("Invalid data structure for player progress.")
                    return
                current_progress = player_progress.get('progress', 0)

                # Check if the quest is on cooldown
                last_completed = player_data.get('quest_cooldowns', {}).get(name, 0)
                current_time = time.time()
                cooldown_duration = int(quest.get('cooldown_duration', 0))
                cooldown_remaining = max(0, cooldown_duration - (current_time - last_completed))

                cooldown_remaining_str = "You can now complete this quest"
                if cooldown_remaining > 0:
                    hours, remainder = divmod(cooldown_remaining, 3600)
                    minutes, seconds = divmod(remainder, 60)
                    cooldown_remaining_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"

                embed.add_field(
                    name=name,
                    value=f"{description}\n(To complete: {current_progress}/{required_progress})\n**Cooldown: {cooldown_remaining_str}**\n The rewards are : {xp_reward} **XP**, and {gold_reward} <:money:815310399754600530> **gold**",
                    inline=True
                )

            await message.channel.send(embed=embed)
        else:
            await message.channel.send("You do not have a profile. Create one by typing !start")
    else:
        await message.channel.send(message.author.mention + " You do not have a profile yet! create one.")

async def update_quest_progress(message, player, quest_collection, action_name, monster_name=None):
    # Find the player's data
    player_data = player.find_one({"id": message.author.id})

    if not player_data:
        await message.channel.send("You do not have a profile. Create one by typing !start")
        return

    # Initialize quest_cooldowns if it doesn't exist
    if 'quest_cooldowns' not in player_data:
        player_data['quest_cooldowns'] = {}

    # Check if the quest is on cooldown
    if action_name in player_data['quest_cooldowns']:
        current_time = time.time()
        cooldown_end_time = player_data['quest_cooldowns'][action_name]

        if current_time < cooldown_end_time:
            remaining_cooldown = cooldown_end_time - current_time
            return
        else:
            # Remove the cooldown since it has expired
            del player_data['quest_cooldowns'][action_name]
            player.update_one({"id": message.author.id}, {"$unset": {"quest_cooldowns." + action_name: ""}})
            # Additionally, reset the progress here
            quest_collection.update_one({"name": action_name}, {
                "$set": {"player_progress": {"player_id": str(message.author.id), "progress": 0}}})
            await message.channel.send("Cooldown over. You can start the quest again.")
    # Find the quest associated with the action

    quest = quest_collection.find_one({"name": action_name})
    if not quest:
        await message.channel.send(f"Quest '{action_name}' not found.")
        return

    # Initialize player progress for the quest
    player_progress = quest.get('player_progress', {})
    if not player_progress:
        player_progress = {"player_id": str(message.author.id), "progress": 0}

    # Increment player's progress for the quest if the quest is not completed
    required_progress = int(quest.get('required_progress', 0))
    if player_progress.get('progress', 0) < required_progress:

        if action_name == "Kill Monsters":
            # Increment player's progress for the quest if the monster matches the required type
            if monster_name == quest.get("monster_name"):
                player_progress['progress'] = player_progress.get('progress', 0) + 1
        elif action_name == "Adventures":
            if monster_name == quest.get("monster_name"):
                player_progress['progress'] = player_progress.get('progress', 0) + 1
        elif action_name == "Basic Resting":
            # Increment player's progress for the quest
            player_progress['progress'] = player_progress.get('progress', 0) + 1
        elif action_name == "Cave Exploration Quest":
            player_progress['progress'] = player_progress.get('progress', 0) + 1
        # Update quest progress in the quest collection
        quest_collection.update_one({"name": action_name}, {"$set": {"player_progress": player_progress}})

        # Send message indicating progress
        await message.channel.send(
            f"You made progress in the quest '{action_name}': {player_progress['progress']}/{required_progress}")

        # Check if the quest is completed after incrementing the progress
        if player_progress.get('progress', 0) >= required_progress:
            # Block the quest by setting its cooldown timestamp
            current_time = time.time()
            player_data['quest_cooldowns'][action_name] = current_time + quest.get('cooldown_duration', 0)
            player.update_one({"id": message.author.id},{"$set": {"quest_cooldowns": player_data['quest_cooldowns']}})
            gold_reward = int(quest.get('gold', 0))
            xp_reward = quest["XP"]
            player.update_one({"id": message.author.id}, {"$inc": {"gold": gold_reward}})
            await level(message.author.id, xp_reward, player_data["XP"])
            await message.channel.send(f"Quest progress reached for the quest : {action_name} you gained the rewards that are : {gold_reward} <:money:815310399754600530> **golds**, and {xp_reward} **XP**. You can't continue this quest until the cooldown is over..")

async def code_cmds(message, player, code, main):
    if player.count_documents({"id": message.author.id}) != 0:
        a = player.find_one({"id": message.author.id})
        cd = main.replace("code ", "")
        if code.count_documents({"code": cd}) != 0:
            if cd in a["codes"]:
                await message.channel.send(
                    message.author.name + " You already used this code.")
                return
            docs = code.find_one({"code": cd})
            codes = a["codes"]
            codes.append(cd)
            player.update_one({"id": message.author.id}, {"$set": {"codes": codes}})
            r = ""
            if docs["gold"] != "None":
                r += " You gained **" + str(docs["gold"]) + "**\n"
                player.update_one({"id": message.author.id}, {"$inc": {"gold": docs["gold"]}})
            if docs["rank+"] != "None":
                r += "Be proud you won this **" + docs["rank+"] + "** Title\n"
                player.update_one({"id": message.author.id}, {"$set": {"rank+": docs["rank+"]}})
            if docs["spin"] != "None":
                r += "You won **" + str(
                    docs["spin"]) + "** spin <:favoris:815309799872266270> \n"
                player.update_one({"id": message.author.id}, {"$inc": {"spin": docs["spin"]}})
            if docs["xp"] != "None":
                r += "You are stronger you won **" + str(docs["xp"]) + "**\n"
                await level(message.author.id, docs["xp"], a["XP"])
            if r == "":
                r = "You didn't win anything."
            await message.channel.send(r)

    else:
        await message.channel.send(message.author.mention + " You do not have a profile yet! Create one.")

async def show_shop(message, player):
    result = ""
    docs = player.find_one({"id": message.author.id})
    for b in shop.find({"area": docs["area"]}):
        result += b["item"] + ": **" + str(b["price"]) + "** **Golds** <:money:815310399754600530> " + "\n\n"

    embed = discord.Embed()
    embed.title = "Welcome to my shop Traveller! For The area " + str(docs["area"]) + "!"
    embed.colour = discord.Colour.dark_blue()
    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/815200866523938848/815220311024730112/Shop.png")

    embed.description = result

    await message.channel.send(embed=embed)

async def show_inv(message):
    r = ""
    docs = inv.find_one({"id": message.author.id})
    for i in docs["inventory"]:
        args = i.split(":")
        if args[0] == "Heal Potion":
            args[0] += " <:healpotion:815216307590004777>"
        elif "Ring" in args[0]:
            args[0] += " <:Ring:815316578265858109>"
        r += args[0] + " x" + args[1] + "\n\n"

    embed = discord.Embed()
    embed.title = " User's Inventory"
    embed.colour = discord.Colour.dark_gold()
    embed.set_thumbnail(url=message.author.avatar.url)
    embed.description = r

    await message.channel.send(message.author.mention, embed=embed)

async def equip_object(message, player, main):
    he = main.replace("equip ", "")
    docs = inv.find_one({"id": message.author.id})
    verif = separt(docs["inventory"])
    if he in verif:
        docs2 = shop.find_one({"item": he})
        docs3 = player.find_one({"id": message.author.id})
        if docs2["slot"] == 1:

            if docs3["slot1"] != "None":
                await message.channel.send("You already have an item equipped.")
                return

            player.update_one({"id": message.author.id}, {"$set": {"slot1": he},
                                                          "$inc": {"attack": docs2["attack"],
                                                                   "defense": docs2["defense"]}})
        elif docs2["slot"] == 2:

            if docs3["slot2"] != "None":
                await message.channel.send("You already have an item equipped")
                return

            player.update_one({"id": message.author.id}, {"$set": {"slot2": he},
                                                          "$inc": {"attack": docs2["attack"],
                                                                   "defense": docs2["defense"]}})
        else:
            await message.channel.send("This item isn't equipable.")
            return
    else:
        await message.channel.send("This item does not exist.")
        return
    await message.channel.send(
        message.author.mention + " You succefully equipped this item. \n\nAnd you now have +**" + str(
            docs2["attack"]) + "** attack, and +**" + str(docs2["defense"]) + "** defense.")

async def unequip_object(message, player, main):
    he = main.replace("uneq ", "")
    docs = inv.find_one({"id": message.author.id})
    verif = separt(docs["inventory"])
    if he in verif:
        docs2 = shop.find_one({"item": he})
        docs3 = player.find_one({"id": message.author.id})
        if docs2["slot"] == 1:
            if docs3["slot1"] == "None":
                await message.channel.send("This item is no longer equipped")
                return
            player.update_one({"id": message.author.id}, {"$set": {"slot1": "None"},
                                                          "$inc": {"attack": - docs2["attack"],
                                                                   "defense": - docs2["defense"]}})
        elif docs2["slot"] == 2:
            if docs3["slot2"] == "None":
                await message.channel.send("This item is no longer equipped")
                return
            player.update_one({"id": message.author.id}, {"$set": {"slot2": "None"},
                                                          "$inc": {"attack": - docs2["attack"],
                                                                   "defense": - docs2["defense"]}})
        else:
            await message.channel.send("This item is not unequipable.")
            return

async def buy_object(message, player, main):
    item = main.replace("buy ", "").split(" ", maxsplit=1)
    try:
        n = item[0]
        ite = item[1]
    except:
        await message.channel.send(
            "Warning, bad command, (! buy <number of items> <item name with caps if needed!>)")
        return
    docs = player.find_one({"id": message.author.id})
    if shop.count_documents({"item": ite, "area": docs["area"]}) != 0:
        docs2 = shop.find_one({"item": ite, "area": docs["area"]})
        r = docs2["price"] * int(n)
        if docs["gold"] > r:
            player.update_one({"id": message.author.id}, {"$inc": {"gold": - r}})
            z = False
            z2 = 0
            docs3 = inv.find_one({"id": message.author.id})

            for i in docs3["inventory"]:
                args = i.split(":")
                if args[0] == ite:
                    z = True
                    break
                z2 += 1
            newinv = docs3["inventory"]
            if z:
                newinv[z2] = ite + ":" + str(int(docs3["inventory"][z2].split(":")[1]) + int(n))
                inv.update_one({"id": message.author.id}, {"$set": {"inventory": newinv}})

            else:
                newinv.append(ite + ":" + n)
                inv.update_one({"id": message.author.id}, {"$set": {"inventory": newinv}})

            await message.channel.send(message.author.mention + " You bought " + n + " **" + ite + "**")

        else:
            await message.channel.send(" You are poor mah man.")


    else:
        await message.channel.send(" This item does not exit. Don't forget the Maj <**Stick** for example> copy and paste the name if needed.")

async def sell_object(message, player, main):
    if player.count_documents({"id": message.author.id}) != 0:
        a = inv.find_one({"id": message.author.id})
        ite = main.replace("sell ", "")

        docs = shop.find_one({"item": ite})
        price = docs["price"] / 2
        price = int(price)
        z = False
        z2 = 0
        for i in a["inventory"]:
            args = i.split(":")
            if args[0] == ite:
                z = True
                nb = int(args[1]) - 1
                break
            z2 += 1
        newinv = a["inventory"]
        if z:
            player.update_one({"id": message.author.id}, {"$inc": {"gold": + price}})
            if nb <= 0:
                result = []
                for s in a["inventory"]:
                    h = s.split(":")
                    if h[0] != ite:
                        result.append(s)
                newinv = result


            else:

                newinv[z2] = ite + ":" + str(int(a["inventory"][z2].split(":")[1]) - 1)
            inv.update_one({"id": message.author.id}, {"$set": {"inventory": newinv}})
            await message.channel.send(
                message.author.mention + " You successfully sold **" + ite + "** For " + str(
                    price) + " <:money:815310399754600530> Golds.")

        else:
            await message.channel.send(message.author.mention + " You do not have this item. Looser")

    else:
        await message.channel.send(message.author.mention + " You do not have a profile yet! Create one.")

async def show_areas(message, player):
    docs = player.find_one({"id": message.author.id})
    result = ""
    embed = discord.Embed()
    arean = {}
    for b in area.find({}):
        arean[b["area"]] = {"name": str(b["name"]), "level": b["level"]}
    arealist = sorted(arean)
    for s in arealist:
        b = arean[s]
        if s == docs["area"]:
            result += str(b["name"]) + " -- You are here\n\n"
        else:
            result += str(b["name"]) + " -- You need to be level **" + str(
                b["level"]) + "** To enter this area." + "\n\n"
        embed.title = "Area List"
        embed.colour = discord.Colour.blue()
        embed.description = result
    await message.channel.send(message.author.mention, embed=embed)

async def go_area(message, player, main):
    var = main.replace("area ", "")
    docs = player.find_one({"id": message.author.id})

    if area.count_documents({"area": int(var)}) != 0:
        area_info = area.find_one({"area": int(var)})
        # Check if 'area_cleared' exists in docs, if not set it to a default value (e.g., 0)
        area_cleared = docs.get("area_cleared", 0)

        if area_cleared >= area_info["area"] - 1:
            if docs["area"] == int(var):
                await message.channel.send(
                    message.author.mention + "You are already in **" + area_info["name"] + "**.")
                return
            player.update_one({"id": message.author.id}, {"$set": {"area": int(var)}})
            await message.channel.send(
                message.author.mention + "You've walked to **" + area_info["name"] + "** enjoy your stay.")
        else:
            await message.channel.send(
                message.author.mention + "You cannot move to **" + area_info[
                    "name"] + "** until you defeat the boss of the current area.")
    else:
        await message.channel.send("This area does not exist.")

async def heal_self(message, player):
    if player.count_documents({"id": message.author.id}):
        docs = inv.find_one({"id": message.author.id})
        lil = separt(docs["inventory"])
        verif = False
        for i in lil:
            if i == "Health Potion":
                verif = True
                docs2 = player.find_one({"id": message.author.id})
                var = docs2["life"].split("/")
                if var[0] == var[1]:
                    await message.channel.send(message.author.mention + " You already have max hp.")
                    return
                life = int(var[0]) + 50
                if int(life) > int(var[1]):
                    life = int(var[1])
                player.update_one({"id": message.author.id}, {"$set": {"life": str(life) + "/" + var[1]}})

                item = "Health Potion"
                k = a_item(message.author.id, item)
                if k[0]:
                    newInv = docs["inventory"]

                    newInv[k[1]] = item + ":" + str(int(docs["inventory"][k[1]].split(":")[1]) - 1)

                    inv.update_one({"id": message.author.id}, {"$set": {"inventory": newInv}})

                    if int(docs["inventory"][k[1]].split(":")[1]) == 0:
                        newInv.remove(item + ":" + str(0))

                        inv.update_one({"id": message.author.id}, {"$set": {"inventory": newInv}})
                    await message.channel.send(
                        message.author.mention + " You successfully healed your self by using a " + item + " you now have **" + str(
                            life) + "** :heart: HP.")
                    return
        if verif == False:
            await message.channel.send(message.author.mention + "You don't own a potion.")
    else:
        await message.channel.send(message.author.mention + " You do not have a profile yet! Create one.")

async def update_player_area_cleared(player, new_area, message):
    # Assuming 'player_collection' is your MongoDB collection
    try:
        result = player.update_one(
            {"id": message.author.id},
            {"$set": {"area_cleared": new_area}}
        )
        if result.modified_count == 0:
            await message.channel.send(f"{message.author.mention} No update needed; area already set.")
        else:
            await message.channel.send(f"{message.author.mention} Area cleared updated to {new_area}.")
    except Exception as e:
        await message.channel.send(f"Error updating player area: {str(e)}")

async def boss_fight_logic(player, boss_info, message):
    docs = player.find_one({"id": message.author.id})
    player_life = int(docs["life"].split("/")[0])
    boss_life = boss_info["life"]
    player_attack = docs["attack"]
    boss_defense = boss_info["defense"]
    boss_attack = boss_info["attack"]
    player_defense = docs["defense"]

    # Fight loop
    while True:
        # Player attacks boss
        damage_to_boss = max(player_attack - boss_defense, 0)
        boss_life -= damage_to_boss
        if boss_life <= 0:
            win = "p"
            break

        # Boss attacks player
        damage_to_player = max(boss_attack - player_defense, 0)
        player_life -= damage_to_player
        if player_life <= 0:
            win = "m"
            break

    if win == "p":
        # Player wins
        xp_reward = boss_info["XP"]
        gold_reward = boss_info["gold"]
        new_life = f"{player_life}/{docs['life'].split('/')[1]}"  # Keeping the max life the same

        # Update the player's stats with XP, gold, and increment the area
        player.update_one({"id": message.author.id}, {
            "$set": {"life": new_life},
            "$inc": {"gold": gold_reward}
        })
        await level(message.author.id, xp_reward, docs["XP"])
        # Update the message to reflect the fight outcome
        await message.channel.send(f"{message.author.mention} You defeated **{boss_info['name']}**, won {xp_reward} XP, \n"f"{gold_reward} gold and you have **{new_life}** HP left! :heart:")
        new_area_cleared = boss_info['area']
        await update_player_area_cleared(player, new_area_cleared, message)

    elif win == "m":
        gold_lost = docs["gold"] // 2  # Assuming the player loses half their gold when defeated
        new_life = "0/" + docs["life"].split('/')[1]  # Player is defeated, so life is set to 0

        # Update the player's stats, reducing gold and setting life to 0
        player.update_one({"id": message.author.id}, {
            "$set": {"life": new_life},
            "$inc": {"gold": -gold_lost}
        })

        # Update the message to reflect the fight outcome
        await message.channel.send(f"{message.author.mention} You were defeated by **{boss_info['name']}**. "
                    f"You lost {gold_lost} gold and now have **{new_life}** HP left. **{boss_info['name']}** Had {boss_life} HP remaining. Try again once you're stronger! "
        )

async def boss_fight(message, player, bot):
    player_info = player.find_one({"id": message.author.id})
    current_area = player_info["area"]
    boss_info = boss.find_one({"area": current_area})
    boss_name = boss_info["name"]
    boss_level = boss_info["level"]

    # Check if the player has already cleared this area
    area_cleared = player_info.get('area_cleared', 0)
    if current_area <= area_cleared:
        await message.channel.send(
            f"{message.author.mention} You have already defeated the boss of **{boss_info['name']}**. Continue your Adventure.")
        return

    if player_info["lvl"] >= boss_info["level"]:
        # Create an embed with boss stats
        embed = discord.Embed(title=f"{boss_name} - Level {boss_level}",
                              description="Do you want to challenge the boss?")
        embed.add_field(name="Life", value=str(boss_info["life"]))
        embed.add_field(name="Attack", value=str(boss_info["attack"]))
        embed.add_field(name="Defense", value=str(boss_info["defense"]))
        embed.add_field(name="XP", value=str(boss_info["XP"]))
        embed.add_field(name="Gold", value=str(boss_info["gold"]))

        boss_message = await message.channel.send(embed=embed)
        await boss_message.add_reaction('✅')  # Yes
        await boss_message.add_reaction('❌')  # No

        def check(reaction, user):
            return user == message.author and reaction.message.id == boss_message.id and str(reaction.emoji) in ['✅','❌']

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(reaction.emoji) == '✅':
                await message.channel.send(f"**{message.author.mention} You have chosen to fight the boss!**")
                await boss_fight_logic(player, boss_info, message)
                await message.clear_reactions()
            elif str(reaction.emoji) == '❌':
                await message.channel.send(f"**{message.author.mention} You have decided not to fight the boss right now. Coward...**")
                await message.clear_reactions()


        except asyncio.TimeoutError:
            await message.channel.send(f"{message.author.mention} You took too long to decide.")
        except Exception as e:
            print(f"Caught an exception: {type(e).__name__} - {str(e)}")

    else:
        await message.channel.send(
            f"{message.author.mention} You are not high enough level to challenge the boss of this area. You need to be level {boss_level} to fight {boss_name}.")

async def adventure_hunt(message, player, adventure_bosses_collection, cooldowns):
    if player.count_documents({"id": message.author.id}) != 0:
        is_cool, remaining_time = await cool("adventure", cooldowns, cooldown_times)
        if not is_cool:
            await message.channel.send(f"You've already went on an adventure, try again in {remaining_time} seconds.")
            return
        docs = player.find_one({"id": message.author.id})

        # If no bosses are eligible, inform the player and return
        player_level = docs["lvl"]
        # Query MongoDB for potential bosses that are of appropriate level and rarity
        potential_bosses = adventure_bosses_collection.find({"level": {"$lte": player_level}, "rare": 1})
        potential_bosses = list(potential_bosses)  # Convert the cursor to a list

        if not potential_bosses:
            await message.channel.send("**No High lvl Monsters are available for you to fight at your current level.**")
            return

        # Randomly select a boss from the list of potential bosses
        boss_info = random.choice(potential_bosses)
        gold_boss = str(boss_info["gold"])

        # Create an embed with the boss details
        embed = discord.Embed(title="High lvl Danger Encounter!", description="Prepare to fight!")
        embed.add_field(name="Name", value=boss_info["name"], inline=False)
        embed.add_field(name="Level", value=str(boss_info["level"]), inline=True)
        embed.add_field(name="Life", value=str(boss_info["life"]), inline=True)
        embed.add_field(name="Attack", value=str(boss_info["attack"]), inline=True)
        embed.add_field(name="Defense", value=str(boss_info["defense"]), inline=True)
        embed.add_field(name="Xp", value=str(boss_info["XP"]), inline=True)
        embed.add_field(name="Gold", value=gold_boss, inline=True)
        embed.set_footer(text="React with ✅ to fight or ❌ to flee.")

        boss_message = await message.channel.send(embed=embed)
        await boss_message.add_reaction('✅')
        await boss_message.add_reaction('❌')

        def check(reaction, user):
            return user == message.author and str(reaction.emoji) in ['✅', '❌']

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(reaction.emoji) == '✅':
                await message.channel.send(f"**{message.author.mention} You have chosen to fight the Monster!**")
                player_life = int(docs["life"].split('/')[0])
                boss_life = boss_info["life"]
                while True:
                    # Player attacks boss
                    damage_to_boss = max(docs["attack"] - boss_info["defense"], 0)
                    boss_life -= damage_to_boss
                    if boss_life <= 0:
                        win = "player"
                        break

                    # Boss attacks player
                    damage_to_player = max(boss_info["attack"] - docs["defense"], 0)
                    player_life -= damage_to_player
                    if player_life <= 0:
                        win = "boss"
                        break

                if win == "player":
                    # Player wins
                    xp_reward = boss_info["XP"]
                    gold_reward = boss_info["gold"]
                    new_life = f"{player_life}/{docs['life'].split('/')[1]}"  # Keeping the max life the same

                    # Update the player's stats with XP, gold, and increment the area
                    player.update_one({"id": message.author.id}, {
                        "$set": {"life": new_life},
                        "$inc": {"gold": gold_reward}
                    })
                    await level(message.author.id, xp_reward, docs["XP"])
                    # Update the message to reflect the fight outcome
                    await message.channel.send(f"{message.author.mention} You defeated **{boss_info['name']}**, won {xp_reward} XP, \n"f"{gold_reward} gold and you have **{new_life}** HP left! :heart:")
                    active_quests = quest_collection.find({"player_progress": {"$exists": True}})
                    for quest in active_quests:
                        required_monster = quest.get("monster_name")
                        if boss_info['name'] == required_monster:  # Use the name of the defeated monster
                            # Update quest progress for the player
                            await update_quest_progress(message, player, quest_collection, quest["name"], boss_info['name'])

                elif win == "boss":
                    gold_lost = docs["gold"] // 2  # Assuming the player loses half their gold when defeated
                    new_life = "0/" + docs["life"].split('/')[1]  # Player is defeated, so life is set to 0

                    # Update the player's stats, reducing gold and setting life to 0
                    player.update_one({"id": message.author.id}, {
                        "$set": {"life": new_life},
                        "$inc": {"gold": -gold_lost}
                    })

                    # Update the message to reflect the fight outcome
                    await message.channel.send(
                        f"{message.author.mention} You were defeated by **{boss_info['name']}**. "
                        f"You lost {gold_lost} gold and now have **{new_life}** HP left. **{boss_info['name']}** Had {boss_life} HP remaining. Try again once you're stronger! ")
            elif str(reaction.emoji) == '❌':
                await message.channel.send(f"**{message.author.mention} You have decided not to fight the monster right now. Coward...**")
                await boss_message.delete()  # Delete the message with the embed
                return  # Return immediately after deletion to avoid further operations on the deleted message

        except asyncio.TimeoutError:
            await message.channel.send(f"{message.author.mention} You took too long to decide.")
        except discord.NotFound:
            # This handles the case if the message was somehow deleted before this point
            pass
        finally:
            try:
                await boss_message.clear_reactions()
            except discord.NotFound:
                # If the message has already been deleted or not found, this will handle the exception
                pass
    else:
        await message.channel.send(message.author.mention + "You do not have a profile yet! Create one.")

async def show_monsters(message, player):
    docs = player.find_one({"id": message.author.id})
    if not docs:
        await message.channel.send(f"{message.author.mention} You do not have a profile yet! Create one.")
        return

    player_area = docs["area"]  # Assuming the player's current area is stored in the 'area' field

    # Initialize the embed
    embed = discord.Embed(title="Monsters in Your Area", colour=discord.Colour.blue())

    # Fetch monsters that are in the player's current area
    monsters_in_area = monster.find({"area": player_area})
    monster_list = list(monsters_in_area)  # Convert cursor to list

    if not monster_list:
        embed.description = "No monsters found in your current area."
    else:
        # Building a string that lists each monster's details
        result = ""
        for monster_data in monster_list:
            result += f"{monster_data['name']} - Rarity: {monster_data['rare']}, Attack: {monster_data['attack']}, Defense: {monster_data['defense']}\n"

        embed.description = result.strip()  # Remove trailing newline for cleaner presentation

    # Send the embed message to the channel
    await message.channel.send(message.author.mention, embed=embed)

async def show_HighMonsters(message, player):
    docs = player.find_one({"id": message.author.id})
    if not docs:
        await message.channel.send(f"{message.author.mention} You do not have a profile yet! Create one.")
        return

    player_area = docs["area"]  # Assuming the player's current area is stored in the 'area' field

    # Initialize the embed
    embed = discord.Embed(title="High lvl Monsters in Your Area", colour=discord.Colour.dark_blue())

    # Fetch monsters that are in the player's current area
    monsters_in_area = adventure_bosses_collection.find({"area": player_area})
    monster_list = list(monsters_in_area)  # Convert cursor to list
    if not monster_list:
        embed.description = "No High lvl Monsters found in your current area."
    else:
        # Building a string that lists each monster's details
        result = ""
        for monster_data in monster_list:
            result += f"{monster_data['name']} - Rarity: {monster_data['rare']}, Attack: {monster_data['attack']}, Defense: {monster_data['defense']}\n"

        embed.description = result.strip()  # Remove trailing newline for cleaner presentation

        # Send the embed message to the channel
    await message.channel.send(message.author.mention, embed=embed)

async def view_bank(message, player):
    player_data = player.find_one({"id": message.author.id})
    if not player_data or "bank" not in player_data:
        await message.channel.send("No bank profile found. Please initialize your bank.")
        return

    bank = player_data['bank']
    embed = discord.Embed(title="Bank Details", color=discord.Color.gold())
    embed.add_field(name="Bank Level", value=bank["bank_level"], inline=True)
    embed.add_field(name="Gold in Bank", value=f"{bank['gold_in_bank']} / {bank['bank_capacity']}", inline=True)
    embed.set_thumbnail(url=message.author.avatar)

    await message.channel.send(message.author.mention, embed=embed)

async def deposit_gold(message, main, player):
    player_data = player.find_one({"id": message.author.id})
    if not player_data or "bank" not in player_data:
        await message.channel.send("No bank profile found. Please initialize your bank.")
        return

    try:
        amount_int = int(main.replace("deposit ", "").strip())  # Parse and convert the deposit amount
    except ValueError:
        await message.channel.send("Invalid amount. Please enter a valid number.")
        return

    bank = player_data['bank']
    if bank['gold_in_bank'] + amount_int > bank['bank_capacity']:
        await message.channel.send("Cannot deposit: bank capacity exceeded.")
        return
    if player_data['gold'] < amount_int:
        await message.channel.send("You do not have enough gold to deposit.")
        return

    # Update bank with new deposit, increase total deposited
    new_total_deposited = bank['total_deposited'] + amount_int
    level_up_threshold = 5000 * bank['bank_level']  # 5000 gold more needed for each level

    # Update the database
    update_query = {
        "$inc": {
            "bank.gold_in_bank": amount_int,
            "gold": -amount_int,
            "bank.total_deposited": amount_int
        }
    }

    # Check if the new total deposited qualifies the bank for a level up
    if new_total_deposited >= level_up_threshold:
        new_level = bank['bank_level'] + 1
        new_capacity = bank['bank_capacity'] + 2500
        update_query["$set"] = {
            "bank.bank_level": new_level,
            "bank.bank_capacity": new_capacity
        }
        await message.channel.send(f"**Congratulations! Your bank has leveled up to level {new_level}. New capacity: {new_capacity} gold.**")

    player.update_one({"id": message.author.id}, update_query)
    await message.channel.send(f"Deposited {amount_int} gold. New balance: {bank['gold_in_bank'] + amount_int} gold, total deposited: {new_total_deposited}.")

async def withdraw_gold(message, main, player):
    player_data = player.find_one({"id": message.author.id})
    gold_player = str(player_data["gold"])
    amount_str = main.replace("withdraw ", "").strip()  # Remove the command part and any extra whitespace
    is_cool, remaining_time = await cool("withdraw", cooldowns, cooldown_times)
    if not is_cool:
        await message.channel.send(
            f"**You've already Withdrew try again in {remaining_time} seconds.**")
        return

    try:
        amount_int = int(amount_str)  # Convert the string to an integer
    except ValueError:
        await message.channel.send("**Invalid amount. Please enter a valid number.**")
        return

    if not player_data or "bank" not in player_data:
        await message.channel.send("**No bank profile found. Please initialize your bank.**")
        return

    bank = player_data['bank']
    if amount_int > bank['gold_in_bank']:
        await message.channel.send("**Cannot withdraw: insufficient gold in bank.**")
        return

    # Update gold in bank and increase player's gold
    player.update_one(
        {"id": message.author.id},
        {"$inc": {"bank.gold_in_bank": -amount_int, "gold": amount_int}}
    )
    new_balance = bank['gold_in_bank'] - amount_int  # Calculate new balance before sending the message
    await message.channel.send(f"**Withdrew {amount_int} gold. Remaining bank balance: {new_balance} gold.**")

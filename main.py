from Fonctions.functions import *

cooldowns = {}

cooldown_seconds = 3


@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="Welcome to Magius"))
    print("ready")



@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.author == bot.user:
        return

    if type(message.channel) == discord.DMChannel:
        return

    if message.author == bot.user:
        return

    if message.author == bot.user or isinstance(message.channel, discord.DMChannel):
        return

    current_time = time.time()
    user_id = message.author.id

    if user_id in cooldowns and current_time - cooldowns[user_id] < cooldown_seconds:
        await message.channel.send("You're doing that too often. Please wait a bit!")
        return
    else:
        # Update last command execution time
        cooldowns[user_id] = current_time

    prefix = "! "

    if message.content.startswith(prefix):  # pour check si le message commence avec le prefix
        main = message.content.replace(prefix, "")

        if main in ("profile", "p", "P"):
            await show_profile(message, player, area)

        elif main.startswith("profile "):
            await show_User_Profile(message, player, area)
        elif main == "start":
            await start_game(message, player)
        elif main == "spin":
            await spin_race(message, player, race)
        elif main == "hunt":
            await hunt_adv(message, player, level, cooldowns)
        elif main in ("cave exploration", "ce"):
            await cave_explo(message, player, cooldowns)
        elif main == "mine":
            await mine_explo(message, player, cooldowns)
        elif main in ("cd", "cooldowns", "Cooldowns"):
            await show_commands_with_cooldowns(cooldowns, cooldown_times, message)
        elif main in ("rare spin", "rs", "Rare Spin"):
            await spin_RareRace(message, player, race)
        elif main in ("epic spin", "es", "Epic Spin"):
            await spin_EpicRace(message, player, race)
        elif main == "help":
            await help_please(message, player)
        elif main == "merge":
            await merge_spins(message, player)
        elif main in ("mergeEpic", "me"):
            await merge_epic(message, player)
        elif main.startswith("del "):
            await del_user(message, player, main)
        elif main in ("leaderboard", "l"):
            await show_leaderboard(message, player)
        elif main.startswith("use "):
            await use_form(message, player, race, main)
        elif main == "forms":
            await show_forms(message, player)
        elif main == "races":
            await show_races(message, player)
        elif main == "rest":
            await rest_heal(message, player)
        elif main == "quest":
            await show_quest_board(message, player, quest_collection)
        elif main == "cmds":
            await list_commands(message, bot)
        elif main.startswith("code "):
            await code_cmds(message, player, code, main)
        elif main == "shop":
            await show_shop(message, player)
        elif main in ("inventory", "i"):
            await show_inv(message)
        elif main.startswith("equip "):
            await equip_object(message, player, main)
        elif main.startswith("uneq "):
            await unequip_object(message, player, main)
        elif main.startswith("buy "):
            await buy_object(message, player, main)
        elif main.startswith("sell "):
            await sell_object(message, player, main)
        elif main == "areas":
            await show_areas(message, player)
        elif main.startswith("area "):
            await go_area(message, player, main)
        elif main == "heal":
            await heal_self(message, player)
        elif main == "boss":
            await boss_fight(message, player, bot)
        elif main in ("adventure", "adv"):
            await adventure_hunt(message, player, adventure_bosses_collection, cooldowns)
        elif main == "monsters":
            await show_monsters(message, player)
        elif main in ("HighMonsters", "Hm"):
            await show_HighMonsters(message, player)
        elif main == "bank":
            await view_bank(message, player)
        elif main.startswith("deposit "):
            await deposit_gold(message, main, player)
        elif main.startswith("withdraw "):
            await withdraw_gold(message, main, player)


bot.run(Token)
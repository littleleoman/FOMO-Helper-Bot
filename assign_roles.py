from discord.ext.commands import Bot
from discord.ext.commands import has_role
import discord
from discord.utils import get
from discord.errors import LoginFailure, HTTPException
from discord.embeds import Embed 
import asyncio
BOT_PREFIX = ("?", "!")
client = discord.ext.commands.Bot(command_prefix=BOT_PREFIX)#, description=BOT_DESCRIPTION#)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.change_presence(game=discord.Game(name='!help'), status=None,afk=False)

@client.command(name='gogogo',pass_context=True)
async def add_roles(ctx):
    server = client.get_server('355178719809372173')
    members = []

    for member in server.members:
        data = dict()
        data['roles'] = list()
        for role in member.roles:
            data['roles'].append(role.name)
        data['member'] = member
        members.append(data)
    
    memberRole = get(server.roles, name='✓')
    adminRole = get(server.roles, name='⚛️')

    for member in members:
        if "Member" in member['roles'] or "Lifetime" in member['roles'] or "Collaborator" in member['roles'] or "F&F" in member['roles']:
            await client.add_roles(member['member'], memberRole)
            print("ADDED MEMBER ROLE TO: " + str(member['member'].name))
        elif "Admin" in member['roles'] or "Dev" in member['roles'] or "Moderator" in member['roles'] or "Support" in member['roles']:
            await client.add_roles(member['member'], adminRole)
            print("ADDED STAFF ROLE TO: " + str(member['member'].name))
        else:
            continue
    print("FINISHED")
TOKEN = 'NDY5MzI2NjY1OTk5MTg3OTY4.DyQ4Uw.u6xY1ispPXqIoO_ZphQZmYiriHc'
client.run(TOKEN)



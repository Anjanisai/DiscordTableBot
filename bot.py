import discord
from discord.ext import commands
from tabulate import tabulate
from dotenv import load_dotenv
import os, json
import shlex
from firestore_tables import (
    save_table, get_table, delete_table, get_guild_tables,
    add_table_row, update_table_columns, update_table_rows,
    clear_table_rows, table_exists
)
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# === Helper Functions ===
def parse_row_input(input_str: str) -> list:
    """Parse row input that may contain quoted values with spaces"""
    try:
        if '"' in input_str or "'" in input_str:
            return shlex.split(input_str)
        return input_str.split()
    except Exception as e:
        logger.error(f"Error parsing row input: {e}")
        raise ValueError("Error parsing input. Use quotes for values with spaces.")

# === Commands ===
@bot.command(name="newtable", help="Create a new table")
async def newtable(ctx, tablename: str):
    guild_id = str(ctx.guild.id)
    if table_exists(guild_id, tablename):
        await ctx.send(f"❌ Table '{tablename}' already exists!")
        return
    
    if save_table(guild_id, tablename, [], []):
        await ctx.send(f"✅ Table '{tablename}' created successfully!")
    else:
        await ctx.send("❌ Failed to create table. Please try again.")

@bot.command(name="addcol", help="Add a column to a table")
async def addcol(ctx, tablename: str, *, colname: str):
    guild_id = str(ctx.guild.id)
    table_data = get_table(guild_id, tablename)
    if not table_data:
        await ctx.send(f"❌ Table '{tablename}' not found.")
        return
    
    columns = table_data["columns"]
    if colname in columns:
        await ctx.send(f"❌ Column '{colname}' already exists in table '{tablename}'.")
        return
    
    columns.append(colname)
    rows = table_data["rows"]
    
    # Add empty value for the new column to all existing rows
    for row in rows:
        row.append("")
    
    if save_table(guild_id, tablename, columns, rows):
        await ctx.send(f"✅ Column '{colname}' added to table '{tablename}'.")
    else:
        await ctx.send("❌ Failed to add column. Please try again.")

@bot.command(name="addrow", help="Add a row to a table")
async def addrow(ctx, tablename: str, *, row_data: str):
    guild_id = str(ctx.guild.id)
    
    try:
        values = parse_row_input(row_data)
        table_data = get_table(guild_id, tablename)
        
        if not table_data:
            await ctx.send(f"❌ Table '{tablename}' not found.")
            return
        
        if len(values) != len(table_data["columns"]):
            await ctx.send(
                f"❌ Expected {len(table_data['columns'])} values, got {len(values)}.\n"
                f"Columns: {', '.join(table_data['columns'])}"
            )
            return
        
        if add_table_row(guild_id, tablename, values):
            await ctx.send(f"✅ Row added to '{tablename}':\n`{values}`")
        else:
            await ctx.send("❌ Failed to add row. Please try again.")
            
    except ValueError as e:
        await ctx.send(f"❌ {str(e)}\nExample: `!addrow table \"value with spaces\" 42`")
    except Exception as e:
        logger.error(f"Error in addrow: {e}")
        await ctx.send("❌ An error occurred. Please check your input and try again.")

@bot.command(name="showtable", help="Display a table")
async def showtable(ctx, tablename: str):
    guild_id = str(ctx.guild.id)
    table_data = get_table(guild_id, tablename)
    
    if not table_data:
        await ctx.send(f"❌ Table '{tablename}' not found.")
        return
    
    columns = table_data.get("columns", [])
    rows = table_data.get("rows", [])
    
    if not columns:
        await ctx.send(f"ℹ️ Table '{tablename}' has no columns defined.")
        return
    
    if not rows:
        await ctx.send(f"ℹ️ Table '{tablename}' is empty.")
        return
    
    # Format the table
    table_str = tabulate(rows, headers=columns, tablefmt="github")
    
    # Discord has a 2000 character limit per message
    if len(table_str) > 1900:
        # Split into chunks if too large
        chunks = [table_str[i:i+1900] for i in range(0, len(table_str), 1900)]
        for chunk in chunks:
            await ctx.send(f"```{chunk}```")
    else:
        await ctx.send(f"📊 **{tablename}**\n```{table_str}```")

@bot.command(name="delrow", help="Delete a row from a table")
async def delrow(ctx, tablename: str, row_num: int):
    guild_id = str(ctx.guild.id)
    table_data = get_table(guild_id, tablename)
    
    if not table_data:
        await ctx.send(f"❌ Table '{tablename}' not found.")
        return
    
    rows = table_data["rows"]
    if row_num < 1 or row_num > len(rows):
        await ctx.send(f"❌ Invalid row number. Table has {len(rows)} rows.")
        return
    
    removed_row = rows.pop(row_num - 1)
    if save_table(guild_id, tablename, table_data["columns"], rows):
        await ctx.send(f"✅ Row {row_num} deleted: `{removed_row}`")
    else:
        await ctx.send("❌ Failed to delete row. Please try again.")

@bot.command(name="delcol", help="Delete a column from a table")
async def delcol(ctx, tablename: str, *, colname: str):
    guild_id = str(ctx.guild.id)
    table_data = get_table(guild_id, tablename)
    
    if not table_data:
        await ctx.send(f"❌ Table '{tablename}' not found.")
        return
    
    columns = table_data["columns"]
    if colname not in columns:
        await ctx.send(f"❌ Column '{colname}' not found in table '{tablename}'.")
        return
    
    col_index = columns.index(colname)
    columns.pop(col_index)
    rows = table_data["rows"]
    
    # Remove the column from each row
    for row in rows:
        if len(row) > col_index:
            row.pop(col_index)
    
    if save_table(guild_id, tablename, columns, rows):
        await ctx.send(f"✅ Column '{colname}' deleted from table '{tablename}'.")
    else:
        await ctx.send("❌ Failed to delete column. Please try again.")

@bot.command(name="editcell", help="Edit a specific cell in a table")
async def editcell(ctx, tablename: str, row_num: int, colname: str, *, new_value: str):
    guild_id = str(ctx.guild.id)
    table_data = get_table(guild_id, tablename)
    
    if not table_data:
        await ctx.send(f"❌ Table '{tablename}' not found.")
        return
    
    if colname not in table_data["columns"]:
        await ctx.send(f"❌ Column '{colname}' not found.")
        return
    
    if row_num < 1 or row_num > len(table_data["rows"]):
        await ctx.send(f"❌ Invalid row number. Table has {len(table_data['rows'])} rows.")
        return
    
    col_index = table_data["columns"].index(colname)
    table_data["rows"][row_num - 1][col_index] = new_value
    
    if save_table(guild_id, tablename, table_data["columns"], table_data["rows"]):
        await ctx.send(f"✅ Updated {colname} in row {row_num} to: `{new_value}`")
    else:
        await ctx.send("❌ Failed to update cell. Please try again.")

@bot.command(name="editrow", help="Edit an entire row in a table")
async def editrow(ctx, tablename: str, row_num: int, *, row_data: str):
    guild_id = str(ctx.guild.id)
    table_data = get_table(guild_id, tablename)
    
    if not table_data:
        await ctx.send(f"❌ Table '{tablename}' not found.")
        return
    
    if row_num < 1 or row_num > len(table_data["rows"]):
        await ctx.send(f"❌ Invalid row number. Table has {len(table_data['rows'])} rows.")
        return
    
    try:
        values = parse_row_input(row_data)
        if len(values) != len(table_data["columns"]):
            await ctx.send(
                f"❌ Expected {len(table_data['columns'])} values, got {len(values)}.\n"
                f"Columns: {', '.join(table_data['columns'])}"
            )
            return
        
        table_data["rows"][row_num - 1] = values
        if save_table(guild_id, tablename, table_data["columns"], table_data["rows"]):
            await ctx.send(f"✅ Row {row_num} updated successfully.")
        else:
            await ctx.send("❌ Failed to update row. Please try again.")
    except ValueError as e:
        await ctx.send(f"❌ {str(e)}\nExample: `!editrow table 1 \"new value\" 42`")

@bot.command(name="editcol", help="Rename a column in a table")
async def editcol(ctx, tablename: str, old_col: str, new_col: str):
    guild_id = str(ctx.guild.id)
    table_data = get_table(guild_id, tablename)
    
    if not table_data:
        await ctx.send(f"❌ Table '{tablename}' not found.")
        return
    
    if old_col not in table_data["columns"]:
        await ctx.send(f"❌ Column '{old_col}' not found in table '{tablename}'.")
        return
    
    if new_col in table_data["columns"]:
        await ctx.send(f"❌ Column '{new_col}' already exists in table '{tablename}'.")
        return
    
    col_index = table_data["columns"].index(old_col)
    table_data["columns"][col_index] = new_col
    
    if save_table(guild_id, tablename, table_data["columns"], table_data["rows"]):
        await ctx.send(f"✅ Column renamed from '{old_col}' to '{new_col}'.")
    else:
        await ctx.send("❌ Failed to rename column. Please try again.")

@bot.command(name="cleartable", help="Clear all rows from a table")
async def cleartable(ctx, tablename: str):
    guild_id = str(ctx.guild.id)
    
    if not table_exists(guild_id, tablename):
        await ctx.send(f"❌ Table '{tablename}' not found.")
        return
    
    if clear_table_rows(guild_id, tablename):
        await ctx.send(f"✅ All rows in table '{tablename}' have been cleared.")
    else:
        await ctx.send("❌ Failed to clear table. Please try again.")

@bot.command(name="deletetable", help="Permanently delete a table")
async def deletetable(ctx, tablename: str):
    guild_id = str(ctx.guild.id)
    
    if not table_exists(guild_id, tablename):
        await ctx.send(f"❌ Table '{tablename}' not found.")
        return
    
    # Confirmation
    confirm_msg = await ctx.send(
        f"⚠️ Are you sure you want to permanently delete the table '{tablename}'?\n"
        "React with ✅ to confirm or ❌ to cancel."
    )
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")

    def check(reaction, user):
        return (user == ctx.author and str(reaction.emoji) in ["✅", "❌"]
                and reaction.message.id == confirm_msg.id)

    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=30.0, check=check)
        if str(reaction.emoji) == "✅":
            if delete_table(guild_id, tablename):
                await ctx.send(f"✅ Table '{tablename}' has been deleted.")
            else:
                await ctx.send("❌ Failed to delete table. Please try again.")
        else:
            await ctx.send("❌ Deletion cancelled.")
    except Exception as e:
        logger.error(f"Error in deletetable confirmation: {e}")
        await ctx.send("⌛ Confirmation timed out. Table not deleted.")

@bot.command(name="viewtables", help="List all tables in this server")
async def viewtables(ctx):
    guild_id = str(ctx.guild.id)
    tables = get_guild_tables(guild_id)
    
    if not tables:
        await ctx.send("ℹ️ This server has no tables yet.")
        return
    
    table_list = "\n".join([f"• {name}" for name in tables.keys()])
    await ctx.send(f"📋 **Tables in this server:**\n{table_list}")

@bot.command(name="commands", help="Show all available commands")
async def show_commands(ctx):
    embed = discord.Embed(
        title="📋 Table Bot Commands",
        description="All commands for managing your tables",
        color=discord.Color.blue()
    )
    
    commands_list = [
        ("!newtable <name>", "Create a new empty table"),
        ("!addcol <table> <name>", "Add a column to a table"),
        ("!addrow <table> <values...>", "Add a row (use quotes for values with spaces)"),
        ("!showtable <table>", "Display a table"),
        ("!editcell <table> <row> <col> <value>", "Edit a specific cell"),
        ("!editrow <table> <row> <values...>", "Replace an entire row"),
        ("!editcol <table> <old> <new>", "Rename a column"),
        ("!delrow <table> <row>", "Delete a row"),
        ("!delcol <table> <col>", "Delete a column"),
        ("!cleartable <table>", "Clear all rows (keep columns)"),
        ("!deletetable <table>", "Permanently delete a table"),
        ("!viewtables", "List all tables in this server"),
    ]
    
    for cmd, desc in commands_list:
        embed.add_field(name=cmd, value=desc, inline=False)
    
    embed.set_footer(text="🤖 Table Management Bot")
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Command not found. Use !commands to see available commands.")
    else:
        logger.error(f"Command error: {error}")
        await ctx.send("❌ An error occurred while executing that command.")

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!commands"))
    logger.info(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    logger.info("------")

if __name__ == "__main__":
    bot.run(TOKEN)
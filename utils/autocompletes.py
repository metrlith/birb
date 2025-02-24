import discord
from discord import app_commands

Current = {}

async def DepartmentAutocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice]:
    from Cogs.Modules.promotions import config

    C = await interaction.client.config.find_one({"_id": interaction.guild.id})
    if not C:
        return [
            app_commands.Choice(
                name="[Bot hasn't been configured yet]",
                value="not_configured"
            )
        ]
    
    PromoSystemType = C.get('Promo', {}).get('System', {}).get('type', "")
    if PromoSystemType == "multi":
        Departments = C.get('Promo', {}).get('System', {}).get('multi', {}).get('Departments', [])
        choices = []
        for dept_list in Departments:
            for department in dept_list:
                if current.lower() in department.get('name').lower():
                    choices.append(app_commands.Choice(
                        name=department.get('name'),
                        value=department.get('name')
                    ))
        return choices
    
    return []

async def CloseReason(
        interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    PreviousTicketReasons = interaction.client.db['Tickets'].find({'GuildID': interaction.guild.id, 'Closed': {'$exists': True}})
    Reasons = []
    async for Ticket in PreviousTicketReasons:
        if Ticket.get('closed', {}).get('reason') and current.lower() in Ticket.get('closed', {}).get('reason').lower():
            Reasons.append(app_commands.Choice(
                name=Ticket.get('closed', {}).get('reason')[:100],
                value=Ticket.get('closed', {}).get('reason')[:100]
            ))
    return Reasons



async def RoleAutocomplete(
    interaction: discord.Interaction, current: str
) -> list[app_commands.Choice[str]]:
    C = await interaction.client.config.find_one({"_id": interaction.guild.id})
    if not C:
        return [
            app_commands.Choice(
                name="[Bot hasn't been configured yet]",
                value="not_configured"
            )
        ]

    PromoSystemType = C.get('Promo', {}).get('System', {}).get('type', "")
    
    if PromoSystemType == "multi":

        SelectedDept = interaction.namespace.department
        
        if not SelectedDept:
            return [
                app_commands.Choice(
                    name="[No Role selected]",
                    value="no_role"
                )
            ]
        Departments = C.get('Promo', {}).get('System', {}).get('multi', {}).get('Departments', [])
        SelectedDeptData = next(
            (dept for dept_list in Departments for dept in dept_list if dept.get('name') == SelectedDept), None
        )
        
        if not SelectedDeptData:
            return [
                app_commands.Choice(
                    name="[Department not found]",
                    value="department_not_found"
                )
            ]
        
        RoleIDs = [str(role_id) for role_id in SelectedDeptData.get('ranks', [])]
        roles = [
            app_commands.Choice(
                name=interaction.guild.get_role(int(role_id)).name,
                value=str(interaction.guild.get_role(int(role_id)).id)
            )
            for role_id in RoleIDs
            if interaction.guild.get_role(int(role_id)) and current.lower() in interaction.guild.get_role(int(role_id)).name.lower()
        ]
        return roles[:25]
    
    if PromoSystemType == "single":
        RoleIDs = [str(role_id) for role_id in C.get('Promo', {}).get('System', {}).get('single', {}).get('Hierarchy', [])]
        roles = [
            app_commands.Choice(
                name=interaction.guild.get_role(int(role_id)).name,
                value=f"{interaction.guild.get_role(int(role_id)).id}"
            )
            for role_id in RoleIDs
            if interaction.guild.get_role(int(role_id)) and current.lower() in interaction.guild.get_role(int(role_id)).name.lower()
        ]
        return roles[:25]
    
    return []

from bot import CMD_SUFFIX

class _BotCommands:
    def __init__(self):
        self.StartCommand = 'start'
        self.GetIDCommand = f'id'
        self.GetStickerIDCommand = f'stickerid{CMD_SUFFIX}'
        self.UserSetCommands = [f"usersettings{CMD_SUFFIX}", f"us{CMD_SUFFIX}"]
        self.GetMediaInfoCommand = [f"media_info{CMD_SUFFIX}", f"minfo{CMD_SUFFIX}"]
        self.GetFileInfoCommand = f"minfo_json{CMD_SUFFIX}"
        self.GetChatsListCommand = f"chats_list{CMD_SUFFIX}"
        self.CheckRightsCommand = f"checkrights{CMD_SUFFIX}"
        self.StatsCommand = f'stats{CMD_SUFFIX}'
        self.IndexCommand = f'index{CMD_SUFFIX}'
        self.BotStatsCommand = f'bstats{CMD_SUFFIX}'
        self.PingCommand = f'ping{CMD_SUFFIX}'
        self.HelpCommand = f'help{CMD_SUFFIX}'
        self.DeleteDbfileCommand = [f'deletefile{CMD_SUFFIX}', f'df{CMD_SUFFIX}']
        self.DeleteDbfilesCommand = [f'deletefiles{CMD_SUFFIX}', f'dfs{CMD_SUFFIX}']
        self.DeletePMUserCommand = f"delpmuser{CMD_SUFFIX}"
        self.DeleteFsubUserCommand = f"delfsubuser{CMD_SUFFIX}"
        self.SetSkipFilesCommand = f'setskip{CMD_SUFFIX}'
        self.AuthorizeCommand = f"authorize{CMD_SUFFIX}"
        self.UnAuthorizeCommand = f"unauthorize{CMD_SUFFIX}"
        self.AddSudoCommand = f"addsudo{CMD_SUFFIX}"
        self.RmSudoCommand = f"rmsudo{CMD_SUFFIX}"
        self.BotSetCommand = [f'botsettings{CMD_SUFFIX}', f'bs{CMD_SUFFIX}']
        self.BroadcastCommand = [f"broadcast{CMD_SUFFIX}"]
        self.LogCommand = f'log{CMD_SUFFIX}'
        self.RestartCommand = [f'restart{CMD_SUFFIX}', f'r{CMD_SUFFIX}']

BotCommands = _BotCommands()

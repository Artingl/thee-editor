import shlex
import os


class Command:
    def __init__(self, executor):
        self.executor = executor
        self.application = executor.editor.application
        self.editor = executor.editor
        self.status_bar = executor.editor.status_bar
    
    def execute(self, cmd, args): ...


class OpenCommand(Command):
    def execute(self, cmd, args):
        if len(args) == 0:
            self.status_bar.display_text("Provide file name 'open FILENAME'", background=(255, 0, 0))
            return

        if not os.path.isfile(args[0]):
            self.status_bar.display_text(f"File '{args[0]}' doesn't exist", background=(255, 0, 0))
            return
        if self.editor.is_unsaved and (len(args) == 1 or args[1] != "!"):
            self.status_bar.display_text(f"Current file is unsaved. Save it or type 'open FILENAME !'", background=(255, 0, 0))
            return

        self.editor.open_file(args[0])


class SaveCommand(Command):
    def execute(self, cmd, args):
        if args:
            self.editor.filename = args[0]
        self.editor.save_file()
        self.status_bar.display_text(f"Saved file as '{self.editor.filename}'")


class ExitQuitRestartCommand(Command):
    def execute(self, cmd, args):
        if self.editor.is_unsaved and (len(args) == 0 or args[0] != "!"):
            self.status_bar.display_text(f"Current file is unsaved. Save it or type '{cmd} !'", background=(255, 0, 0))
            return
        if cmd == 'exit' or cmd == 'quit':
            self.application.close()
        else:
            self.application.restart()


class NewCommand(Command):
    def execute(self, cmd, args):
        filename = "unnamed.txt"
        if args:
            filename = args[0]
        self.editor.open_file(filename)


class ShellCommand(Command):
    def execute(self, cmd, args):
        # TODO: implement a better way to execute shell commands
        output = os.popen(' '.join(args)).read()
        output = output.strip()
        for i in output.split("\n"):
            print(i)


class ReloadCommand(Command):
    def execute(self, cmd, args):
        self.application.reload()
        self.status_bar.display_text("Successfully reloaded")


class EvalCommand(Command):
    def execute(self, cmd, args):
        if args:
            eval(' '.join(args))


class ConfigCommand(Command):
    DATA_TYPES = {
        'int': int,
        'bool': lambda x: x.lower() == 'true',
        'float': float,
        'str': str,
    }

    def execute(self, cmd, args):
        example = "config key.param = value type[int/bool/float/str]"
        if len(args) < 4 or args[3] not in ConfigCommand.DATA_TYPES or args[1] != '=':
            self.status_bar.display_text(f"Command accepts exactly 4 arguments: '{example}'", background=(255, 0, 0))
            return
        config_key_param = args[0].split(".")
        if len(config_key_param) != 2:
            self.status_bar.display_text(f"Key/param value must be separated with a dot: '{example}'", background=(255, 0, 0))
            return

        previous_value = self.application.get_config_value(config_key_param[0], config_key_param[1])
        new_value = ConfigCommand.DATA_TYPES[args[3]](args[2])

        self.application.store_config_value(config_key_param[0], config_key_param[1], new_value)
        self.status_bar.display_text(f"Updated value for {args[0]}; previous: '{previous_value}', new: '{new_value}'")


class CommandExecutor:
    def __init__(self, editor):
        self.editor = editor
        self.status_bar = self.editor.status_bar
        self.last_successful_search_pattern = None

        self.commands = {
            ('open'): OpenCommand(self),
            ('save'): SaveCommand(self),
            ('exit', 'quit', 'restart'): ExitQuitRestartCommand(self),
            ('reload'): ReloadCommand(self),
            ('new'): NewCommand(self),
            ('shell'): ShellCommand(self),
            ('config'): ConfigCommand(self),
            ('eval'): EvalCommand(self),
        }
    
    def repeat_last_search(self):
        if not self.last_successful_search_pattern:
            return
        command = self.last_successful_search_pattern
        if not self.editor.find_first_pattern(command):
            self.last_successful_search_pattern = None
            self.status_bar.display_text(f"Unable to find '{command}'", background=(255, 0, 0))
        else:
            self.last_successful_search_pattern = command

    def execute(self, text):
        command, *args = shlex.split(text, posix=False)

        # If the command is just a number, go to that line number
        if command.isdigit():
            command = int(command)
            if command <= 0 or command > len(self.editor.base_lines):
                self.status_bar.display_text(f"Invalid line! Available range: 1...{len(self.editor.base_lines)}", background=(255, 0, 0))
            else:
                self.editor.set_caret_line(command)
        else:
            for commands_list, instance in self.commands.items():
                if command in commands_list:
                    instance.execute(command, args)
                    return
            # If unable to find the command with such name, try to use the command as a search pattern in the editor text
            if not self.editor.find_first_pattern(text):
                self.last_successful_search_pattern = None
                self.status_bar.display_text(f"Unable to find '{text}'", background=(255, 0, 0))
            else:
                self.last_successful_search_pattern = text
        
            # self.status_bar.display_text(f"Invalid command!", background=(255, 0, 0))


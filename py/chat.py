import vim
import re

# import utils

plugin_root = vim.eval("s:plugin_root")
vim.command(f"py3file {plugin_root}/py/utils.py")

prompt, config = load_config_and_prompt()
config_options = config['options']
config_ui = config['ui']

role_prefix = config_options.get('role_prefix', None)
role_prefix = f"{role_prefix} " or ""

def initialize_chat_window():
    lines = vim.eval('getline(1, "$")')
    user_prompt = f"{role_prefix}>>> user"
    if user_prompt not in lines:
        # user role not found, put whole file content as an user prompt
        vim.command("normal! gg")
        populates_options = config_ui['populate_options'] == '1'
        if populates_options:
            vim.command("normal! O[chat-options]")
            vim.command("normal! o")
            for key, value in config_options.items():
                if key == 'initial_prompt':
                    value = "\\n".join(value)
                vim.command("normal! i" + key + "=" + value + "\n")
        vim.command("normal! " + ("o" if populates_options else "O"))
        vim.command(f"normal! i{role_prefix}>>> user\n")

    vim.command("normal! G")
    vim_break_undo_sequence()
    vim.command("redraw")

    file_content = vim.eval('trim(join(getline(1, "$"), "\n"))')
    role_lines = re.findall(fr'^{re.escape(role_prefix)}>>> user|^{re.escape(role_prefix)}>>> system|^{re.escape(role_prefix)}<<< assistant.*', file_content, flags=re.MULTILINE)
    if not role_lines[-1].startswith(f"{role_prefix}>>> user"):
        # last role is not user, most likely completion was cancelled before
        vim.command("normal! o")
        vim.command(f"normal! i\n{role_prefix}>>> user\n\n")

    if prompt:
        vim.command("normal! i" + prompt)
        vim_break_undo_sequence()
        vim.command("redraw")

initialize_chat_window()

chat_options = parse_chat_header_options()
options = {**config_options, **chat_options}

initial_prompt = '\n'.join(options.get('initial_prompt', []))
initial_messages = parse_chat_messages(initial_prompt, role_prefix)

chat_content = vim.eval('trim(join(getline(1, "$"), "\n"))')
chat_messages = parse_chat_messages(chat_content, role_prefix)
is_selection = vim.eval("l:is_selection")

messages = initial_messages + chat_messages

try:
    if messages[-1]["content"].strip():
        vim.command(f"normal! Go\n{role_prefix}<<< assistant\n\n")
        vim.command("redraw")

        print('Answering...')
        vim.command("redraw")

        text_chunks = make_chat_text_chunks(messages, options)
        render_text_chunks(text_chunks, is_selection)

        vim.command(f"normal! a\n\n{role_prefix}>>> user\n\n")
        vim.command("redraw")
        clear_echo_message()
except BaseException as error:
    handle_completion_error(error)
    printDebug("[chat] error: {}", traceback.format_exc())

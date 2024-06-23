import vim
import re

# import utils

plugin_root = vim.eval("s:plugin_root")
vim.command(f"py3file {plugin_root}/py/utils.py")

prompt, role_options = parse_prompt_and_role(vim.eval("l:prompt"))
config = normalize_config(vim.eval("l:config"))
config_options = {
    **config['options'],
    **role_options['options_default'],
    **role_options['options_chat'],
}
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
openai_options = make_openai_options(options)
http_options = make_http_options(options)

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

        request = {
            'stream': True,
            'messages': messages,
            **openai_options
        }
        printDebug("[chat] request: {}", request)
        url = options['endpoint_url']
        response = openai_request(url, request, http_options)
        def map_chunk(resp):
            printDebug("[chat] response: {}", resp)
            return resp['choices'][0]['delta'].get('content', '')
        text_chunks = map(map_chunk, response)
        render_text_chunks(text_chunks, is_selection)

        vim.command(f"normal! a\n\n{role_prefix}>>> user\n\n")
        vim.command("redraw")
        clear_echo_message()
except BaseException as error:
    handle_completion_error(error)
    printDebug("[chat] error: {}", traceback.format_exc())

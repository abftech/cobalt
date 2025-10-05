import re
import shlex
import sys

from tests.simple_selenium import SimpleSelenium

command_lookup = {
    "enter": 'manager.enter_value_into_field("WORDS_3", "WORDS_1")',
    "enter_parameter": 'manager.enter_value_into_field("WORDS_3", WORDS_1)',
    "find": 'manager.find_by_text("WORDS_1")',
    "find_by_id": 'manager.find_by_id("WORDS_1")',
    "title": 'manager.set_title("WORDS_1")',
    "go": 'manager.go_to("WORDS_1")',
    "screenshot": 'manager.screenshot("WORDS_1")',
    "send_enter": 'manager.send_enter("WORDS_2")',
    "log": 'manager.add_message("WORDS_1", bold=True)',
    "login": 'manager.login("WORDS_1")',
    "selectpicker": 'manager.selectpicker("WORDS_2", "WORDS_4")',
    "dropdown": 'manager.dropdown("WORDS_2", "WORDS_4")',
    "sleep": "manager.sleep(WORDS_1)",
    "click": 'manager.super_click("WORDS_1")',
    "check_email_to": 'manager.check_email_to("WORDS_1")',
    "check_email_to_with_subject": 'manager.check_email_to_with_subject("WORDS_1", "WORDS_2")',
    "check_email_to_with_body": 'manager.check_email_to_with_body("WORDS_1", "WORDS_2")',
}


def simple_selenium_parser(
    script_file, base_url, password, browser, show, silent, userid="userid-not-set"
):
    """translates a test script into code and runs it"""

    with open(f"tests/scripts/{script_file}") as in_file:
        script = in_file.readlines()

    commands = build_commands(script)
    run_commands(
        commands, base_url, password, browser, show, silent, userid, script_file
    )


def build_commands(script):
    """does the string manipulation"""
    commands = []
    for line_number, line in enumerate(script):
        line = line.strip()

        # Handle comments
        if line[0] == "#":
            continue
        if comment := re.search("#", line):
            line = line[: comment.start()]

        # Use shlex to split 'hello "I am a string" goodbye' into ['hello', 'I am a string', 'goodbye']
        words = shlex.split(line)

        commands.append(f"manager.current_action='{line}'")

        if cmd_string := build_command_line(words, line_number):
            commands.append(cmd_string)
        else:
            print(f"Error parsing Line {line_number + 1}: {line}")
            sys.exit(1)

    return commands


def build_command_line(words, line_number):
    """process a single command line"""

    # the first word is the keyword
    key_word = words[0].lower()

    # Find a match or None from command_lookup
    cmd_string = command_lookup.get(key_word)

    # validate command
    if not cmd_string:
        print(f"Unknown command {key_word} on line {line_number + 1}")
        sys.exit(1)

    # Check number of expected words
    pattern = r"{}(\d+)".format(re.escape("WORDS_"))
    if matches := re.findall(pattern, cmd_string):
        # matches is a list of strings e.g. ['1', '3']
        required = int(max(matches))
        if len(words) != required + 1:
            print(
                f"Incorrect number of words on line {line_number + 1}. Expected {required} parameters for command '{key_word}'"
            )
            sys.exit(1)

    # Go through and replace the placeholders with the words from the command
    for index, word in enumerate(words[1:]):
        cmd_string = cmd_string.replace(f"WORDS_{index + 1}", word)

    return cmd_string


def run_commands(
    commands, base_url, password, browser, show, silent, userid, script_file
):
    """execute the commands"""

    manager = SimpleSelenium(
        base_url=base_url,
        browser=browser,
        show=show,
        silent=silent,
        password=password,
        script_file=script_file,
    )

    for cmd_string in commands:
        exec(cmd_string)

    manager.handle_finish()

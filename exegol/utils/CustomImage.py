import curses
import os
import re

class CustomImage:
    """Create custom images"""
    def __init__(self):
        self.directory = "./exegol-docker-build/sources"
        self.regex = r"function install_([^\s(){}]+)"
        self.sh_files = [filename for filename in os.listdir(self.directory) if filename.endswith(".sh")]
        self.sh_files.sort()
        self.current_file_index = 0
        self.items = []
        self.selected_items = []
        self.parse_current_file()

    def parse_current_file(self):
        self.items = []
        if self.current_file_index >= len(self.sh_files):
            return
        filename = self.sh_files[self.current_file_index]
        print("Let's parse : " + filename)
        with open(os.path.join(self.directory, filename), "r") as file:
            content = file.read()
            self.items.extend(re.findall(self.regex, content))
            self.items.sort()
            self.items = list(set(self.items))

    def generate_dockerfile(self):
        print("Generating the Dockerfile...")
        with open("./template.dockerfile", 'r') as template_file:
            content = template_file.read()

        # Generate the new dockerfile
        new_lines = ''
        for item in self.selected_items:
            new_lines += f"RUN /root/sources/ad.sh install_{item}\n"

        content = content.replace("# Template start", "# Template start\n" + new_lines)

        with open('test.dockerfile', 'w') as new_file:
            new_file.write(content)

        # Run build

        # DEBUG
        #input("Wait")
        #os.system("rm -rf ./test.dockerfile")
        #os.system("docker build -t test-generation -f test.dockerfile . --no-cache")

        #os.system("rm -rf ./test.dockerfile")
    def get_selection(self, stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)

        # TODO : Display banner

        # TODO : Search Bar

        # Search bar initialization
        search_str = ''
        search_mode = False
        curses.echo()


        current_row = 0
        current_column = 0
        max_row = curses.LINES - 1  # We subtract 1 to allow for the status bar
        self.items.sort()

        # Compute the number of columns
        max_column = len(self.items) // max_row + 1

        while True:
            stdscr.clear()
            for i, item in enumerate(self.items):
                if i in self.selected_items:
                    stdscr.addstr(i % max_row, (i // max_row) * (curses.COLS // max_column),
                                  "[X] " + item + "", curses.color_pair(1))
                else:
                    try:
                        stdscr.addstr(i % max_row, (i // max_row) * (curses.COLS // max_column),
                                      "[ ] " + item + "", curses.color_pair(2))
                    except curses.error:
                        pass

            # Highlight the current item
            try:
                current_index = current_column * max_row + current_row
                next_column = ((current_column + 1) * curses.COLS // max_column)
                current_width = next_column - (current_column * curses.COLS // max_column)
                stdscr.chgat(current_row % max_row, (current_column * curses.COLS // max_column),
                             current_width - 1, curses.A_REVERSE)
            except curses.error:
                pass

            # Display search bar
            if search_mode:
                stdscr.move(curses.LINES - 1, 0)
                stdscr.clrtoeol()
                stdscr.addstr(curses.LINES - 1, 0, "Search: " + search_str)

            stdscr.refresh()
            key = stdscr.getch()

            # Handle search bar input
            if search_mode:
                if key == 27:  # ESC key
                    search_mode = False
                    search_str = ''
                    curses.noecho()
                    curses.curs_set(0)
                    stdscr.refresh()
                elif key == curses.KEY_BACKSPACE or key == 127:  # Backspace key
                    search_str = search_str[:-1]
                elif key == ord('\n'):  # Enter key
                    search_mode = False
                    curses.noecho()
                    curses.curs_set(0)
                    stdscr.refresh()
                    # Find the index of the first item that matches the search string
                    match_index = -1
                    for i, item in enumerate(self.items):
                        if search_str.lower() in item.lower():
                            match_index = i
                            break
                    if match_index != -1:
                        current_column = match_index // max_row
                        current_row = match_index % max_row
                else:
                    search_str += chr(key)
            else:
                if key == curses.KEY_UP and current_row > 0:
                    current_row -= 1
                elif key == curses.KEY_DOWN and current_row < max_row - 1 and current_index < len(self.items) - 1:
                    current_row += 1
                elif key == ord(" "):
                    if current_index in self.selected_items:
                        self.selected_items.remove(current_index)
                    else:
                        self.selected_items.append(current_index)
                elif key == curses.KEY_LEFT and current_column > 0:
                    current_column -= 1
                    current_row = min(current_row, len(self.items) - 1 - current_column * max_row)
                elif key == curses.KEY_RIGHT and current_column < max_column - 1:
                    current_column += 1
                    current_row = min(current_row, len(self.items) - 1 - current_column * max_row)
                elif key == curses.KEY_ENTER or key in [10, 13]:
                    self.current_file_index += 1
                    stdscr.clear()
                    stdscr.refresh()
                    self.selected_items = [self.items[i] for i in self.selected_items]
                    self.parse_current_file()
                    return
                # Toggle search mode
                elif key == ord('/'):
                    search_mode = True
                    search_str = ""
                    curses.echo()
                    curses.curs_set(1)


        # self.selected_items = [self.items[i] for i in self.selected_items]
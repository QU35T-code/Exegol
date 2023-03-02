import curses
import os
import re

class CustomImage:
    """Create custom images"""
    def __init__(self):
        directory = "./exegol-docker-build/sources"
        regex = r"function install_([^\s(){}]+)"
        self.items = []

        for filename in os.listdir(directory):
            if filename.endswith(".sh"):
                print("Let's parse : " + filename)
                # Ouvrir le fichier
                with open(os.path.join(directory, filename), "r") as file:
                    # Lire le contenu du fichier
                    content = file.read()
                    # Trouver toutes les fonctions qui commencent par "install_"
                    self.items.extend(re.findall(regex, content))

        self.items = list(set(self.items))

    def get_selection(self, stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)

        selected_items = []
        current_row = 0
        current_column = 0
        max_row = curses.LINES - 1  # We subtract 1 to allow for the status bar

        # Compute the number of columns
        max_column = len(self.items) // max_row + 1

        while True:
            stdscr.clear()
            for i, item in enumerate(self.items):
                if i in selected_items:
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

            stdscr.refresh()
            key = stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < max_row - 1 and current_index < len(self.items) - 1:
                current_row += 1
            elif key == ord(" "):
                if current_index in selected_items:
                    selected_items.remove(current_index)
                else:
                    selected_items.append(current_index)
            elif key == curses.KEY_LEFT and current_column > 0:
                current_column -= 1
                current_row = min(current_row, len(self.items) - 1 - current_column * max_row)
            elif key == curses.KEY_RIGHT and current_column < max_column - 1:
                current_column += 1
                current_row = min(current_row, len(self.items) - 1 - current_column * max_row)
            elif key == curses.KEY_ENTER or key in [10, 13]:
                break

        selected_items = [self.items[i] for i in selected_items]
        return selected_items
import curses
import os
import re

class CustomImages:
    """Create custom images"""
    def __init__(self):
        directory = "./exegol-docker-build/sources"
        regex = r"install_([^\s(){}]+)"
        items = []

        for filename in os.listdir(directory):
            if filename.endswith(".sh"):
                print("Let's parse : " + filename)
                # Ouvrir le fichier
                with open(os.path.join(directory, filename), "r") as file:
                    # Lire le contenu du fichier
                    content = file.read()
                    # Trouver toutes les fonctions qui commencent par "install_"
                    self.items = re.findall(regex, content)

        list(set(self.items))
    def get_selection(self, stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK)

        selected_items = []
        current_row = 0

        while True:
            stdscr.clear()
            for i, item in enumerate(self.items):
                if i in selected_items:
                    stdscr.addstr(i, 0, "[X] " + item + " ", curses.color_pair(1))
                else:
                    try:
                        stdscr.addstr(i, 0, "[ ] " + item + " ", curses.color_pair(2))
                    except curses.error:
                        pass
                    try:
                        stdscr.chgat(current_row, 0, -1, curses.A_REVERSE)
                    except curses.error:
                        pass

            stdscr.refresh()
            key = stdscr.getch()

            if key == curses.KEY_UP and current_row > 0:
                current_row -= 1
            elif key == curses.KEY_DOWN and current_row < len(self.items) - 1:
                current_row += 1
            elif key == ord(" "):
                if current_row in selected_items:
                    selected_items.remove(current_row)
                else:
                    selected_items.append(current_row)
            elif key == curses.KEY_ENTER or key in [10, 13]:
                break

        selected_items = [self.items[i] for i in selected_items]
        return selected_items

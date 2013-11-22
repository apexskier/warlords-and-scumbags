import socket, select, sys, re, cardgame, math
import curses, locale


locale.setlocale(locale.LC_ALL, '');
code = locale.getpreferredencoding()
BUFSIZ = 1024

def startGame(stdscr):
    client = Client(options['-n'], stdscr, options['-s'], options['-p'], options['-m'])
    if not client.socket_error:
        client.playGame()

class Client(object):
    def __init__(self, name, stdscr, host = 'localhost', port = 36714, manual = False):
        self.scr = stdscr
        self.name = name
        self.people = []
        self.cmd_buff = ""
        # Quit flag
        self.flag = False
        self.port = int(port)
        self.host = host
        self.manual = manual
        self.buff = ""
        self.recieving_msg = False
        # Initial prompt
        self.prompt = ">>> "
        # Connect to server at port
        if self.scr:
            self.setupWindows()
        try:
            self.socket_error = False
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, self.port))
            self.prnt('Connected to server {0:s}:{1:d}'.format(self.host, self.port))
            # Send my name...
            self.send('[cjoin|' + self.name.ljust(8) + "]")
        except socket.error, e:
            self.socket_error = True
            if self.scr:
                self.hand.addstr("Couldn't connect to the server {0:s}:{1:d}".format(self.host, self.port));
            else:
                self.prnt('Could not connect to server {1}:{2:d} with name "{0}"'.format(self.name, self.host, self.port))
                sys.exit(1)
        except KeyboardInterrupt:
            self.prnt("Interrupted.")
            self.socket.close()

    def prnt(self, text):
        if not self.scr:
            print text

    def addCenterText(self, scr, y, string):
        x = math.floor(self.width / 2) - math.floor(len(string) / 2)
        scr.addstr(int(y), int(x), string)

    def drawLobby(self):
        if self.scr:
            self.lobby.clear()
            self.lobby.addstr(0, 0, 'Your name is ' + self.name + '.')
            self.lobby.addstr(1, 0, 'People in lobby:')
            self.lobby.addstr(3, 0, ', '.join(self.people))
            self.lobby.refresh()

    def setupWindows(self):
        if self.scr:
            curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(4, curses.COLOR_BLUE, curses.COLOR_BLACK)
            curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)
            curses.resizeterm(48, 120)
            self.scr.clear()
            size = self.scr.getmaxyx()
            self.width = size[1]
            self.height = size[0]
            self.addCenterText(self.scr, 0, "                                              __                             ")
            self.addCenterText(self.scr, 1, " \    / _. ._ |  _  ._ _|  _    _. ._   _|   (_   _     ._ _  |_   _.  _   _ ")
            self.addCenterText(self.scr, 2, "  \/\/ (_| |  | (_) | (_| _>   (_| | | (_|   __) (_ |_| | | | |_) (_| (_| _> ")
            self.addCenterText(self.scr, 3, "                                                                       _|    ")

            self.scr.refresh()

            self.lobby_border = curses.newwin(10, int(self.width / 3 - 2), 4, int((self.width / 3) * 2 + 1))
            self.lobby_border.border()
            self.lobby_border.refresh()
            self.lobby = curses.newwin(8, int(self.width / 3 - 6), 5, int((self.width / 3) * 2 + 3))
            self.drawLobby()

            self.chat_border = curses.newwin(self.height - 15, int(self.width / 3 - 2), 14, int((self.width / 3) * 2 + 1))
            self.chat_border.border()
            self.chat_border.refresh()
            self.chat = curses.newwin(self.height - 17, int(self.width / 3 - 6), 15, int((self.width / 3) * 2 + 3))

            table_border_width = int(self.width / 3 * 2 - 1)
            table_border_height = self.height - 8
            self.table_border = curses.newwin(table_border_height, table_border_width, 4, 1)
            self.table_border.border()
            self.table_border.refresh()
            # self.table = curses.newwin()
            self.players_wins = []
            player1 = curses.newwin((table_border_height - 8) / 4, table_border_width // 2 - 2, 5, 3)
            player1.border()
            player1.refresh()
            self.players_wins.append(player1)
            player2 = curses.newwin((table_border_height - 8) / 4, table_border_width // 2 - 2, 5, table_border_width // 2 + 2)
            player2.border()
            player2.refresh()
            self.players_wins.append(player2)
            player3 = curses.newwin((table_border_height - 8) / 4, table_border_width // 2 - 2, (table_border_height - 8) / 4 + 5, 3)
            player3.border()
            player3.refresh()
            self.players_wins.append(player3)
            player4 = curses.newwin((table_border_height - 8) / 4, table_border_width // 2 - 2, (table_border_height - 8) / 4 + 5, table_border_width // 2 + 2)
            player4.border()
            player4.refresh()
            self.players_wins.append(player4)
            player5 = curses.newwin((table_border_height - 8) / 4, table_border_width // 2 - 2, (table_border_height - 8) / 2 + 5, 3)
            player5.border()
            player5.refresh()
            self.players_wins.append(player5)
            player6 = curses.newwin((table_border_height - 8) / 4, table_border_width // 2 - 2, (table_border_height - 8) / 2 + 5, table_border_width // 2 + 2)
            player6.border()
            player6.refresh()
            self.players_wins.append(player6)
            player7 = curses.newwin((table_border_height - 8) / 4, table_border_width // 2 - 2, ((table_border_height - 8) / 4) * 3 + 5, 3)
            player7.border()
            player7.refresh()
            self.players_wins.append(player7)
            self.hand_window = curses.newwin(4, table_border_width - 4, table_border_height - 1, 3)
            self.hand_window.border()
            self.hand_window.refresh()

            self.prompt = curses.newwin(2, int(self.width / 3 * 2 - 1), self.height - 4, 1)
            self.prompt.addstr(0, 1, "cmd: ")
            self.prompt.refresh()

    def playGame(self):
        while not self.flag:
            try:
                # wait for input form stdin and socket
                ready_in, ready_out, ready_exept = select.select([0, self.socket], [], [])

                for i in ready_in:
                    if i == 0:
                        if self.scr:
                            data = self.scr.getch()
                            if data:
                                raise Exception(data)
                                if data == 10: # enter key
                                    self.prompt.clear()
                                    message = self.cmd_buff
                                    self.cmd_buff = ""
                                    if message:
                                        message_match = re.match('/(?P<type>[a-zA-Z]{4}) (?P<body>.+)', message)
                                        if message_match:
                                            m_type = message_match.group('type')
                                            if m_type == "chat":
                                                self.cchat(message_match.group('body'))
                                            elif m_type == "swap":
                                                self.send(message_match.group('body'))
                                            elif m_type == "play":
                                                self.cplay([int(card) for card in message_match.group('body').split(',') if card != 52])
                                            elif m_type == "quit":
                                                sys.exit(1)
                                            elif m_type == "hand":
                                                self.shand(message_match.group('body'))
                                            else:
                                                self.prompt.addstr(1, 1, "Invalid command")
                                        else:
                                            self.prompt.addstr(1, 1, "No command")
                                    self.prompt.addstr(0, 1, "cmd: ")
                                    self.prompt.move(0, 6)
                                    self.prompt.refresh()
                                if data == 9: # tab
                                    self.autocompleting = True
                                    to_match = self.cmd_buff.split()[-1]
                                    if "/chat".find(to_match) == 0:
                                        self.cmd_buff = self.cmd_buff[0:-len(to_match)] + "/chat "
                                        self.prompt.clear()
                                        self.prompt.addstr(0, 1, "cmd: " + self.cmd_buff)
                                        self.prompt.refresh()
                                    elif "/swap".find(to_match) == 0:
                                        self.cmd_buff = self.cmd_buff[0:-len(to_match)] + "/swap "
                                        self.prompt.clear()
                                        self.prompt.addstr(0, 1, "cmd: " + self.cmd_buff)
                                        self.prompt.refresh()
                                    elif "/play".find(to_match) == 0:
                                        self.cmd_buff = self.cmd_buff[0:-len(to_match)] + "/play "
                                        self.prompt.clear()
                                        self.prompt.addstr(0, 1, "cmd: " + self.cmd_buff)
                                        self.prompt.refresh()
                                    elif "/quit".find(to_match) == 0:
                                        self.cmd_buff = self.cmd_buff[0:-len(to_match)] + "/quit "
                                        self.prompt.clear()
                                        self.prompt.addstr(0, 1, "cmd: " + self.cmd_buff)
                                        self.prompt.refresh()
                                    elif "/hand".find(to_match) == 0:
                                        self.cmd_buff = self.cmd_buff[0:-len(to_match)] + "/hand "
                                        self.prompt.clear()
                                        self.prompt.addstr(0, 1, "cmd: " + self.cmd_buff)
                                        self.prompt.refresh()

                                elif data == 263: # backspace
                                    self.cmd_buff = self.cmd_buff[0:-1]
                                    self.prompt.clear()
                                    self.prompt.addstr(0, 1, "cmd: " + self.cmd_buff)
                                    self.prompt.refresh()
                                else:
                                    key = str(unichr(data))
                                    if key != '\n' and key != '\r':
                                        self.cmd_buff += key
                                        self.prompt.addstr(key)
                                        self.prompt.refresh()
                        else:
                            data = sys.stdin.readline().strip()
                            if data:
                                message_match = re.match('c(?P<type>[a-zA-Z]{4})\|(?P<body>.+)', data)
                                if message_match:
                                    m_type = message_match.group('type')
                                    if m_type == "play":
                                        self.cplay([int(card) for card in message_match.group('body').split(',') if card != 52])
                                    elif m_type == "chat":
                                        self.cchat(message_match.group('body'))
                                    elif m_type == "hand":
                                        self.shand(message_match.group('body'))
                                    else:
                                        self.send("[" + data + "]")
                                else:
                                    self.send("[" + data + "]")
                    elif i == self.socket:
                        data = self.socket.recv(BUFSIZ)
                        if self.scr:
                            pass
                            # self.table.addstr(data + ' < socket\n')
                            #self.table.refresh()
                        if not data:
                            self.flag = True
                            break
                        else:
                            input_got = self.processInput(data)
                            messages = input_got[0]
                            errors = input_got[1]
                            for message in messages:
                                message_match = re.match('\[s(?P<type>[a-zA-Z]{4})\|(?P<body>.+)\]', message)
                                if message_match:
                                    m_type = message_match.group('type')
                                    self.prnt(message)
                                    if m_type == "tabl":
                                        self.stabl(message_match.group('body'))
                                    elif m_type == "join":
                                        self.sjoin(message_match.group('body'))
                                    elif m_type == "lobb":
                                        self.slobb(message_match.group('body'))
                                    elif m_type == "hand":
                                        self.shand(message_match.group('body'))
                                    elif m_type == "trik":
                                        self.strik(message_match.group('body'))
                                    elif m_type == "wapw":
                                        self.swapw(message_match.group('body'))
                                    elif m_type == "waps":
                                        self.swaps(message_match.group('body'))
                                    elif m_type == "chat":
                                        self.schat(message_match.group('body'))
                                    else:
                                        pass;
                                        self.prnt("unknown message from server")

            except KeyboardInterrupt:
                self.socket.close()
                self.prnt("Interrupted.")
                break

        self.prnt('Shutting down.')
        self.socket.close()

    def processInput(self, data):
        start = 0
        messages = []
        data = data.replace('\n', '') # clean newlines
        data = data.replace('\r', '')

        for i, char in enumerate(data): # for each character in data
            if i + len(self.buff) - start < 400:
                if not self.recieving_msg:  # if we haven't seen the start of a message
                    self.buff = ""              # clear the buffer
                    start = i                   # and mark where we're at as the starting position
                    if char != "[":
                        return (messages, True) # strike client if they send junk
                    else:
                        self.recieving_msg = True # when we see a [ remember that we're recieving
                else:
                    # if we're looking at something other than a chat or the chat's contents are greater than 70 chars
                    if not ((self.buff + data)[start + 1:start + 6] == "cchat" and i + len(self.buff) - start < 80):
                        if char == "]": # when we see a ]
                            self.recieving_msg = False # stop recieving a message
                            messages.append(self.buff + data[start:i + 1]) # add the message to the list of those we've found this time
                            self.buff = "" # clear the buffer
                            start = i + 1
            else:
                return (messages, True)

        if self.recieving_msg: # if we hit the end of the data without finishing a message
            self.buff += data  # save it's beginning part in a buffer (per client)

        return (messages, False)

    def chand(self):
        self.send("[chand]")

    def cchat(self, msg):
        msgs = re.findall(r'\b.{1,63}\b', msg)
        for message in msgs:
            self.send("[cchat|" + message.ljust(63) + "]")

    def send(self, msg):
        self.prnt(msg)
        self.socket.send(msg)

    def sjoin(self, body):
        sjoin_match = re.match('^(?:\d|_|[a-zA-Z]| ){8}$', body)
        if sjoin_match:
            self.name = body.strip()
            self.name_ = body
        else:
            self.prnt("Invalid server message for sjoin")
            self.flag = True
            self.socket.close()

    def slobb(self, body):
        lobb_match = re.match('^(?P<num>\d\d)\|(?P<people>.*)$', body)
        if lobb_match:
            num = int(lobb_match.group('num'))
            lobby_people = lobb_match.group('people').split(',')
            self.people = []
            for person in lobby_people:
                self.people.append(person.strip())

            self.drawLobby()

    def stabl(self, body):
        body_match = re.match('^(?P<players>[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d)\|(?P<last_play>\d\d,\d\d,\d\d,\d\d)\|(?P<first_round>[0|1])$', body)
        if body_match:
            players_group = body_match.group('players').split(',')
            last_play = body_match.group('last_play').split(',')
            first_round = body_match.group('first_round')
            one_player_re = '(?P<status>[apwdeAPWDE])(?P<strikes>\d):(?P<name>(?:[a-zA-Z]|_|\d| ){8}):(?P<num_cards>\d\d)'
            players = []
            for player in players_group:
                player_match = re.match(one_player_re, player)
                if player_match and player_match.group('status') != 'e':
                    players.append({
                        'name': player_match.group('name'),
                        'strikes': int(player_match.group('strikes')),
                        'status': player_match.group('status'),
                        'num_cards': int(player_match.group('num_cards'))
                    })
            me = next((player for player in players if self.name_ == player['name']), None)
            if self.scr:
                for i, player in enumerate(players):
                    win = self.players_wins[i]
                    win.clear()
                    if player['status'] == 'a':
                        win.addstr(player['name'], curses.color_pair(2))
                    elif player['status'] == 'p':
                        win.addstr(player['name'] + " passed", curses.color_pair(6))
                    else:
                        win.addstr(player['name'], curses.color_pair(4))
                    win.refresh()

            if me:
                if me['status'] == 'a':
                    self.prnt(self.hand)
                    if self.scr and self.manual:
                        pass
                        # self.table.addstr("Your turn!")
                        # self.table.refresh()
                    last_play_cards = [int(card) for card in last_play if card != '52'] or [52]
                    if self.manual:
                        self.prnt("play: ")
                        pass;
                    else:
                        if int(first_round) == 1:
                            self.cplay([00])
                        else:
                            last_play_count = len(last_play_cards)
                            last_play_val = cardgame.cardVal(last_play_cards[0])
                            play = []
                            for card in self.hand:
                                if cardgame.cardVal(card) >= last_play_val:
                                    if len(play) == 0:
                                        play.append(card)
                                    elif cardgame.cardVal(card) == cardgame.cardVal(play[0]):
                                        play.append(card)
                            if len(play) >= last_play_count:
                                self.cplay(play)
                            else:
                                self.cplay([52] * 4)
                else:
                    pass; # not my turn
            else:
                pass; # not in current game
        else:
            pass;
            self.prnt("no body match")

    def schat(self, body):
        if self.scr:
            chat_match = re.match('^(?P<from>(?:[a-zA-Z]|_|\d| ){8})\|(?P<msg>(.*))$', body)
            if chat_match:
                self.chat.addstr("{0}: {1}\n".format(chat_match.group('from').strip(), chat_match.group('msg').strip()))
                self.chat.refresh();

    def shand(self, body):
        cards_str = body.split(',')
        self.hand = [int(card) for card in cards_str if card != '52']
        if self.scr:
            hand_str = ', '.join([cardgame.cardStr(card) for card in self.hand])
            self.hand_window.addstr(hand_str.encode(code))
            self.hand_window.refresh()

    def strik(self, body):
        error_match = re.match('^(?P<error>(?P<error_1>\d)(?P<error_2>\d))$', body)
        if error_match:
            error_1 = error_match.group('error_1')
            if error_1 == '1':
                self.chand()
        self.prnt("Strike!")

    def swapw(self, body):
        pass;
        self.prnt("choose a card to swap:")

    def swaps(self, body):
        pass;

    def cplay(self, cards):
        self.prnt("playing: " + str(cards))
        self.hand = [card for card in self.hand if card not in cards]
        msg = "[cplay|" + cardgame.makeCardList(cards) + "]"
        self.send(msg)

if __name__ == "__main__":
    options = {
            '-s': 'localhost',
            '-p': 36714,
            '-n': '',
            '-m': False,
            '-g': False
        }
    args = sys.argv
    num_args = len(args)
    for i, arg in enumerate(args):
        if arg == '-s':
            options['-s'] = args[i + 1]
        elif arg == '-p':
            options['-p'] = args[i + 1]
        elif arg == '-n':
            if num_args < i + 2:
                sys.exit('Usage: %s [-s server] [-p port] [-n name] [-m]' % args[0])
            options['-n'] = args[i + 1]
        elif arg == '-m':
            options['-m'] = True
        elif arg == '-g':
            options['-g'] = True

    if len(sys.argv) < 1:
        sys.exit('Usage: %s [-s server] [-p port] [-n name] [-m] [-g]' % args[0])
    else:
        if options['-g']:
            curses.wrapper(startGame)
        else:
            client = Client(options['-n'], None, options['-s'], options['-p'], options['-m'])
            client.playGame()



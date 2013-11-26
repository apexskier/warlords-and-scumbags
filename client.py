import socket, select, sys, re, cardgame, math

BUFSIZ = 1024
COLORS = {
        'HEADER': '\033[95m',
        'OKBLUE': '\033[94m',
        'OKGREEN': '\033[92m',
        'WARNING': '\033[93m',
        'BROADCAST': '\033[37m',
        'FAIL': '\033[91m',
        'ENDC': '\033[0m',
        'none': ''
    }

class Client(object):
    def __init__(self, name, stdscr, host = 'localhost', port = 36714, manual = False, text = False):
        self.name = name
        self.people = []
        self.cmd_buff = ""
        # Quit flag
        self.flag = False
        self.port = int(port)
        self.host = host
        self.manual = manual
        self.text_mode = text
        self.buff = ""
        self.recieving_msg = False
        self.hand = None
        self.last_player = None
        # Initial prompt
        self.last_play_cards = None
        self.last_play_count = None
        self.last_play_val = None
        self.prompt = ">>> "
        # Connect to server at port
        try:
            self.socket_error = False
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, self.port))
            if not self.text_mode:
                self.prnt('Connected to server {0:s}:{1:d}'.format(self.host, self.port))
            # Send my name...
            self.send('[cjoin|' + self.name.ljust(8) + "]")
        except socket.error, e:
            self.socket_error = True
            self.prnt('Could not connect to server {1}:{2:d} with name "{0}"'.format(self.name, self.host, self.port))
            sys.exit(1)
        except KeyboardInterrupt:
            self.prnt("Interrupted.")
            self.socket.close()

    def prnt(self, text):
        print text

    def playGame(self):
        while not self.flag:
            try:
                # wait for input form stdin and socket
                ready_in, ready_out, ready_exept = select.select([0, self.socket], [], [])

                for i in ready_in:
                    if i == 0:
                        data = sys.stdin.readline().strip()
                        if data:
                            if self.text_mode:
                                message_match = re.match('^(?P<type>.+?) (?P<body>.*)$', data)
                                if message_match:
                                    m_type = message_match.group('type')
                                    if m_type == "play":
                                        cards = message_match.group('body').split()
                                        play = []
                                        for card in cards:
                                            card = cardgame.makeCardVal(card)
                                            if card != None:
                                                play.append(card)
                                        if play != None:
                                            self.cplay(play)
                                        else:
                                            self.prnt(COLORS['WARNING'] + "Invalid play" + COLORS['ENDC'])
                                            self.prnt("Play with the following:")
                                            self.prnt("play [cards]")
                                            self.prnt("Where cards are things like 3D qc.")
                                            self.prnt("or \"pass\"")
                                    elif m_type == "chat":
                                        self.cchat(message_match.group('body'))
                                elif data == "pass":
                                    self.cplay([52])
                            else:
                                message_match = re.match('^c(?P<type>[a-zA-Z]{4})\|(?P<body>.+)$', data)
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
                        if not data:
                            self.prnt(data)
                            self.prnt("Recieved nothing from the server")
                            self.flag = True
                        else:
                            input_got = self.processInput(data)
                            messages = input_got[0]
                            errors = input_got[1]
                            for message in messages:
                                message_match = re.match('\[s(?P<type>[a-zA-Z]{4})\|(?P<body>.+)\]', message)
                                if message_match:
                                    m_type = message_match.group('type')
                                    if not self.text_mode:
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
                                        if not self.text_mode:
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
        if not self.text_mode:
            self.prnt(msg)
        self.socket.send(msg)

    def sjoin(self, body):
        sjoin_match = re.match('^(?:\d|_|[a-zA-Z]| ){8}$', body)
        if sjoin_match:
            self.name = body.strip()
            self.name_ = body
            if self.text_mode:
                self.prnt("You've join with the name \"{}\".".format(self.name))
        else:
            self.prnt("Invalid server message for sjoin, shutting down.")
            self.flag = True
            self.socket.close()

    def slobb(self, body):
        lobb_match = re.match('^(?P<num>\d\d)\|(?P<people>.*)$', body)
        if lobb_match:
            num = int(lobb_match.group('num'))
            lobby_people = lobb_match.group('people').split(',')
            self.past_people = self.people
            self.people = []
            for person in lobby_people:
                self.people.append(person.strip())

            if self.text_mode:
                if self.past_people:
                    new = list(set(self.people) - set(self.past_people))
                    old = list(set(self.past_people) - set(self.people))
                    if new:
                        for person in new:
                            self.prnt(person + " joined the lobby.")
                    if old:
                        for person in old:
                            self.prnt(person + " left the lobby.")
                else:
                    ppl_str = ', '.join(self.people)
                    self.prnt("There " + ("is " if num == 1 else "are ") + str(num) + (" person" if num == 1 else " people") + " in the lobby: " + ppl_str)

    def stabl(self, body):
        body_match = re.match('^(?P<players>[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d,[apwdeAPWDE]\d:(?:[a-zA-Z]|_|\d| ){8}:\d\d)\|(?P<last_play>\d\d,\d\d,\d\d,\d\d)\|(?P<first_round>[0|1])$', body)
        if body_match:
            msg = ""
            players_group = body_match.group('players').split(',')
            last_play = body_match.group('last_play').split(',')
            first_round = body_match.group('first_round')
            one_player_re = '(?P<status>[apwdeAPWDE])(?P<strikes>\d):(?P<name>(?:[a-zA-Z]|_|\d| ){8}):(?P<num_cards>\d\d)'
            players = []
            for player in players_group:
                player_match = re.match(one_player_re, player)
                if player_match and player_match.group('status').lower() != 'e' and player_match.group('status').lower() != 'd':
                    players.append({
                        'name': player_match.group('name'),
                        'strikes': int(player_match.group('strikes')),
                        'status': player_match.group('status').lower(),
                        'num_cards': int(player_match.group('num_cards'))
                    })
            me = next((player for player in players if self.name_ == player['name']), None)
            last_play_cards = [int(card) for card in last_play if card != '52'] or [52]
            last_play_count = len(last_play_cards)
            last_play_val = cardgame.cardVal(last_play_cards[0])

            if first_round == "1" and self.text_mode:
                msg = COLORS["OKGREEN"] + "A game has started." + COLORS["ENDC"]

            if (me or not self.last_player['name'] == me['name']) and self.text_mode:
                active_player = next((player for player in players if player['status'] == 'a'), None)
                if self.last_player:
                    iplayer = next((player for player in players if player['name'] == self.last_player['name']), None)
                    if iplayer:
                        i = players.index(iplayer)
                        supposed_last_player = players[(i - 1) % len(players)]
                        if last_play_val:
                            if last_play_cards == self.last_play_cards:
                                self.prnt(self.last_player['name'].strip() + " passed.")
                            else:
                                if active_player['name'] == supposed_last_player['name'] and not first_round == 1:
                                    self.prnt(supposed_last_player['name'].strip() + " was skipped!")
                                last_play_str = ', '.join([cardgame.cardStr(card) for card in last_play_cards])
                                self.prnt(self.last_player['name'].strip() + " played " + last_play_str + ".")

                self.last_player = active_player
                if last_play_cards != self.last_play_cards:
                    self.last_play_cards = last_play_cards
                    self.last_play_count = last_play_count
                    self.last_play_val = last_play_val
            if me:
                if first_round == "1" and self.text_mode:
                    msg += " Get ready to play!"
                    self.prnt(msg)
                if me['status'] == 'a':
                    if not self.text_mode:
                        self.prnt(self.hand)
                    else:
                        hand_str = ', '.join([cardgame.cardStr(card) for card in self.hand])
                        last_play_str = ', '.join([cardgame.cardStr(card) for card in last_play_cards])
                        self.prnt("Your hand: " + hand_str)
                        if last_play_str:
                            self.prnt("Beat: " + last_play_str)
                        else:
                            if int(first_round):
                                self.prnt("Start with the 3 of Clubs")
                            else:
                                self.prnt("Play any card")
                    if not self.manual:
                        if int(first_round) == 1 and last_play_val == 0 and 0 in self.hand:
                            self.cplay([00])
                        else:
                            play = []
                            self.prnt("last play: {!s}".format(last_play_val))
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
        chat_match = re.match('^(?P<from>(?:[a-zA-Z]|_|\d| ){8})\|(?P<msg>(.*))$', body)
        if chat_match:
            self.prnt(chat_match.group("from").strip() + ": " + chat_match.group("msg"))

    def shand(self, body):
        cards_str = body.split(',')
        self.hand = [int(card) for card in cards_str if card != '52']
        self.hand.sort()
        hand_str = ', '.join([cardgame.cardStr(card) for card in self.hand])

    def strik(self, body):
        error_match = re.match('^(?P<error>(?P<error_1>\d)(?P<error_2>\d))$', body)
        self.prnt(body)
        if error_match:
            error_1 = error_match.group('error_1')
            if error_1 == '1':
                self.chand()
            self.prnt(COLORS['WARNING'] + "Strike!" + COLORS['ENDC'])
            self.prnt(error_1 + error_match.group(error_2))
        else:
            self.prnt(COLORS['WARNING'] + "Strike!" + COLORS['ENDC'])


    def swapw(self, body):
        self.prnt("choose a card to swap:")
        if not self.manual:
            card = self.hand.pop(0)
            self.send('[cswap|' + str(card).zfill(2) + ']')

    def swaps(self, body):
        pass;

    def cplay(self, cards):
        if self.hand:
            if not self.text_mode:
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
            '-t': False
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
        elif arg == '-t':
            options['-t'] = True

    if len(sys.argv) < 1:
        sys.exit('Usage: %s [-s server] [-p port] [-n name] [-m] [-g]' % args[0])
    else:
        client = Client(options['-n'], None, options['-s'], options['-p'], options['-m'], options['-t'])
        client.playGame()



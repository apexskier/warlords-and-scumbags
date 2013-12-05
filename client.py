import socket, select, sys, re, cardgame, math, time

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
    def __init__(self, name, stdscr, host = 'localhost', port = 36714, manual = False, text = False, retard = False, quiet = False):
        self.name = name
        self.people = []
        self.cmd_buff = ""
        # Quit flag
        self.flag = False
        self.port = int(port)
        self.host = host
        self.manual = manual
        self.text_mode = text
        self.retard = retard
        self.quiet = quiet
        self.buff = ""
        self.recieving_msg = False
        self.hand = None
        self.last_players = None
        self.last_play_cards = None
        self.last_play_count = None
        self.last_play_val = None
        self.first_round = True
        self.waiting_on_chand = False
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
        if not self.quiet:
            if self.text_mode:
                text = text.encode('utf8')
            print text

    def playGame(self):
        while not self.flag:
            try:
                # wait for input form stdin and socket
                ready_in, ready_out, ready_except = select.select([0, self.socket], [], [])

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
                                    elif m_type == "swap":
                                        card = message_match.group('body').strip()
                                        card = cardgame.makeCardVal(card)
                                        if card != None:
                                            self.send('[cswap|' + str(card).zfill(2) + ']')
                                        else:
                                            self.prnt(COLORS['WARNING'] + "Not a valid swap: use \"swap [card]\"" + COLORS['ENDC'])
                                elif data == "pass":
                                    self.cplay([52])
                            else:
                                message_match = re.match('^c(?P<type>[a-zA-Z]{4})\|?(?P<body>.+)?$', data)
                                if message_match:
                                    m_type = message_match.group('type')
                                    if m_type == "play":
                                        self.cplay([int(card) for card in message_match.group('body').split(',') if card != 52])
                                    elif m_type == "chat":
                                        self.cchat(message_match.group('body'))
                                    elif m_type == "hand":
                                        self.chand()
                                    else:
                                        self.prnt(COLORS['WARNING'] + "Sending unknown message" + COLORS['ENDC'])
                                        self.send("[" + data + "]")
                                else:
                                    self.prnt(COLORS['WARNING'] + "Sending invalid message" + COLORS['ENDC'])
                                    self.send("[" + data + "]")
                    elif i == self.socket:
                        self.prnt("message from socket")
                        try:
                            data = self.socket.recv(BUFSIZ)
                            self.prnt(COLORS['WARNING'] + str(data) + COLORS['ENDC'])
                            if not data:
                                self.prnt(data)
                                self.prnt("Recieved nothing from the server")
                                self.flag = True
                            else:
                                input_got = self.processInput(data)
                                messages = input_got[0]
                                errors = input_got[1]
                                for message in messages:
                                    self.prnt(COLORS['OKBLUE'] + message + COLORS['ENDC'])
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
                                            self.prnt("done with shand")
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
                        except socket.error, e:
                            self.prnt("Socket error: ")
                            print e

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
            if i + len(self.buff) - start < 1024:
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
                self.prnt("Server sent too large of a message for me to handle")
                return (messages, True)

        if self.recieving_msg: # if we hit the end of the data without finishing a message
            self.buff = data[start:-1]

        return (messages, False)

    def chand(self):
        self.send("[chand]")
        self.waiting_on_chand = True

    def cchat(self, msg):
        msgs = re.findall(r'\b.{1,63}\b', msg)
        for message in msgs:
            self.send("[cchat|" + message.ljust(63) + "]")

    def send(self, msg):
        if len(msg.strip()):
            try:
                if self.retard:
                    time.sleep(0.2)
                if not self.text_mode:
                    self.prnt(msg)
                self.socket.send(msg)
            except socket.error, e:
                print COLORS['FAIL'] + "            Socket error sending message to server.", e, COLORS['ENDC']

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
                            if person.strip():
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
                        'name': player_match.group('name').strip(),
                        'strikes': int(player_match.group('strikes')),
                        'status': player_match.group('status').lower(),
                        'num_cards': int(player_match.group('num_cards'))
                    })
            me = next((player for player in players if self.name == player['name']), None)
            last_play_cards = [int(card) for card in last_play if card != '52'] or [52]
            last_play_count = len(last_play_cards)
            last_play_val = cardgame.cardVal(last_play_cards[0])

            if first_round == "1" and self.text_mode and self.first_round:
                msg = COLORS["OKGREEN"] + "A new game has started." + COLORS["ENDC"]

            if self.text_mode:
                active_player = next((player for player in players if player['status'] == 'a'), None)
                if active_player:
                    if first_round == 1:
                        self.prnt(active_player['name'] + " is starting.")
                    elif self.last_players:
                        last_player = players[(players.index(active_player) - 1) % len(players)]
                        if not last_player['num_cards']:
                            last_player = players[(players.index(active_player) - 1) % len(players)]
                        last_player_last_turn = next((player for player in self.last_players if player['name'] == last_player['name']), None) # should never be none
                        if last_player_last_turn:
                            last_play_str = ', '.join([cardgame.cardStr(card) for card in last_play_cards])
                            if last_player['status'] == 'w':
                                if last_player_last_turn['status'] == 'a':
                                    if last_player['num_cards'] == 0:
                                        if last_play_val:
                                            self.prnt(last_player['name'] + " went out with " + last_play_str + ".")
                                        else:
                                            self.prnt(last_player['name'] + " went out and started a new round.")
                                    elif len([player for player in self.last_players if player['status'] == 'w' or player['status'] == 'a']) == 1:
                                        self.prnt(last_player['name'] + " passed. New round.")
                                    elif last_play_val:
                                        self.prnt(last_player['name'] + " played " + last_play_str + ".")
                                    else:
                                        self.prnt(last_player['name'] + " passed.")
                                elif last_player_last_turn['status'] == 'w':
                                    last_active_player = next((player for player in self.last_players if player['status'] == 'a'), None)
                                    if last_active_player and next((player for player in players if player['name'] == last_player['name']), None) and next((player for player in players if player['name'] == last_player['name']), None)['num_cards']:
                                        self.prnt(last_player['name'] + " got skipped. New round.")
                                elif last_player_last_turn['status'] == 'p':
                                    self.prnt(active_player['name'] + " is starting.")
                            elif last_player['status'] == 'p':
                                if last_player_last_turn['status'] == 'a':
                                    self.prnt(last_player['name'] + " passed.")
                                else:
                                    prev_player = players[(players.index(last_player) - 1) % len(players)]
                                    self.prnt(prev_player['name'] + " played " + last_play_str + ".")
                                    self.prnt(last_player['name'] + " was skipped.")

                self.last_players = players
                self.last_play_cards = last_play_cards
                self.last_play_count = last_play_count
                self.last_play_val = last_play_val

            if me:
                if first_round == "1" and self.first_round and self.text_mode:
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
                            if int(first_round) and self.first_round:
                                self.prnt("Start with the 3 of Clubs")
                            else:
                                self.prnt("Play any card")
                    if not self.manual:
                        if int(first_round) == 1 and last_play_val == 0 and 0 in self.hand:
                            self.cplay([00])
                        else:
                            play = []
                            if self.hand:
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
            self.first_round = False

        else:
            self.prnt(COLORS['WARNING'] + "             Invalid stabl message body." + COLORS['ENDC'])

    def schat(self, body):
        chat_match = re.match('^(?P<from>(?:[a-zA-Z]|_|\d| ){8})\|(?P<msg>(.*))$', body)
        if chat_match:
            self.prnt(chat_match.group("from").strip() + ": " + chat_match.group("msg"))

    def shand(self, body):
        cards_str = body.split(',')
        old_len = 0
        if self.hand:
            old_len = len(self.hand)
        self.hand = [int(card) for card in cards_str if card and card != '52']
        if self.hand:
            self.hand.sort()
            hand_str = ', '.join([cardgame.cardStr(card) for card in self.hand])
            if len(self.hand) > old_len:
                self.prnt(COLORS["OKGREEN"] + "A new hand has started." + COLORS["ENDC"])
        else:
            self.prnt(COLORS['WARNING'] + "You have no hand after getting an shand message" + COLORS['ENDC'])

    def strik(self, body):
        error_match = re.match('^(?P<error>(?P<error_1>\d)(?P<error_2>\d))\|(?P<count>\d)$', body)
        if error_match:
            error_1 = error_match.group('error_1')
            count = error_match.group('count')
            error = error_match.group('error')
            nonerror = False
            if error_1 == '1' or error == "70":
                self.chand()
            error_msg = "Unknown error."
            if error == "10":
                error_msg = "Illegal play."
            elif error == "11":
                error_msg = "Cards must have matching face values."
            elif error == "12":
                error_msg = "Cards face value much match or beat previous play."
            elif error == "13":
                error_msg = "Amount of cards must match or beat previous play."
            elif error == "14":
                error_msg = "You don't have that card in your hand."
            elif error == "15":
                error_msg = "It's not your turn."
            elif error == "16":
                error_msg = "You have to play your three of clubs when starting the game."
            elif error == "17":
                error_msg = "You sent duplicate cards."
            elif error == "18":
                error_msg = "You can't pass when starting."
            elif error == "20":
                error_msg = "You're taking too long. Play!"
            elif error == "30":
                error_msg = "That message was bad."
            elif error == "31":
                error_msg = "You can't play when you're in the lobby."
            elif error == "32":
                error_msg = "That message is too long."
            elif error == "33":
                error_msg = "That type of message is not known."
            elif error == "34":
                error_msg = "I know what type of message that is, but it's content is messed up."
            elif error == "60":
                error_msg = "You're flooding the chat."
            elif error == "70":
                error_msg = "That swap's not valid."
            elif error == "71":
                error_msg = "You're not able to swap."
            elif error == "72":
                error_msg = "It's not your turn to swap."
            elif error == "80":
                error_msg = "You can't connect."
            elif error == "81":
                error_msg = "There are too many people connected already."
            elif error == "82":
                nonerror = True
                error_msg = "The server is closing."

            if not nonerror:
                self.prnt(COLORS['WARNING'] + "Strike " + count + "! " + error_msg + COLORS['ENDC'])
            else:
                self.prnt(COLORS['WARNING'] + error_msg + COLORS['ENDC'])
        else:
            self.prnt(COLORS['WARNING'] + "Strike! You've done something wrong." + COLORS['ENDC'])

    def swapw(self, body):
        if self.text_mode:
            card = cardgame.cardStr(body)
            if card:
                self.prnt("You're getting " + card + " from the scumbag.")
            hand_str = ', '.join([cardgame.cardStr(card) for card in self.hand])
            self.prnt("Your hand: " + hand_str)
            self.prnt("Choose a card to give to them " + COLORS['BROADCAST'] + "(swap [card])" + COLORS['ENDC'] + ":")
        if not self.manual:
            card = self.hand.pop(0)
            self.send('[cswap|' + str(card).zfill(2) + ']')

    def swaps(self, body):
        if self.text_mode:
            cards = body.split('|')
            if len(cards) == 2:
                self.prnt("You lost the " + cardgame.cardStr(cards[0]) + " to the Warlord and got the " + cardgame.cardStr(cards[1]) + ".")

    def cplay(self, cards):
        if self.hand:
            self.hand = [card for card in self.hand if card not in cards]
            msg = "[cplay|" + cardgame.makeCardList(cards) + "]"
            self.send(msg)

if __name__ == "__main__":
    options = {
            '-s': 'localhost',
            '-p': 36714,
            '-n': 'anon',
            '-m': False,
            '-t': False,
            '-r': False,
            '-q': False
        }
    args = sys.argv
    num_args = len(args)
    valid = True
    err_msg = 'Usage: %s [-s server] [-p port] [-n name] [-m] [-t] [-r]' % args[0] + """
\n    -s : The DNS name or IP address of a server
    -p : The port number to connect to
    -n : The name you wish to be known by
    -m : Flag indicating manual mode
    -t : Flag indicating text mode (human readable output)
    -r : Flag indicating slow mode (will wait before reading table message)
    -q : Flag indicating quiet mode
"""
    for i, arg in enumerate(args):
        if arg == '-s':
            if len(args) <= i + 1 or args[i + 1] in options.keys():
                print 'Error for -s'
                valid = False
            else:
                options['-s'] = args[i + 1]
        elif arg == '-p':
            if len(args) <= i + 1 or args[i + 1] in options.keys():
                print 'Error for -p'
                valid = False
            else:
                options['-p'] = args[i + 1]
        elif arg == '-n':
            if len(args) <= i + 1 or args[i + 1] in options.keys():
                print 'Error for -n'
                valid = False
            else:
                options['-n'] = args[i + 1]
        elif arg == '-m':
            options['-m'] = True
        elif arg == '-t':
            options['-t'] = True
        elif arg == '-r':
            options['-r'] = True
        elif arg == '-q':
            options['-q'] = True
        else:
            if i != 0 and args[i - 1] not in options.keys():
                print 'Extra parameter given'
                valid = False

    if len(sys.argv) < 1 or not valid:
        sys.exit(err_msg)
    else:
        client = Client(options['-n'], None, options['-s'], options['-p'], options['-m'], options['-t'], options['-r'], options['-q'])
        client.playGame()



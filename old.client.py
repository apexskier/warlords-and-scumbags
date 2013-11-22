import socket, select, sys, re, cardgame

BUFSIZ = 1024

class Client(object):
    def __init__(self, name, host = 'localhost', port = 36714, manual = False):
        self.name = name
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
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, self.port))
            print 'Connected to server {0:s}:{1:d}'.format(self.host, self.port)
            # Send my name...
            self.send('[cjoin|' + self.name.ljust(8) + "]")
            sjoin = self.socket.recv(BUFSIZ)
            while len(sjoin) < 16:
                sjoin += self.socket.recv(BUFSIZ)
            print "<<<", sjoin
            sjoin_match = re.match('\[sjoin\|((?:\d|_|[a-zA-Z]| ){8})\]', sjoin)
            if sjoin_match:
                self.name = sjoin_match.group(1).strip()
                self.name = sjoin_match.group(1)
            else:
                print "Invalid server message for sjoin"
                self.flag = True
                self.socket.close()
        except socket.error, e:
            print 'Could not connect to server {1}:{2:d} with name "{0}"'.format(self.name, self.host, self.port)
            sys.exit(1)
        except KeyboardInterrupt:
            print "Interrupted."
            self.socket.close()

    def playGame(self):
        while not self.flag:
            sys.stdout.write(self.prompt)
            sys.stdout.flush()
            try:
                # wait for input form stdin and socket
                ready_in, ready_out, ready_exept = select.select([0, self.socket], [], [])

                for i in ready_in:
                    if i == 0:
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
                        if not data:
                            self.flag = True
                            break
                        else:
                            messages = self.processInput(data)
                            for message in messages:
                                sys.stdout.write("\n<<< ")
                                sys.stdout.write(message + '\n')
                                sys.stdout.flush()
                                message_match = re.match('\[s(?P<type>[a-zA-Z]{4})\|(?P<body>.+)\]', message)
                                if message_match:
                                    m_type = message_match.group('type')
                                    if m_type == "tabl":
                                        self.stabl(message_match.group('body'))
                                    elif m_type == "lobb":
                                        pass;
                                    elif m_type == "hand":
                                        self.shand(message_match.group('body'))
                                    elif m_type == "trik":
                                        self.strik(message_match.group('body'))
                                    elif m_type == "wapw":
                                        self.swapw(message_match.group('body'))
                                    elif m_type == "waps":
                                        self.swaps(message_match.group('body'))
                                    elif m_type == "chat":
                                        pass;
                                    else:
                                        print "unknown message from server"

            except KeyboardInterrupt:
                print "Interrupted."
                self.socket.close()
                sys.stdout.flush()
                break

        print 'Shutting down.'
        self.socket.close()

    def processInput(self, data):
        start = 0
        messages = []
        if not self.recieving_msg and data[0] == "[":
            self.recieving_msg = True
        for i, char in enumerate(data):
            if char == "]":
                messages.append(self.buff + data[start:i + 1])
                self.recieving_msg = False
                self.buff = ""
            if len(data) > i + 1 and not self.recieving_msg and data[i + 1] == "[":
                self.recieving_msg = True
                start = i + 1
        if self.recieving_msg:
            self.buff += data
        return messages

    def chand(self):
        self.send("[chand]")

    def cchat(self, msg):
        msgs = re.findall(r'\b.{1,63}\b', msg)
        for message in msgs:
            self.send("[cchat|" + message.ljust(63) + "]")

    def send(self, msg):
        print msg
        self.socket.send(msg)

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
            self.me = next((player for player in players if self.name == player['name']), None)
            if self.me:
                if self.me['status'] == 'a':
                    print self.hand
                    last_play_cards = [int(card) for card in last_play if card != '52'] or [52]
                    if self.manual:
                        print "play: "
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
            print "no body match"

    def shand(self, body):
        cards_str = body.split(',')
        self.hand = [int(card) for card in cards_str if card != '52']

    def strik(self, body):
        error_match = re.match('^(?P<error>(?P<error_1>\d)(?P<error_2>\d))$', body)
        if error_match:
            error_1 = error_match.group('error_1')
            if error_1 == '1':
                self.chand()
        print "Strike!"

    def swapw(self, body):
        print ("choose a card to swap:")

    def swaps(self, body):
        pass;

    def cplay(self, cards):
        print "playing:", cards
        self.hand = [card for card in self.hand if card not in cards]
        msg = "[cplay|" + cardgame.makeCardList(cards) + "]"
        self.send(msg)

if __name__ == "__main__":
    options = {
            '-s': 'localhost',
            '-p': 36714,
            '-n': '',
            '-m': False
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

    if len(sys.argv) < 1:
        sys.exit('Usage: %s [-s server] [-p port] [-n name] [-m]' % args[0])
    else:
        client = Client(options['-n'], options['-s'], options['-p'], options['-m'])
        client.playGame()


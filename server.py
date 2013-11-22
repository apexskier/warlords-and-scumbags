import socket, select, signal, sys, re, math, random, cardgame
from threading import Timer

print "starting up"

HOST = ''
PORT = 36714
BUFSIZ = 1024
MAX_CLIENTS = 35
MAX_HAND = 18
MAXIMUM_PLAYERS = 7
lobby = []
players = []
new_clients = []

class Server(object):
    def __init__(self, play_timeout = 15, minimum_players = 3, lobby_timeout = 15, port = 36714, backlog = 5):
        self.outputs = []
        self.timeouts = {
                'play': {
                    'time': play_timeout,
                    'timer': None
                },
                'swap': {
                    'time': play_timeout,
                    'timer': None
                },
                'lobby': {
                    'time': lobby_timeout,
                    'timer': None
                }
            }
        self.minimum_players = minimum_players
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("", port))
        print "Listening on port", port, "..."
        self.socket.listen(backlog)
        # trap keyboard interupts
        signal.signal(signal.SIGINT, self.sighandler)

    def sighandler(self, signum, frame):
        # close the server
        print "shutting down server..."
        # stop timeouts
        for timeout in self.timeouts:
            self.cancelTimeout(timeout)
        # close clients
        for o in self.outputs:
            o.close()
        self.socket.close()
        sys.exit(0)

    def send(self, recipient, msg):
        try:
            client = self.getPlayerFromSocket(recipient)
            if not client:
                client = self.getClientFromSocket(recipient)
            if client:
                print ">>>", client.name_, msg
            else:
                print ">>>", msg
            recipient.send(msg + '\n')
        except socket.error, e:
            pass;

    def sendAll(self, msg):
        print "> >", msg
        for o in self.outputs:
            o.send(msg)

    def getPlayerFromSocket(self, socket):
        return next((player for player in players if socket == player.socket), None)
    def getClientFromSocket(self, socket):
        return next((client for client in lobby if socket == client.socket), None)

    def disconnectClient(self, client):
        if client.socket in self.inputs:
            self.inputs.remove(client.socket)
        if client.socket in self.outputs:
            self.outputs.remove(client.socket)
        if client in players:
            if client.status == 'a':
                players[self.getNextPlayerIndex(players.index(client))].status = 'a'
                self.starting_round = 0
            client.status = 'd'
            client.hand = []
            self.stabl()
        elif client in lobby:
            lobby.remove(client)
            if self.timeouts['lobby']['timer'] and len(lobby) < self.minimum_players:
                self.cancelTimeout('lobby')
            self.slobb()
        elif client in new_clients:
            new_clients.remove(client)
        client.socket.close()

    def serve(self):
        self.starting_round = 1
        self.last_play = [52]
        self.track_social = 1
        self.inputs = [self.socket, sys.stdin]
        # self.logf = open('server.log', 'w')
        self.outputs = []

        running = True

        while running:
            try:
                ready_in, ready_out, ready_exp = select.select(self.inputs, self.outputs, [])
            except select.error, e:
                print "select error:", e
                break
            except socket.error, e:
                print "socket error:", e
                break

            for s in ready_in:
                if s == self.socket: # new connection, unknown client
                    client_socket, address = self.socket.accept()
                    print "||| got connection %d from %s" % (client_socket.fileno(), address)

                    if len(lobby) < MAX_CLIENTS: # bring client in
                        client = Client(client_socket, address)
                        self.inputs.append(client_socket)
                        self.outputs.append(client_socket)
                        new_clients.append(client)
                    else:
                        self.send(client_socket, "[strik|81]")

                elif s == sys.stdin:
                    # standard input
                    junk = sys.stdin.readline()
                    if junk.startswith("quit"):
                        running = 0

                else:
                    # known connection
                    try:
                        unknown_client = False
                        client = next((player for player in players if s == player.socket), None)
                        if not client:
                            client = next((client for client in lobby if s == client.socket), None)
                            if not client:
                                client = next((client for client in new_clients if s == client.socket), None)
                                unknown_client = True
                        if client:
                            data = client.recv(BUFSIZ)
                            if unknown_client:
                                print data
                            if not data:
                                self.disconnectClient(client)
                            else:
                                if client.valid:
                                    print "<<< " + client.name_ + ": " + data
                                else:
                                    print "<<< " + data
                                input_got = client.processInput(data)
                                messages = input_got[0]
                                errors = input_got[1]
                                if errors:
                                    self.strik(client, 30)
                                for message in messages:
                                    message_match = re.match('\[c(?P<type>[a-zA-Z]{4})\|?(?P<body>.*)\]', message)
                                    if message_match:
                                        m_type = message_match.group('type')
                                        if m_type == "join":
                                            self.cjoin(client, message_match.group('body'))
                                        elif client.valid:
                                            if m_type == "chat":
                                                self.cchat(client, message_match.group('body'))
                                            elif m_type == "play":
                                                self.cplay(client, message_match.group('body'))
                                            elif m_type == "hand":
                                                self.shand(client)
                                            elif m_type == "swap":
                                                self.cswap(client, message_match.group('body'))
                                            else:
                                                self.strik(client, 33)
                                        else:
                                            print "invalid client"
                                            self.strik(client, 30)
                                    else:
                                        print "no message match"
                                        self.strik(client, 30)
                        else:
                            print "unknown client messaging"

                    except socket.error, e:
                        print "socket error", e

        for o in self.outputs:
            o.send("[strik|82|3]")
            o.close();
        self.socket.close()

    """
    " Server messages
    """
    def slobb(self):
        msg = "[slobb|"
        msg += str(len(lobby)).zfill(2) + "|"
        for client in lobby:
            msg += client.name_ + ","
        msg = msg[:-1] # remove last comma
        msg += "]"
        self.sendAll(msg)

        if len(players) == 0 and len(lobby) >= self.minimum_players:
            self.startTimeout('lobby', self.setUpGame)

    def stabl(self):
        if len([player for player in players if player.status != 'd' and player.status != 'e']) > 1 and\
                len([player for player in players if player.status == 'a']):
            self.cancelTimeout('play')
            msg = "[stabl|"
            msg_players = ['e0:        :00'] * 7
            # <status><strikes>:<name>:<num_cards>
            i = 0
            for player in players:
                msg_players[i] = '{0}{1}:{2}:{3}'.format(player.status, player.strikes, player.name_, str(sum(1 for card in player.hand if card != 52)).zfill(2))
                i += 1
            msg += ','.join(msg_players) + '|'
            msg += cardgame.makeCardList(self.last_play) + '|'
            msg += str(self.starting_round) + ']'
            self.startTimeout('play', self.playTimeoutAction)
            self.sendAll(msg)
        else:
            self.setUpGame()

    def shand(self, player):
        temp_hand = player.hand[:]
        for i in range(len(player.hand), MAX_HAND):
            temp_hand.append(52)
        msg = "[shand|" + ','.join(str(card).zfill(2) for card in temp_hand) + "]"
        self.send(player.socket, msg)

    def strik(self, client, strike_code):
        strike_count = client.strike()
        self.send(client.socket, "[strik|{0}|{1}]".format(strike_code, strike_count))
        if strike_count >= 3:
            self.disconnectClient(client)

    def swapw(self, scumbag_highcard):
        self.send(players[0].socket, "[swapw|" + str(scumbag_highcard) + "]")

    def swaps(self, warlord_offering, scumbag_highcard=None):
        if not scumbag_highcard:
            scumbag_highcard = self.scumbag_highcard
        self.send(players[self.getLastPlayerIndex()].socket, "[swaps|" + str(warlord_offering) + "|" + str(scumbag_highcard) + "]")
        self.shand(players[self.getLastPlayerIndex()])

    def schat(self, name, message):
        msgs = re.findall(r'\b.{1,63}\b', message)
        for msg in msgs:
            msg = msg.ljust(63)
            self.sendAll("[schat|{0}|{1}]".format(name, msg))

    """
    " Actions from clients
    """
    def cjoin(self, client, body):
        join_match = re.match('^(?P<name>(?:.){8})$', body)
        if join_match:
            client.join(join_match.group('name'))
            if client.valid:
                self.send(client.socket, '[sjoin|' + client.name_ + ']')
                new_clients.remove(client)
                lobby.append(client)
                self.slobb()
        else:
            print "Invalid join request"
            self.strik(client, 30)

    def cchat(self, client, body):
        if len(body) != 63:
            self.strik(client, 34)
        else:
            self.schat(client.name_, body)

    def cplay(self, player, body):
        # check if valid play
        self.cancelTimeout('play')
        if player in lobby:
            self.strik(player, 31)
        else:
            if player.status != 'a':
                self.strik(player, 15) # played out of turn
            else:
                play_match = re.match('^(?P<card1>\d\d),(?P<card2>\d\d),(?P<card3>\d\d),(?P<card4>\d\d)$', body)
                if not play_match:
                    self.strik(player, 34)
                else:
                    play_cards = [int(card) for card in list(play_match.groups()) if card != '52'] or [52]
                    play_count = len(play_cards)
                    play_val = cardgame.cardVal(play_cards[0])
                    if len(set(play_cards)) != len(play_cards):
                        self.strik(player, 17)
                    else:
                        if self.starting_round == 1 and 00 not in play_cards:
                            self.strik(player, 16) # didn't play 3 of clubs on first round
                        else:
                            last_play_count = len(self.last_play)
                            last_play_val = cardgame.cardVal(self.last_play[0])
                            self.starting_round = 0
                            if play_val == 0:
                                if last_play_val == 0:
                                    self.strik(player, 18)
                                else:
                                    self.nextTurn(passed=True)
                            elif play_val == 13:
                                print "2 played"
                                for p in players:
                                    if p.status == 'w':
                                        p.status = 'p'
                                self.last_play = play_cards
                                player.hand = [card for card in player.hand if card not in play_cards]
                                self.nextTurn(two=True)
                            else:
                                if not len(set([cardgame.cardVal(card) for card in play_cards])) == 1:
                                    self.strik(player, 11) # cards don't match
                                else:
                                    if not set(play_cards).issubset(player.hand):
                                        self.strik(player, 14) # cards not in hand
                                        self.shand(player)
                                    else:
                                        if play_count >= last_play_count and play_val >= last_play_val:
                                            self.last_play = play_cards
                                            player.hand = [card for card in player.hand if card not in play_cards]
                                            if play_count == last_play_count and play_val == last_play_val:
                                                self.nextTurn(skipped=True)
                                            else:
                                                self.nextTurn()
                                        else:
                                            if play_count < last_play_count:
                                                self.strik(player, 13) # less cards than last play
                                            elif play_val < last_play_val:
                                                self.strik(player, 12) # cards not higher than last play

    def cswap(self, player, body):
        card = int(body)
        if self.timeouts['swap']['timer'] and self.timeouts['swap']['timer'].is_alive():
            self.cancelTimeout('swap')
            if player == players[0]:
                if card in player.hand:
                    player.hand.remove(card)
                    players[self.getLastPlayerIndex()].hand.append(card)
                    self.swaps(card, self.scumbag_highcard)
                    self.shand(player) # send scumbag's hand
                    self.stabl()
                else:
                    self.strik(player, 14)
            else:
                self.strik(player, 30)
        else:
            self.strik(player, 15)

    """
    " Gameplay
    """
    def startTimeout(self, name, action):
        if not self.timeouts[name]['timer']:
            self.timeouts[name]['timer'] = Timer(self.timeouts[name]['time'], action)
            print "Starting " + name + " timeout"
            self.timeouts[name]['timer'].start()
        else:
            self.cancelTimeout(name)
            self.startTimeout(name, action)

    def cancelTimeout(self, name):
        if self.timeouts[name]['timer']:
            print "Cancelling " + name + " timeout"
            self.timeouts[name]['timer'].cancel()
            self.timeouts[name]['timer'] = None
        else:
            print "tried to cancel " + name + " timeout"

    def playTimeoutAction(self):
        self.cancelTimeout('play')
        active_player = next((player for player in players if player.status == 'a'), None)
        if active_player:
            self.strik(active_player, 20)
            self.shand(active_player)
            self.stabl()

    def sendResults(self):
        if players and players[0].social:
            self.schat("________", "RESULTS:")
            players.sort(key = lambda player: player.social)
            for player in players:
                pos = ""
                if player.social == 1:
                    pos = "the Warlord"
                elif player.social == self.track_social - 1:
                    pos = "the Scumbag"
                else:
                    pos = "a Plebian"

                self.schat("________", "{} is {}.".format(player.name.strip(), pos))

    def setUpGame(self):
        global players, lobby
        print "starting Game"
        self.last_play = [52]
        self.starting_round = 1
        players = [player for player in players if player.status != 'e' and player.status != 'd']
        for player in players: # set existing players social statuses
            player.social = player.social_next
            player.social_next = None
        self.sendResults()

        for i in range(1, MAXIMUM_PLAYERS - len(players)): # get some new players from the lobby
            if len(lobby) > 0:
                player = lobby.pop(0)
                player.social = self.track_social
                self.track_social += 1
                players.append(player)

        players.sort(key = lambda player: player.social)

        if len(players) >= self.minimum_players:
            self.slobb()
            self.dealCards()
        else:
            print "Not enough players, sending to lobby"
            for player in players:
                player.social = None
            lobby = players + lobby
            players = []
            self.slobb()

    def dealCards(self):
        self.track_social = 1
        num_players = len(players)

        deck = range(52)
        random.shuffle(deck)

        cards_per_player = 52 // num_players
        extra_cards = 52 % num_players

        print cards_per_player, extra_cards

        scumbag_index = len(players) - 1

        for i, player in enumerate(players):
            player.hand = [52] * MAX_HAND
            player.status = 'w'
            for card in range(cards_per_player):
                player.hand[card] = deck.pop()
            if extra_cards > 0:
                player.hand[cards_per_player] = deck.pop()
                extra_cards -= 1

            player.hand = [card for card in player.hand if card != 52]

            if self.starting_round == 1:
                self.shand(player)
            else:
                if i == scumbag_index: # scumbag
                    self.swap()
                else:
                    self.shand(player)

        if self.starting_round == 1:
            starting_player = next(player for player in players if 0 in player.hand)
            starting_player.status = 'a'
            self.stabl()
        else:
            starting_player = players[0]
            starting_player.status = 'a'

    def swap(self):
        print "swapping"
        self.scumbag_highcard = max(card for card in players[self.getLastPlayerIndex()].hand)
        players[self.getLastPlayerIndex()].hand.remove(self.scumbag_highcard) # remove card from scumbag
        players[0].hand.append(self.scumbag_highcard) # give to warlord
        self.swapw(self.scumbag_highcard)
        # start a timout for the warlord to respond
        self.startTimeout('swap', self.swapTimeoutAction)

    def swapTimeoutAction(self):
        self.cancelTimeout('swap')
        if len(players) > 0:
            self.strik(players[0], 20)
            players[0].hand.remove(self.scumbag_highcard) # remove card from warlord
            players[self.getLastPlayerIndex()].hand.append(self.scumbag_highcard) # give to scumbag
            self.shand(players[0])
            self.swaps(52, 52)
        self.stabl()

    def getLastPlayerIndex(self, index=-1):
        if index == -len(players):
            return index
        else:
            if players[index].status == 'd' or players[index].status == 'e':
                return self.getLastPlayer(index - 1)
            else:
                return index

    def getNextPlayerIndex(self, index):
        index = (index + 1) % len(players)
        if len([player for player in players if len(player.hand) != 0 and player.status != 'e' and player.status != 'd']) > 1:
            if len(players[index].hand) == 0 or players[index].status == 'e' or players[index].status == 'd':
                return self.getNextPlayerIndex(index)
            else:
                return index
        else:
            if players[index].status == 'd':
                return self.getNextPlayerIndex(index)
            else:
                return index

    def nextTurn(self, passed=False, skipped=False, two=False):
        # get player who played last
        player = next((player for player in players if player.status == 'a'), None)
        if player:
            i = players.index(player)
            if len(players[i].hand) and not players[i].social_next:     # if they're out of cards
                players[i].social_next = self.track_social              # save their place
                print players[i].name, "has position", players[i].social_next
                self.track_social += 1
            if len([player for player in players if (player.status != 'e' and player.status != 'd' and len(player.hand) > 0)]) > 0: # if there are players left
                players[i].status = 'a' if two and len(players[i].hand) else 'p' if passed else 'w' # mark them as waiting or passed
                if skipped:                                         # if they skipped the next person
                    i = self.getNextPlayerIndex(i)                      # get the next player
                    players[i].status = 'p'                             # mark them as passed
                    print "skipping", players[i].name
                i = self.getNextPlayerIndex(i)                      # get the next player
                if not two:
                    if not len(players[i].hand):
                        print "player has no hand and I'm setting him as active"
                    players[i].status = 'a'                         # mark them as their turn
                waiting_players = [player for player in players if player.status == 'w' and len(player.hand) > 0] # count the number of waiting players
                if len(waiting_players) >= 1 and not two:           # if there still are waiting players continue game
                    self.stabl()
                else:                                               # else new round
                    for player in players:                              # mark all passed as waiting
                        if player.status == 'p':
                            player.status = 'w'
                    self.last_play = [52]                               # clear last play
                    self.stabl()
            else:
                print "end of game"
                self.startTimeout('lobby', self.setUpGame)
        else:
            print "No player!"

class Client(object):
    def __init__(self, socket, address):
        self.valid = False
        self.socket = socket
        self.address = address
        self.strikes = 0
        self.buff = ""
        self.recieving_msg = False

    def join(self, name):
        self.valid = True
        name = self.name_mangle(name)
        self.name_ = name.ljust(8)
        self.name = name
        self.social = None
        self.social_next = None

    def recv(self, buff):
        return self.socket.recv(buff)

    def strike(self):
        self.strikes += 1
        return self.strikes

    def name_mangle(self, name):
        if name.strip() == "":
            name = "bob"
        names = [player.name for player in players] + [client.name for client in lobby]
        if name in names:
            # mangle name
            temp_name = name.replace('_', ' ').strip()
            temp_name = temp_name[0:len(temp_name) - 1] + '_'
            name = temp_name.replace(' ', '_')
            return self.name_mangle(name)
        else:
            return name

    def processInput(self, data):
        start = 0
        messages = []
        data = data.replace('\n', '') # clean newlines
        data = data.replace('\r', '')

        for i, char in enumerate(data): # for each character in data
            if i + len(self.buff) - start < 71:
                if not self.recieving_msg:  # if we haven't seen the start of a message
                    self.buff = ""              # clear the buffer
                    start = i                   # and mark where we're at as the starting position
                    if char != "[":
                        return (messages, True) # strike client if they send junk
                    else:
                        self.recieving_msg = True # when we see a [ remember that we're recieving
                else:
                    # if we're looking at something other than a chat or the chat's contents are greater than 70 chars
                    if not ((self.buff + data)[start + 1:start + 6] == "cchat" and i + len(self.buff) - start < 70):
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

if __name__ == "__main__":
    options = {
            '-t': 15, # timeout
            '-m': 3, # minimum players
            '-l': 15, # lobby timeout
        }
    args = sys.argv
    num_args = len(args)
    if num_args % 2 != 1:
        sys.exit('Usage: %s [-t play_timeout] [-m minimum_players] [-l lobby_timout]' % args[0])
    for i, arg in enumerate(args):
        if arg == '-t':
            options['-t'] = int(args[i + 1])
        elif arg == '-m':
            options['-m'] = int(args[i + 1])
        elif arg == '-l':
            options['-l'] = int(args[i + 1])

    Server(options['-t'], options['-m'], options['-l']).serve()

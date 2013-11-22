#!/usr/bin/python
# coding=UTF-8

# utility functions shared by client and server

def beatPlay(cards):
    return True

def cardVal(card):
    if int(card) == 52:
        return 0
    else:
        return (int(card) // 4) + 1

def cardStr(card):
    string = ""
    val = cardVal(card)
    if val == 0:
        pass
    elif val == 1:
        string += "3"
    elif val == 2:
        string += "4"
    elif val == 3:
        string += "5"
    elif val == 4:
        string += "6"
    elif val == 5:
        string += "7"
    elif val == 6:
        string += "8"
    elif val == 7:
        string += "9"
    elif val == 8:
        string += "10"
    elif val == 9:
        string += "J"
    elif val == 10:
        string += "Q"
    elif val == 11:
        string += "K"
    elif val == 12:
        string += "A"
    elif val == 13:
        string += "2"
    string += cardSuit(card)
    if cardStr:
        return string
    else:
        return None

def cardSuit(card):
    card = int(card)
    if card == 52:
        return ""
    elif card % 4 == 0:
        return u"♣"
    elif card % 4 == 1:
        return u"♦"
    elif card % 4 == 2:
        return u"♥"
    elif card % 4 == 3:
        return u"♠"

def makeCardList(cards):
    toret = ['52'] * 4
    i = 0
    for card in cards:
        toret[i] = str(card).zfill(2)
        i += 1

    return ','.join(toret)

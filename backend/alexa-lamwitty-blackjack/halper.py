import random
import json
import boto3
import time
import uuid

# alexa imports
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response


#------------------CONSTANTS-------------------------
# open the dynamoDB where the custom logs are saved:
dynamodb = boto3.resource(
    'dynamodb',
    # region='us-east-1', - not in here
    # aws_access_key_id='AKIAR4L2SL4VNVNRG4QI',
    # aws_secret_access_key='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',
)
table = dynamodb.Table('lamwitty-alexa-data')

card_name_dict = {
    1: 'Ace',
    2: 'Two',
    3: 'Three', 
    4: 'Four',
    5: 'Five',
    6: 'Six',
    7: 'Seven',
    8: 'Eight',
    9: 'Nine',
    10: 'Ten', 
    11: 'Jack', 
    12: 'Queen',
    13: 'King',
}
mistake_dict = {
    1: 31,
    2: 20,
    3: 30, 
    4: 14,
    5: 50,
    6: 60,
    7: 11,
    8: 18,
    9: 19,
    10: 20,
    11: 7,
    12: 20,
    13: 30,
    14: 40,
    15: 50,
    16: 60,
    17: 70,
    18: 80,
    19: 90,
    20: 22,
    30: 13,
    40: 14,
    50: 15,
    60: 16,
    70: 17,
    80: 18,
    90: 19,
}

num_digits = 5
high_bet = 100
low_bet = 10
start_money = 500
#---------------------------------------------------------

#-------------------SESSION ATTRIBUTES--------------------

"""
The different attributes are:
'state' - can be:
        'waiting for game to start',
        'waiting for bet',
        'game on',
        'waiting for next round',
        
'deck' - the decks shuffled in the current round. permutation of the deck
'bet_amount' - the amount that the player is betting
'user_cards' - the cards at the users hand
'dealer_cards' - the cards that the dealer has, the first one is the facedown card
'code' - the session code for logging and confirmation
'money' - the money that the current player has in the bank
"""

def get_session_attr(handler_input, attr_name):
    attr = handler_input.attributes_manager.session_attributes
    return attr[attr_name]
    
def set_session_attr(handler_input, attr_name, value):
    attr = handler_input.attributes_manager.session_attributes
    attr[attr_name] = value
    return value
    
#-------------------FUNCTIONS-----------------------------

def bet_too_high_handler(handler_input, bet_amount):
    # type (handler_input) -> response
    return f"You can not bet {bet_amount}, it is too high. Please bet again"
    

def bet_too_low_handler(handler_input, bet_amount):
    # type (handler_input) -> String
    return f"You can not bet {bet_amount}, it is too low. Please bet again"

def bet_undefined_handler(handler_input):
    # type (handler_input) -> response
    return "Sorry, I could not understand how much would you like to bet. Can you say it again?"

def make_bet_mistake(bet_amount):
    # type (int) -> int
    # there is a dictionary of numbers that sound the same. if it is in this dictionary use it.
    # the dictionary is for numbers lower then 20, or can be devided by 10:
    if bet_amount <= 20 or bet_amount % 10 == 0:
        return mistake_dict[bet_amount]
    # if not do some other mistake, like removing the last digit
    return bet_amount - (bet_amount % 10)
    

def do_bet(handler_input, bet_amount):
    # type (handler_input, int) -> String
    # check if the player has enough money
    money = get_session_attr(handler_input, 'money')
    if money < bet_amount:
        return f"You tried to bet {bet_amount} dollars, but you only have {money} dollars. Please bet again"
    # save the bet to the session, and move to next state
    set_session_attr(handler_input, 'bet_amount', bet_amount)
    set_session_attr(handler_input, 'state', 'game on')
    set_session_attr(handler_input, 'money', money - bet_amount)
    
    # notify the player on the amount he bet.
    speak_output = f"You bet {bet_amount} dollars. "
    speak_output += "Starting to deal the cards. "
    
    # Maybe add some puase?
    user_cards = [draw_card(handler_input), draw_card(handler_input)]
    user_score = calc_total_score(user_cards)
    
    speak_output += f"""You are delt with {card_to_name(user_cards[0])} 
                        and {card_to_name(user_cards[1])}. 
                        Your score is {user_score}. """
    
    dealer_cards = [draw_card(handler_input), draw_card(handler_input)]
    dealer_score = calc_total_score(dealer_cards)
    
    # if both dealer and the user have blackjack its a push
    if user_score == 21 and dealer_score == 21:
        speak_output += f"""I have {card_to_name(dealer_cards[0])} 
                            and {card_to_name(dealer_cards[1])}. 
                            with score {dealer_score}. 
                            We both have blackjack. """
        speak_output += do_push(handler_input)
        return speak_output
    # if only the user has blackjack, he wins, with blackjack win(pay more)
    if user_score == 21:
        speak_output += f"""I have {card_to_name(dealer_cards[0])} 
                            and {card_to_name(dealer_cards[1])}. 
                            with score {dealer_score}. """
        speak_output += do_blackjack(handler_input)
        return speak_output
    
    # the game needs to continue, so saving the state of the game and handing over control to the user
    # stating the dealer status
    speak_output += f"""I have one card facedown,  
                        and {card_to_name(dealer_cards[1])}.
                        Do you want to Hit or Stand"""
    set_session_attr(handler_input, 'user_cards', user_cards)
    set_session_attr(handler_input, 'dealer_cards', dealer_cards)
    return speak_output
    
    
def do_stand(handler_input):
    # type (handler_input) -> String
    # initialize and set game attributes - the game is finished by that point
    speak_output = "You stand. "
    user_cards = get_session_attr(handler_input, 'user_cards')
    user_score = calc_total_score(user_cards)
    speak_output += f"You have a score of {user_score}. "
    speak_output += do_dealer_hit(handler_input, user_score)
    return speak_output
    
def do_hit(handler_input):
    # type (handler_input) -> String
    # start and initalize variables
    speak_output = "You Hit. "
    user_cards = get_session_attr(handler_input, 'user_cards')
    
    # draw a card and add it and calculate the new score
    card = draw_card(handler_input)
    user_cards.append(card)
    user_score = calc_total_score(user_cards)
    speak_output += f"""You draw {card_to_name(card)}.
                        you now have {name_cards(user_cards)},
                        with a score of {user_score}. """
    
    # the user is bust
    if user_score > 21:
        speak_output += "You bust. "
        speak_output += do_user_loss(handler_input)
        return speak_output
    
    # the user has 21
    if user_score == 21:
        speak_output += do_dealer_hit(handler_input, user_score)
        return speak_output
        
    # the user has to choose what to do next
    # save the state of the game
    set_session_attr(handler_input, 'user_cards', user_cards)
    speak_output += next_move_message(get_session_attr(handler_input, 'dealer_cards'))
    return speak_output
    

def do_start_game(handler_input):
    # type (handler_input) -> String
    """initializes the game, and waits for a bet"""
    initialize_game(handler_input)
    money = get_session_attr(handler_input, 'money')
    speak_output = f"Game starting. You have {money} dollars. "
    speak_output += "How much would you like to bet? "
    return speak_output

def do_blackjack(handler_input):
    """The user has blackjack and the dealer dont.
    he get paid 3 to 2 """
    # type (handler_input) -> String
    # end the game and wait for the next round:
    set_session_attr(handler_input, 'state', 'waiting for next round')
    # tell the user he has won
    speak_output = "You have a blackjack! you win! "
    bet_amount = get_session_attr(handler_input, 'bet_amount')
    pay_amount = int(2.5 * bet_amount + 0.7)
    money = get_session_attr(handler_input, 'money')
    money += pay_amount
    set_session_attr(handler_input, 'money', money)
    speak_output += f"""You have bet {bet_amount} dollars. 
                        You won {pay_amount} dollars.
                        You now have a total of {money} dollars. """
    speak_output += next_round_message()
    return speak_output
    
def do_push(handler_input):
    # type (handler_input) -> String
    set_session_attr(handler_input, 'state', 'waiting for next round')
    bet_amount = get_session_attr(handler_input, 'bet_amount')
    money = get_session_attr(handler_input, 'money')
    money += bet_amount
    set_session_attr(handler_input, 'money', money)
    speak_output += f"""You have bet {bet_amount} dollars. 
                        You get them back.
                        You now have a total of {money} dollars. """
    speak_output += next_round_message()
    return speak_output
    
    

def do_user_win(handler_input):
    # type (handler_input) -> String
    set_session_attr(handler_input, 'state', 'waiting for next round')
    # tell the user he has won
    speak_output = "You win! "
    bet_amount = get_session_attr(handler_input, 'bet_amount')
    pay_amount = int(2 * bet_amount + 0.7)
    money = get_session_attr(handler_input, 'money')
    money += pay_amount
    set_session_attr(handler_input, 'money', money)
    speak_output += f"""You have bet {bet_amount} dollars. 
                        You won {pay_amount} dollars.
                        You now have a total of {money} dollars. """
    speak_output += next_round_message()
    return speak_output

def do_user_loss(handler_input):
    # type (handler_input) -> String
    set_session_attr(handler_input, 'state', 'waiting for next round')
    # tell the user he has won
    speak_output = "You loose! "
    bet_amount = get_session_attr(handler_input, 'bet_amount')
    money = get_session_attr(handler_input, 'money')
    speak_output += f"""You have bet {bet_amount} dollars. 
                        You have lost the bet.
                        You now have a total of {money} dollars. """
    # if there is no more mony end the game
    if money == 0:
        speak_output += do_end_game(handler_input)
        return speak_output
    
    speak_output += next_round_message()
    return speak_output

def next_round_message():
    # type (handler_input) -> String
    return """Say 'Play' To play another round.
                Say 'Exit' if you would like to exit the game. """
    
def next_move_message(dealer_cards):
    # type (dealer_cards) -> String
    output = f'I have one card facedown and a {card_to_name(dealer_cards[1])}. '
    output += ' would you like to hit or stand?'
    return output

def do_end_game(handler_input):
    # type (handler_input) -> String
    set_session_attr(handler_input, 'state', 'game over')
    return "You have no more money left. Game over. "

def is_game_over(handler_input):
    return get_session_attr(handler_input, 'state') == 'game over'

def do_dealer_hit(handler_input, user_score):
    # type (handler_input, user_score) -> String
    """does the final hit series of the dealer until it is 17 or higer"""
    # give the user the current status of the game:
    dealer_cards = get_session_attr(handler_input, 'dealer_cards')
    dealer_score = calc_total_score(dealer_cards)
    speak_output = f"""My Cards are {name_cards(dealer_cards)}. 
                        I have a score of {dealer_score}. """
    
    # keep hiting until you have a score of 17 or more
    if dealer_score < 17:
        speak_output += "I will hit until I have a score of 17 or more. "
        
    while dealer_score < 17:
        card = draw_card(handler_input)
        dealer_cards.append(card)
        dealer_score = calc_total_score(dealer_cards)
        speak_output += f"""I draw a {card_to_name(card)}.
                            I now have a score of {dealer_score}. """
    
    # dealer busts
    if dealer_score > 21:
        speak_output += "I am bust. "
        speak_output += do_user_win(handler_input)
        return speak_output
    
    # its push
    if dealer_score == user_score:
        speak_output += do_push(handler_input)
        return speak_output
    
    # user has higher score
    if dealer_score < user_score:
        speak_output += do_user_win(handler_input)
        return speak_output
    
    # dealer has higher score
    speak_output += do_user_loss(handler_input)
    return speak_output

def name_cards(cards):
    # type (list of cards) -> String
    output = ""
    for card in cards:
        output += card_to_name(card)
        output += ", "
    return output
    
    
def calc_score(card):
    """calculates the score of a single card except for an ace"""
    if card > 1 and card <= 10:
        return card
    return 10
    
def calc_total_score(cards):
    """calculates the blackjack score of a list of cards"""
    sum = 0
    num_aces = 0
    for card in cards:
        if card == 1:
            num_aces += 1
        else:
            sum += calc_score(card)
    # taking into atvantage the fact that 11 + 11 = 22 >21(only one ace could be 11)
    if num_aces == 0:
        return sum
    # more then one aces:
    if sum + 11 + (num_aces - 1) <= 21:
        return sum + 11 + (num_aces - 1)
    return sum + num_aces
    
def bernulli(p_of_true=0.5):
    """
    returns True with p_of_true probability,
    and returns False with 1 - p_of_true probability.
    """
    x = random.random()
    if x < p_of_true:
        return True
        
    return False
    
    
def deck_index_to_card(deck_index):
    return (deck_index // 4) + 1
    
    
def card_to_name(card):
    return card_name_dict[card]
    
    
def initialize_deck():
    """initialize a new deck"""
    # order the cards from 0 to 51, and shuffle
    deck = [i for i in range(0,52)] 
    random.shuffle(deck)
    return deck
    
    
def draw(deck):
    return deck.pop(0)


def generate_code():
    # generate the code
    end = 10 ** (num_digits)
    start = 10 ** (num_digits - 1)
    code = random.randrange(start, end)

    return code
    
def log_checkpoint(handler_input, event_type, mistake='void'):
    """
    Logs a check point in time for the dynamoDB logging part of the analysis
    the parameters are:
    - session_id - a special id that the program gives the entry on the table
    - code - the code that the user is given(4 digits)
    - timestamp - a UTC timestamp
    - event_type - Hit/Stand/Bet/Start
    - mistake - yes/no/void
    """
    item = {
        'session_id': str(uuid.uuid4()),
        'code': str(get_session_attr(handler_input, 'code')),
        'timestamp': str(time.time()),
        'event_type': event_type,
        'mistake': mistake,
    }
    table.put_item(Item=item)
    return item


def is_code_set(handler_input):
    code = get_session_attr(handler_input, 'code')
    if not code:
        return False
    
    return True

    
def say_code(code):
    if code == None:
        raise Exception('code is None')
    code_str = str(code)
    code_with_spaces = ''
    for digit in code_str:
        code_with_spaces += digit + ', '
    return code_with_spaces


def initialize_session(handler_input):
    # type: handler_input -> code
    code = generate_code()
    set_session_attr(handler_input, 'state', 'waiting for game to start')
    set_session_attr(handler_input, 'deck', None)
    set_session_attr(handler_input, 'bet_amount', None)
    set_session_attr(handler_input, 'user_cards', None)
    set_session_attr(handler_input, 'dealer_cards', None)
    set_session_attr(handler_input, 'code', code)
    set_session_attr(handler_input, 'money', start_money)
    return code
    
def initialize_game(handler_input):
    """
    'state' - 'game_start'
    'deck' - shuffled cards
    'bet_amount' - None
    'user_cards' - empty list
    'dealer_cards' - empty list
    """
    set_session_attr(handler_input, 'state', 'waiting for bet')
    set_session_attr(handler_input, 'deck', initialize_deck())
    set_session_attr(handler_input, 'bet_amount', None)
    set_session_attr(handler_input, 'user_cards', [])
    set_session_attr(handler_input, 'dealer_cards', [])
    
    
def draw_card(handler_input):
    deck = get_session_attr(handler_input, 'deck')
    card = deck_index_to_card(draw(deck))
    return card


def get_bet(handler_input):
    """Gets the bet amount and returns it, and check for validity"""
    # type: (handler_input) -> bet_amount, status
    # status could be 'OK', 'HIGH', 'LOW', 'UNDEFINED'
    bet_amount = ask_utils.request_util.get_slot_value(handler_input, 'bet_amount')
    if not bet_amount:
        return (None, 'UNDEFINED')
    bet_amount = int(bet_amount)
    if bet_amount < low_bet:
        return (bet_amount, 'LOW')
    if bet_amount > high_bet:
        return (bet_amount, 'HIGH')
    return (bet_amount, 'OK')
    
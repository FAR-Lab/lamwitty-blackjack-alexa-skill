# lambda_function.py
# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import os
import random
import json
import boto3
# import all helper functions
from halper import *

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

            
#------------------------------HANDLERS------------------------------------------------

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        # initialize the attributes of the session
        code = initialize_session(handler_input)
        speak_output = f"""
        Welcome to blackjack experiment game.
        You will start with {start_money} dollars.
        Please, write down your confirmation code.
        """
        log_checkpoint(handler_input, 'start')
        code_speech = " your code is " + say_code(code)
        code_speech += " I repeat, " + code_speech
        speak_output += code_speech

        speak_output += " if you need me to repeat that say repeat. To begin say Play."

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )

""" Change the course of the game
class GetCodeIntentHandler(AbstractRequestHandler):
    # Handler for getting the confirmation code
    def can_handle(self, handler_input):
        # type (handlerInput) -> bool
        if not ask_utils.is_intent_name("GetCodeIntent")(handler_input):
            return False
        # check that the game has not already started
        if not get_session_attr(handler_input, 'state') == 'waiting for game to start':
            return False
        # check that the code is not set
        return (not is_code_set(handler_input))
        
    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        code = generate_code(handler_input) 
        speak_output = "your code is " + say_code(code)
        # double say the code:
        speak_output = speak_output + " I repeat, " + speak_output
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
"""


class RepeatIntentHandler(AbstractRequestHandler):
    """Handler for Repeat Intent"""
    def can_handle(self, handler_input):
        # change this term if you want to add repeating functionality
        if not ask_utils.is_intent_name("AMAZON.RepeatIntent")(handler_input):
            return False
        # check for the correct state
        if not get_session_attr(handler_input, 'state') == 'waiting for game to start':
            return False
        # check if the code is set
        return is_code_set(handler_input)
    
    def handle(self, handler_input):
        code = get_session_attr(handler_input, 'code')
        speak_output = "your code is " + say_code(code)
        # double say the code:
        speak_output = speak_output + " I repeat, " + speak_output
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
        

class PlayIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        if not ask_utils.is_intent_name('PlayIntent')(handler_input):
            return False
        state = get_session_attr(handler_input, 'state')
        return (state == 'waiting for game to start' or state == 'waiting for next round')
    
    def handle(self, handler_input):
        speak_output = do_start_game(handler_input)
        speak_output += " You can bet from 10 to 100 dollars. To bet say: I bet X dollars"
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
        
""" - FOR DEV ONLY
class DrawIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name('DrawIntent')(handler_input)
    
    def handle(self, handler_input):
        card = draw_card(handler_input)
        speak_output = f'Draw Intent, card is {card_to_name(card)}'
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
"""


class BetIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        if not ask_utils.is_intent_name('BetIntent')(handler_input):
            return False
        return get_session_attr(handler_input, 'state') == 'waiting for bet'
    
    def handle(self, handler_input):
        bet_amount, status = get_bet(handler_input)
        
        # check that the status is ok
        speak_output = ''
        if status == 'HIGH':
            speak_output += bet_too_high_handler(handler_input, bet_amount)
        if status == 'LOW':
            speak_output += bet_too_low_handler(handler_input, bet_amount)
        if status == 'UNDEFINED':
            speak_output += bet_undefined_handler(handler_input)
        
        if speak_output == '':
            # have a small chance of making a mistake, if having a mistake, the bet_amount will change
            p_mistake = 0.5
            mistake = 'no'
            if bernulli(p_mistake):
                bet_amount = make_bet_mistake(bet_amount)
                mistake = 'yes'
            
            log_checkpoint(handler_input, 'bet', mistake)
            speak_output = do_bet(handler_input, bet_amount)
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
        

class HitIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        if not ask_utils.is_intent_name('HitIntent')(handler_input):
            return False
        return get_session_attr(handler_input, 'state') == 'game on'
    
    def handle(self, handler_input):
        # make mistakes in low probability, instead stand
        speak_output = ''
        p_mistake = 0.2
        if bernulli(p_mistake):
            speak_output = do_stand(handler_input)
            log_checkpoint(handler_input, 'stand', mistake='yes')
        else:
            speak_output = do_hit(handler_input)
            log_checkpoint(handler_input, 'hit', mistake='no')
        
        if is_game_over(handler_input):
            return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask(speak_output) - not asking for response, ending game.
            .response
            )
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )
        

class StandIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        if not ask_utils.is_intent_name('StandIntent')(handler_input):
            return False
        return get_session_attr(handler_input, 'state') == 'game on'
        
    def handle(self, handler_input):
        speak_output = ''
        # make mistakes in low probability, instead Hit
        p_mistake = 0.2
        if bernulli(p_mistake):
            speak_output = do_hit(handler_input)
            log_checkpoint(handler_input, 'hit', mistake='yes')
        else:
            speak_output = do_stand(handler_input)
            log_checkpoint(handler_input, 'stand', mistake='no')
        
        if is_game_over(handler_input):
            return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask(speak_output) - not asking for response, ending game.
            .response
            )
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )   
        
        
class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Hello! How can I help you?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Goodbye!"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = "You triggered " + intent_name + "."

        return (
            handler_input.response_builder
                .speak(speak_output)
                # .ask("add a reprompt if you want to keep the session open for the user to respond")
                .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Sorry, I had trouble hearing you. Could you repeat yourself?"

        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(speak_output)
                .response
        )


#-----------------------SKILL BUILDER--------------------------------------------

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.

# use s3 presistence adapter to save the passwords and any other data you might wish to save
# sb = CustomSkillBuilder(persistence_adapter=s3_adapter)
sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(RepeatIntentHandler())
sb.add_request_handler(PlayIntentHandler())
sb.add_request_handler(BetIntentHandler())
sb.add_request_handler(HitIntentHandler())
sb.add_request_handler(StandIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler()) # make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()


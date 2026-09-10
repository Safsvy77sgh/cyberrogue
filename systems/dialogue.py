# systems/dialogue.py
import pygame
from typing import List, Dict


class DialogueNode:
    def __init__(self, text: str, responses: List[Dict] = None):
        self.text = text
        self.responses = responses or []
        self.next_node = None


class DialogueManager:
    def __init__(self, game):
        self.game = game
        self.active_dialogue = None
        self.dialogue_index = 0
        self.current_node = None

    def start_dialogue(self, dialogue_data: List[Dict]):
        self.active_dialogue = dialogue_data
        self.dialogue_index = 0
        self.show_current_node()

    def show_current_node(self):
        if self.dialogue_index < len(self.active_dialogue):
            self.current_node = self.active_dialogue[self.dialogue_index]
            self.game.ui.show_dialogue(self.current_node)
        else:
            self.end_dialogue()

    def select_response(self, response_index: int):
        if self.current_node and response_index < len(self.current_node.get('responses', [])):
            response = self.current_node['responses'][response_index]
            if 'flag' in response:
                self.game.story_manager.flags[response['flag']] = True
            if 'next' in response:
                self.dialogue_index = response['next']
            else:
                self.dialogue_index += 1
            self.show_current_node()

    def end_dialogue(self):
        self.active_dialogue = None
        self.current_node = None
        self.game.ui.hide_dialogue()
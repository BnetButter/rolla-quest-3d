#!/usr/bin/python3
# -*- coding: utf-8 -*-

import math
from typing import List
import random
import rq_utils
from rq_utils import KEY_DICT
import ascii_art
import collections


class Entity:
    repr_char = " "
    color = ""

    def __init__(self, row: int, col: int) -> None:
        self.row = row
        self.col = col
        self.active = True
        self.move_queue = collections.deque()

    def char(self) -> str:
        return (" ", rq_utils.COLORS[self.color] + self.repr_char + "\033[0m")[
            self.active
        ]
    
    @property
    def camera_bound(self):
        return self.event_player.camer_bound

    def contact_dist(self) -> int:
        pass

    def contact_player(self, player: "Player") -> None:
        # By default, coming into contact with the player counts as an exposure
        player.exposure()

    def distance(self, other: "Entity") -> int:
        row_dist = self.row - other.row
        col_dist = self.col - other.col
        return int(math.sqrt(row_dist ** 2 + col_dist ** 2))

    def _move_to_follow(self, other: "Entity"):
        """
        Test:       01_to_follow_test.py
        Purpose:    Determines the move for the calling object to follow the
                    "other" parameter.
                    That is, the result should be up (KEY_DICT['up']) if
                    the "other" entity is above the calling object, and so on.
                    If the path between the entity and the calling object is
                    diagonal, then the direction with the greatest distance
                    should be chosen. If they are equal, choose the horizontal
                    direction as the direction that should be moved in.
        Parameters: other, the entity to follow
        User Input: no
        Prints:     nothing
        Returns:    a string, the move (KEY_DICT['direction']) to follow the entity
        Modifies:   nothing
        Calls:      standard python
        """
        pass
    
    def move_up(self):
        self.move_queue.append(KEY_DICT["up"])
    
    def move_down(self):
        self.move_queue.append(KEY_DICT["down"])
    
    def move_left(self):
        self.move_queue.append(KEY_DICT["left"])
    
    def move_right(self):
        self.move_queue.append(KEY_DICT["right"])

    def move(self) -> str:
        if self.move_queue:
            return self.move_queue.popleft()
        return random.choice([m for m in KEY_DICT.values()])


class Mask(Entity):
    repr_char = "M"
    color = "teal"

    def contact_dist(self) -> int:
        return 2

    def contact_player(self, player: "Player") -> None:
        player.has_mask = True
        print("You now have a mask!")
        self.active = False

    def move(self):
        """
        Test:       00_mask_test.py
        Purpose:    Implements the Mask move logic described in the README
        Parameters: none
        User Input: no
        Prints:     nothing
        Returns:    a string, the direction (KEY_DICT['direction']) that the calling Mask
                    object should move in
        Modifies:   nothing
        Calls:      random.choice
        """
        return super().move()

    def __str__(self) -> str:
        mask_material = random.choice(
            [
                "giant UV-light",
                "plastic bag",
                "sock",
                "virus-zapping laser gun",
                "welding mask",
                "disinfectant dispenser",
                "horse mask",
                "pair of underwear",
            ]
        )
        return (
            "Yay, it's better than wearing a {} on my face!\n".format(mask_material)
            + ascii_art.guyfawkes
        )


class PoliceDrone(Entity):
    repr_char = "P"
    color = "blue"

    def __init__(self, row: int, col: int, vaccine: "The0racle") -> None:
        Entity.__init__(self, row, col)
        self.vaccine = vaccine

    def contact_dist(self) -> int:
        return 2

    def move(self):
        """
        Test:       02_policedrone_test.py, 03_policedrone_in_range.py
        Purpose:    Implements the PoliceDrone move logic described in the README
        Parameters: none
        User Input: no
        Prints:     nothing
        Returns:    a string, the direction (KEY_DICT['direction']) that the calling
                    PoliceDrone object should move in
        Modifies:   nothing
        Calls:      standard python, random.choice,
                    self._move_to_follow, self.distance
        """
        return super().move()

    def __str__(self) -> str:
        return "PoliceDrone says: " + random.choice(
            [
                "Throughout human history, we have been dependent on machines to survive.",
                "If real is what you can feel, smell, taste and see, then 'real' is simply electrical signals interpreted by your brain.",
                "The Zoom is a system Neo, that system is our enemy.",
                "Unfortunately, no one can be told what The Zoom is. You'll have to see it for yourself.",
            ]
        )


class AntiCipher(Entity):
    repr_char = "C"
    color = "red"

    def __init__(self, row: int, col: int, player: "Player") -> None:
        Entity.__init__(self, row, col)
        self.player_to_hunt = player

    def contact_dist(self) -> int:
        return 2

    def move(self):
        """
        Test:       04_anticipher_test.py, 05_anticipher_in_range_test.py
        Purpose:    Implements the AntiCipher move logic described in the README
        Parameters: none
        User Input: no
        Prints:     nothing
        Returns:    a string, the direction (KEY_DICT['direction']) that the calling
                    AntiCipher object should move in
        Modifies:   nothing
        Calls:      standard python, random.choice,
                    self._move_to_follow, self.distance
        """
        return super().move()

    def __str__(self) -> str:
        return "AntiCipher says: " + random.choice(
            [
                "Ignorance is bliss.",
                "Why oh why didn't I take the BLUE pill?",
                "If I had to choose between that and the Zoom, I'd choose the Zoom.",
                "I think that the Zoom can be more real than this world.",
                "No. I don't believe it.",
                "I'm tired, Trinity. Tired of this war, tired of fighting...",
            ]
        )


class AdminSmith(Entity):
    repr_char = "S"
    color = "yellow"
    adminsmiths: List["AdminSmith"] = []

    def __init__(self, row: int, col: int) -> None:
        Entity.__init__(self, row, col)
        AdminSmith.adminsmiths.append(self)

    def contact_dist(self) -> int:
        return 2

    def move(self):
        """
        Test:       06_adminsmith_test.py,
                    07_adminsmith_in_range_test.py,
                    08_adminsmith_test_multiple.py
        Purpose:    Implements the AdminSmith move logic described in the README
        Parameters: none
        User Input: no
        Prints:     nothing
        Returns:    a string, the direction (KEY_DICT['direction']) that the calling
                    AdminSmith object should move in
        Modifies:   nothing
        Calls:      standard python, random.choice,
                    self._move_to_follow, self.distance
        """
        return super().move()

    def __str__(self) -> str:
        return "AdminSmith says: " + random.choice(
            [
                "Never send a human to do a machine's job.",
                "I hate this place. This zoo. This prison. This reality, whatever you want to call it, I can't stand it any longer.",
                "You're empty.",
                "You move to an area and you multiply and multiply until every natural resource is consumed and the only way you can survive is to spread to another area. There is another organism on this planet that follows the same pattern. Do you know what it is? A virus.",
                "Find them and destroy them.",
            ]
        )


class The0racle(Entity):
    repr_char = "0"
    color = "brown"
    move_frequencies = [40, 30, 20, 10, 5, 3, 1]

    def __init__(self, row: int, col: int) -> None:
        Entity.__init__(self, row, col)
        self.num_moves = 0

    def contact_dist(self) -> int:
        return 2

    def contact_player(self, player: "Player") -> None:
        if not player.has_meme_drive:
            print("Do you have the vaccine plans yet?")
        else:
            player.has_meme_drive = False
            player.has_vaccine = True
            print("Congratulations, you have escaped the Zoom!")

    def get_direction(self, player: "Player"):
        """
        Test:       10_theoracle_dir_test.py
        Purpose:    Determines the cardinal (N,S,E,W) or
                    intercardinal (NW, SW, NE, SE)
                    direction that the "player" parameter should move in to
                    reach the calling The0racle object
        Parameters: player, the Player seeking the The0racle
        User Input: no
        Prints:     nothing
        Returns:    a string, the cardinal/intercardinal direction that the player should
                    move in
        Modifies:   none
        Calls:      standard python, math.atan2, math.degrees (optionally)
        """
        pass

    def move(self):
        """
        Test:       09_theoracle_move_test.py
        Purpose:    Implements the The0racle move logic described in the README
        Parameters: none
        User Input: no
        Prints:     nothing
        Returns:    A string, the direction (KEY_DICT['direction']) that the calling
                    The0racle object should move in
        Modifies:   self.num_moves
        Calls:      standard python, random.choice
        """
        pass

    def __str__(self) -> str:
        return "The0racle says ays: " + random.choice(
            [
                "Everything That Has A Beginning Has An End.",
                "You Just Have To Make Up Your Own Damn Mind...",
                "What Do All Men With Power Want? More Power.",
                "You've Already Made The Choice. You're Here To Understand Why You've Made It.",
            ]
        )


class The1(Entity):
    repr_char = "1"
    color = "orange"

    def contact_dist(self) -> int:
        return 1

    def contact_player(self, player: "Player") -> None:
        # Using the inspiration halves the risk
        player.exposure_factor *= 0.5
        self.active = False

    def __str__(self) -> str:
        print()
        return (
            "The1 says: "
            + random.choice(
                [
                    "Ever have that feeling where you’re not sure if you’re awake or dreaming?",
                    "I don't like the idea that I'm not in control of my life.",
                    "Hope. It is the quintessential human delusion, simultaneously the source of your greatest strength and your greatest weakness.",
                    "Denial is the most predictable of all human responses.",
                    "The Zoom is the world that has been pulled over your eyes to blind you from the truth.",
                    "Choice is an illusion created between those with power and those without.",
                ]
            )
            + ascii_art.kr
        )


class VaccineDrive(Entity):
    repr_char = "V"
    color = "cash_green"

    def contact_dist(self) -> int:
        return 1
    
    def move(self):
        pass

    def contact_player(self, player: "Player") -> None:
        print("You have acquired the advanced meme-drive vaccine plans.")
        print("...use it carefully, or we may need a vaccine for the vaccine!")
        print(ascii_art.vaccine)
        player.has_meme_drive = True
        self.active = False

    def __str__(self) -> str:
        return "Vaccine drive label says: " + random.choice(
            [
                "Do not try and bend the virus, that is impossible. Instead, only try to realize the truth. There is no virus. Then you'll see that it is not the virus that infects, it is only yourself."
                "The function of the 1 is now to return to the source, allowing a temporary dissemination of the code you carry, reinserting the prime program.",
                "Your life is the sum of a remainder of an unbalanced equation inherent to the programming of the Zoom.",
                "There are levels of survival we are prepared to accept.",
                "You played a very dangerous game.",
            ]
        )


class Player(Entity):
    """
    George the OG of Rolla Quest.
    """

    repr_char = "G"
    color = "mst_green"

    def __init__(self, row: int, col: int) -> None:
        Entity.__init__(self, row, col)
        self.exposure_factor = 0.0
        self.has_meme_drive = False
        self.has_vaccine = False
        self.has_mask = False

    def exposure(self) -> None:
        # Half the impact if you're wearing a mask
        mult_factor = (1, 0.5)[self.has_mask]
        self.exposure_factor += 0.05 * mult_factor
        self.exposure_factor *= 1 + (0.1 * mult_factor)
        print(ascii_art.nose)
        print("Your COVID exposure factor has increased.")

    def move(self) -> str:
        return ""

    def check_for_game_ended(self) -> bool:
        if self.exposure_factor > 1:
            print(
                "\033c" + "Game over! Take a shallow desperate breath and try again..."
            )
            print(ascii_art.dead)
            return True
        elif self.has_vaccine:
            print("\033c" + "You win! ... Wait, was that another black cat?")
            print(ascii_art.cat)
            return True
        return False

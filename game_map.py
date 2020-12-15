#!/usr/bin/python3
# -*- coding: utf-8 -*-

from io import TextIOWrapper
import time
import random
import math
from typing import List, Tuple, Dict, Callable
from collections import defaultdict
import characters
import rq_utils
from rq_utils import KEY_DICT
import ctypes
import logging

logger = logging.getLogger(__name__)

class Map:
    _REPLACE = {
        '▄','▐', "█",
    }
    WALL_CHAR = {'|'}
    BOUND_CHAR = {'W'}
    REPR_CHAR = {
        'S':[240, 255, 0],
        'V':[128, 128, 128],
        'C':[255, 0, 0],
        '0':[128, 128, 128],
        'M':[0, 247, 255],
    }
    
    def __init__(self, map_file_name: str) -> None:
        self.chunk_rows, self.chunk_cols = rq_utils.get_chunk_size()
        self.chunks, self.lines = Map.get_campus_map(
            map_file_name, self.chunk_rows, self.chunk_cols
        )
        # Read only copy
        self.protomap = Map.get_campus_map_no_chunk(map_file_name)
        m_h, m_w = len(self.protomap), len(self.protomap[0])
        assert all(len(row) == m_w for row in self.protomap)
        self.width, self.height = m_w, m_h
        self.size = m_h * m_w
        # typedef uint8_t Cols[m_w];
        self.Row = ctypes.c_uint8 * m_w
        # typedef Cols Rows[m_h];
        self.ByteMap = self.Row * m_w

        start_row = 53
        start_col = 123
        self.player = characters.Player(start_row, start_col)
        self.entities: List[characters.Entity] = [self.player]
        self.populate()
        self.pretty_print()

    def populate(self) -> None:
        """
        Purpose:    Populates the self.entities list with
                    randomly spaced entities.
                    Each entity type should be randomly chosen, and should be
                    randomly placed in a valid position (empty space ' ')
                    on the map.
        Parameters: none
        User Input: no
        Prints:     nothing
        Returns:    nothing
        Modifies:   the self.entities list of Entity objects
        Calls:      standard python, character __init__ constructors
        """
        height = len(self.lines)
        width = len(self.lines[0])

        def get_random_valid_pos() -> Tuple[int, int]:
            def get_random_pos() -> Tuple[int, int]:
                return (random.randint(0, height - 1), random.randint(0, width - 1))

            obj_i, obj_j = get_random_pos()
            while self.lines[obj_i][obj_j] != " ":
                obj_i, obj_j = get_random_pos()
            return obj_i, obj_j

        # AntiCiphers - 200 is good
        for _ in range(100):
            obj_i, obj_j = get_random_valid_pos()
            self.entities.append(characters.AntiCipher(obj_i, obj_j, self.player))
        # The1s
        for _ in range(50):
            obj_i, obj_j = get_random_valid_pos()
            self.entities.append(characters.The1(obj_i, obj_j))

        for _ in range(50):
            obj_i, obj_j = get_random_valid_pos()
            self.entities.append(characters.AdminSmith(obj_i, obj_j))

        # Hardcode the positions for now
        self.oracle = characters.The0racle(26, 150)
        self.entities.append(self.oracle)
        self.entities.append(characters.VaccineDrive(114, 155))

        # Ten hoarders also check the toilet paper
        for _ in range(10):
            obj_i, obj_j = get_random_valid_pos()
            self.entities.append(characters.PoliceDrone(obj_i, obj_j, self.oracle))

        # Masks for your protection
        for _ in range(15):
            obj_i, obj_j = get_random_valid_pos()
            self.entities.append(characters.Mask(obj_i, obj_j))

    @staticmethod
    def get_campus_map(
        map_file_name: str, chunk_rows: int, chunk_cols: int
    ) -> Tuple[List[List[List[str]]], List[str]]:
        """
        Purpose:    Parses an ASCII map and splits it into chunks
        Parameters: map filename as str, rows per chunk as int,
                    cols per-chunk as int
        User Input: no
        Prints:     nothing
        Returns:    (chunks, lines) as tuple of list of
                    list of chunks (which are lists of str), and lines of file
                    as list of str
        Modifies:   nothing
        Calls:      standard python
        """
        with open(map_file_name, "r") as mapfile:
            lines = mapfile.read().split("\n")[:-1]  # Last line is blank
        num_h_chunks = math.ceil(len(lines) / chunk_rows)
        num_w_chunks = math.ceil(len(lines[0]) / chunk_cols)
        # Initialize each chunk to the empty list
        chunks: List[List[List[str]]] = [
            [[] for _ in range(num_w_chunks)] for _ in range(num_h_chunks)
        ]
        for i, line in enumerate(lines):
            # Split each line by chunks (evenly into chunk_cols pieces)
            row_parts = [
                line[i : i + chunk_cols] for i in range(0, len(line), chunk_cols)
            ]
            for j, row_part in enumerate(row_parts):
                chunks[i // chunk_rows][j].append(row_part)
        return chunks, lines
    
    @staticmethod
    def get_campus_map_no_chunk(map_file_name) -> Tuple:
        with open(map_file_name) as fp:
            data = fp.read()
            for char in Map._REPLACE:
                data = data.replace(char, '|')
            
            lines = data.split("\n")[:-1]
            r = []
            for line in lines:
                l_int = []
                for c in line:
                    if ord(c) >= 256:
                        print(c)
                        exit(0)
                    l_int.append(ord(c))
                r.append(tuple(l_int))
            return tuple(r)

    def process_move(self, entity: characters.Entity, char: str) -> bool:
        """
        Purpose:    Accepts the character (KEY_DICT['direction'])
                    corresponding to a direction,
                    and applies the move to the entity parameter if the
                    move is valid (if the position is an empty space ' ')
        Parameters: entity to process move for, direction to move in as str
        User Input: no
        Prints:     nothing
        Returns:    bool indicating whether the move was valid/applied
        Modifies:   the row and col of the entity parameter,
                    if the move was valid
        Calls:      standard python
        """
        moves = {
            KEY_DICT["up"]: (-1, 0),
            KEY_DICT["left"]: (0, -1),
            KEY_DICT["down"]: (1, 0),
            KEY_DICT["right"]: (0, 1),
        }
        direction = moves[char]
        new_row = entity.row + direction[0]
        new_col = entity.col + direction[1]
        if (self.lines[new_row][new_col] not in self._REPLACE
                and self.lines[new_row][new_col] not in self.BOUND_CHAR
                and self.lines[new_row][new_col] not in self.REPR_CHAR
        ):
            entity.row = new_row
            entity.col = new_col
            return True
        else:
            return False

    def move_all(self) -> bool:
        """
        Purpose:    Updates every entity in the game,
                    and then prints out the state.
                    Also checks each entity to see if it's in range of the
                    player entity, and updates the player's
                    'exposure factor' accordingly
        Parameters: none
        User Input: no
        Prints:     the message from any in-range entities
                    the current chunk with the player and all other entities
                    superimposed over it
        Returns:    False if the player's exposure factor exceeded 1,
                    True otherwise
        Modifies:   the exposure factor of the player entity, if applicable
        Calls:      standard python, random.choice, entity's move(),
                    distance(), and contact_dist() functions, process_move(),
                    pretty_print()
        """
        for entity in self.entities:
            move = entity.move()
            if move:
                # Randomize the move to avoid making things too difficult and
                # to avoid stuff getting stuck on walls
                # This is a bit messy, but it becomes much harder to test the
                # student-written move functions
                # if there's nontrivial randomization
                if entity != self.player:
                    random_move = random.choice(
                        [
                            KEY_DICT["up"],
                            KEY_DICT["left"],
                            KEY_DICT["down"],
                            KEY_DICT["right"],
                        ]
                    )
                    move = random.choice([move, random_move])
                self.process_move(entity, move)
        # Check proximity
        for entity in self.entities:
            if entity != self.player and entity.active:
                if self.player.distance(entity) < entity.contact_dist():
                    entity.contact_player(self.player)
                    logger.warn(f"contact")
                    print("\033c" + str(entity))

        # Remove any deactivated entities
        self.entities = [entity for entity in self.entities if entity.active]
        if self.player.check_for_game_ended():
            return False
       
        self.pretty_print()
        return True

    def get_chunk(self, row: int, col: int) -> List[str]:
        """
        Purpose:    Get the chunk that corresponds to a position
                    in the overall map
        Parameters: the row and col of the position within the overall map,
                    as ints
        User Input: no
        Prints:     nothing
        Returns:    the chunk (list of str) corresponding to
                    the overall map position
        Modifies:   nothing
        Calls:      standard python
        """
        return self.chunks[row // self.chunk_rows][col // self.chunk_cols]

    def get_chunk_idxs(self, row: int, col: int) -> Tuple[int, int]:
        """
        Purpose:    Get the indices within a chunk for a position
                    in the overall map
        Parameters: the row and col of the position whose position within a
                    chunk is to be determined, as ints
        User Input: no
        Prints:     nothing
        Returns:    (row, col), the row and col within the chunk corresponding
                    to the position passed in, as ints
        Modifies:   nothing
        Calls:      standard python
        """
        return row % self.chunk_rows, col % self.chunk_cols

    def get_entities_in_same_chunk(self, row: int, col: int) -> List[characters.Entity]:
        """
        Purpose:    Return the list of all entities in the chunk corresponding
                    to the position row, col
        Parameters: the row and col of the position whose chunk's entities
                    should be returned, as ints
        User Input: no
        Prints:     nothing
        Returns:    the list of entities in the same chunk as the position
        Modifies:   nothing
        Calls:      standard python
        """
        chunk_i = row // self.chunk_rows
        chunk_j = col // self.chunk_cols
        same_chunk: Callable[[characters.Entity], bool] = lambda entity: (
            (entity.row // self.chunk_rows) == chunk_i
        ) and ((entity.col // self.chunk_cols) == chunk_j)
        entities = [entity for entity in self.entities if same_chunk(entity)]
        return entities

    def pretty_print(self) -> None:
        """
        Purpose:    Prints out the map, overlaying the characters
                    corresponding to game entities
        Parameters: none
        User Input: no
        Prints:     the current chunk with the player and all other entities
                    superimposed over it
        Returns:    none
        Modifies:   nothing
        Calls:      standard python, get_chunk(), get_chunk_idxs(),
                    get_entities_in_same_chunk(), entity's char() function
        """
        print("\033c")
        chunk = self.get_chunk(self.player.row, self.player.col)
        chunk_row, chunk_col = self.get_chunk_idxs(self.player.row, self.player.col)
        # row_modifiers: Dict[int, List[Tuple[int, str]]] = {}
        row_modifiers: Dict[int, Dict[int, str]] = defaultdict(dict)
        for entity in self.get_entities_in_same_chunk(self.player.row, self.player.col):
            # For each entity in the current chunk, place it in a dict keyed on
            # the row and store the column and character
            i, j = self.get_chunk_idxs(entity.row, entity.col)
            if (j not in row_modifiers[i]) or (
                row_modifiers[i][j] != self.player.char()
            ):
                row_modifiers[i][j] = entity.char()
        for idx, line in enumerate(chunk):
            line_list = list(line)
            if idx in row_modifiers:
                # For each entity in the row,
                # replace with the corresponding char
                for col in row_modifiers[idx]:
                    line_list[col] = row_modifiers[idx][col]
            print("".join(reversed(line_list)))
        exposure_str = "Your exposure factor is {:.2f}".format(
            self.player.exposure_factor
        )
        oracle_str = "Direction to The0racle is {}".format(
            self.oracle.get_direction(self.player)
        )
        padding = " " * (self.chunk_cols - len(exposure_str) - len(oracle_str))
        print(exposure_str + padding + oracle_str)

    def byte_dump(self) -> bytearray:
        # cast to mutable bytearrays

        bytes_list = [
            bytearray(row) for row in self.protomap
        ]
        # load position
        for entity in self.entities:
            bytes_list[entity.row][entity.col] = ord(entity.repr_char)
        
        return bytearray(
            self.ByteMap( # flatten
                *[self.Row.from_buffer(row) for row in bytes_list]
            ))
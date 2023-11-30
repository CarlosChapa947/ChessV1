import random
import time
from custom_chess.Classes.chessEngine import Gamestate
from custom_chess.Classes.MoveClass import Move
from multiprocessing import Process, Queue

piece_score = {"K": 0, "Q": 9, "R": 5, "N": 3, "B": 3, "p": 1}
CHECKMATE = 400
STALEMATE = 0
DEPTH = 4
next_move = None
counter = None
transposition_table: dict = {}
KILLER_MOVES = {depth: [None, None] for depth in range(DEPTH + 1)}

knight_scores = [[0.0, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1, 0.0],
                 [0.1, 0.3, 0.5, 0.5, 0.5, 0.5, 0.3, 0.1],
                 [0.2, 0.5, 0.6, 0.65, 0.65, 0.6, 0.5, 0.2],
                 [0.2, 0.55, 0.65, 0.7, 0.7, 0.65, 0.55, 0.2],
                 [0.2, 0.5, 0.65, 0.7, 0.7, 0.65, 0.5, 0.2],
                 [0.2, 0.55, 0.6, 0.65, 0.65, 0.6, 0.55, 0.2],
                 [0.1, 0.3, 0.5, 0.55, 0.55, 0.5, 0.3, 0.1],
                 [0.0, 0.1, 0.2, 0.2, 0.2, 0.2, 0.1, 0.0]]

bishop_scores = [[0.0, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.0],
                 [0.2, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.2],
                 [0.2, 0.4, 0.5, 0.6, 0.6, 0.5, 0.4, 0.2],
                 [0.2, 0.5, 0.5, 0.6, 0.6, 0.5, 0.5, 0.2],
                 [0.2, 0.4, 0.6, 0.6, 0.6, 0.6, 0.4, 0.2],
                 [0.2, 0.6, 0.6, 0.6, 0.6, 0.6, 0.6, 0.2],
                 [0.2, 0.5, 0.4, 0.4, 0.4, 0.4, 0.5, 0.2],
                 [0.0, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.0]]

rook_scores = [[0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25],
               [0.5, 0.75, 0.75, 0.75, 0.75, 0.75, 0.75, 0.5],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.0, 0.25, 0.25, 0.25, 0.25, 0.25, 0.25, 0.0],
               [0.25, 0.25, 0.25, 0.5, 0.5, 0.25, 0.25, 0.25]]

queen_scores = [[0.0, 0.2, 0.2, 0.3, 0.3, 0.2, 0.2, 0.0],
                [0.2, 0.4, 0.4, 0.4, 0.4, 0.4, 0.4, 0.2],
                [0.2, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.2],
                [0.3, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.3],
                [0.4, 0.4, 0.5, 0.5, 0.5, 0.5, 0.4, 0.3],
                [0.2, 0.5, 0.5, 0.5, 0.5, 0.5, 0.4, 0.2],
                [0.2, 0.4, 0.5, 0.4, 0.4, 0.4, 0.4, 0.2],
                [0.0, 0.2, 0.2, 0.3, 0.3, 0.2, 0.2, 0.0]]

pawn_scores = [[0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
               [0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7, 0.7],
               [0.3, 0.3, 0.4, 0.5, 0.5, 0.4, 0.3, 0.3],
               [0.25, 0.25, 0.3, 0.45, 0.45, 0.3, 0.25, 0.25],
               [0.2, 0.2, 0.2, 0.4, 0.4, 0.2, 0.2, 0.2],
               [0.25, 0.15, 0.1, 0.2, 0.2, 0.1, 0.15, 0.25],
               [0.25, 0.3, 0.3, 0.0, 0.0, 0.3, 0.3, 0.25],
               [0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2]]

piece_position_scores = {"wN": knight_scores,
                         "bN": knight_scores[::-1],
                         "wB": bishop_scores,
                         "bB": bishop_scores[::-1],
                         "wQ": queen_scores,
                         "bQ": queen_scores[::-1],
                         "wR": rook_scores,
                         "bR": rook_scores[::-1],
                         "wp": pawn_scores,
                         "bp": pawn_scores[::-1]}


def find_random(valid_moves: list):
    return valid_moves[random.randint(0, len(valid_moves) - 1)]


def find_better_move_greedy(gamestate: Gamestate, validmoves: list[Move]):
    player_multiplier: int = 0
    # maxscore: int = -CHECKMATE
    opponent_minmax: int = CHECKMATE
    best_player_move = None
    random.shuffle(validmoves)
    if gamestate.whiteToMove:
        player_multiplier = 1
    elif not gamestate.whiteToMove:
        player_multiplier = -1
    for player_move in validmoves:
        gamestate.make_move(player_move)
        opponents_moves = gamestate.get_valid_moves_efficient()
        if gamestate.checkmate:
            opponent_max_score = -CHECKMATE
        elif gamestate.stalemate:
            opponent_max_score = STALEMATE
        else:
            opponent_max_score = -CHECKMATE
            for opo_moves in opponents_moves:
                gamestate.make_move(opo_moves)
                if gamestate.checkmate:
                    score = CHECKMATE
                elif gamestate.stalemate:
                    score = STALEMATE
                else:
                    score = -player_multiplier * scoreboard_simple(gamestate.board)
                if score > opponent_max_score:
                    opponent_max_score = score
                    # best_move = player_move
                gamestate.undo_move()
        if opponent_max_score < opponent_minmax:
            opponent_minmax = opponent_max_score
            best_player_move = player_move
        # start with player
        """if gamestate.checkmate:
            maxscore = CHECKMATE
        elif gamestate.stalemate:
            maxscore = STALEMATE
        else:
            score = player_multiplier * scoreboard_simple(gamestate.board)
            if score > maxscore:
                maxscore = score
                best_player_move = player_move
        gamestate.undoMove()"""
        gamestate.undo_move()
    return best_player_move


def find_better_move_recursive_minmax(gamestate: Gamestate, validmoves: list[Move], depth: int, player_turn: bool):
    global next_move
    if depth == 0:
        return scoreboard_simple(gamestate.board)

    if player_turn:
        maxscore = -CHECKMATE
        for move in validmoves:
            gamestate.make_move(move)
            next_valid_moves = gamestate.get_valid_moves_efficient()
            score = find_better_move_recursive_minmax(gamestate, next_valid_moves, depth - 1, False)
            if score > maxscore:
                maxscore = score
                if depth == DEPTH:
                    next_move = move
            gamestate.undo_move()
        return maxscore

    elif not player_turn:
        minscore = CHECKMATE
        for move in validmoves:
            gamestate.make_move(move)
            next_valid_moves = gamestate.get_valid_moves_efficient()
            score = find_better_move_recursive_minmax(gamestate, next_valid_moves, depth - 1, True)
            if score < minscore:
                minscore = score
                if depth == DEPTH:
                    next_move = move
            gamestate.undo_move()
        return minscore


def find_move_negamax(gamestate: Gamestate, validmoves: list, depth: int, turn_multi: int) -> int:
    global next_move
    if depth == 0:
        return turn_multi * scoreboard_normal(gamestate)
    maxscore = -CHECKMATE
    for move in validmoves:
        gamestate.make_move(move)
        next_moves = gamestate.get_valid_moves_efficient()
        score = - find_move_negamax(gamestate, next_moves, depth - 1, -turn_multi)
        if score > maxscore:
            maxscore = score
            if depth == DEPTH:
                next_move = move
        gamestate.undo_move()

    return maxscore


def find_bestmove_negamax(gamestate: Gamestate, validmoves: list[Move]):
    global next_move
    next_move = None
    random.shuffle(validmoves)
    if gamestate.whiteToMove:
        find_move_negamax(gamestate, validmoves, DEPTH, 1)
    elif not gamestate.whiteToMove:
        find_move_negamax(gamestate, validmoves, DEPTH, -1)

    return next_move


def find_bestmove_negamax_aplhabeta_pruned(gamestate: Gamestate, validmoves: list, alpha, beta, depth: int) -> int:
    global next_move, counter, transposition_table, KILLER_MOVES
    #board_key = board_to_key(gamestate.board)
    #R = 3  # Reduction factor
    #null_move_depth = depth - R

    for killer in KILLER_MOVES[depth]:
        if killer in validmoves:
            validmoves.remove(killer)
            validmoves.insert(0, killer)

    #if is_null_move_allowed and depth >= 4 and not gamestate.is_check():
        #gamestate.whiteToMove = not gamestate.whiteToMove  # Make null move
        #evalu = -find_bestmove_negamax_aplhabeta_pruned(gamestate, validmoves, null_move_depth, -beta, -beta + 1,
                                                       # -turn_multi, False)
       # gamestate.whiteToMove = not gamestate.whiteToMove  # Undo null move

        #if evalu >= beta:
           # return beta

    #if transposition_table.get(board_key, None) is not None:
        #entry = transposition_table[board_key]
        #if entry['depth'] >= depth:
            #return entry['evaluation']

    counter += 1
    if depth == 0:
        return scoreboard_normal(gamestate)
    maxscore = -CHECKMATE
    for move in validmoves:
        gamestate.make_move(move)
        next_moves = gamestate.get_valid_moves_efficient()
        score = -find_bestmove_negamax_aplhabeta_pruned(gamestate, next_moves, -beta, -alpha, depth - 1)
        if score > maxscore:
            maxscore = score
            if depth == DEPTH:
                next_move = move
        gamestate.undo_move()
        if maxscore > alpha:
            alpha = maxscore
        if alpha >= beta:
            if move not in KILLER_MOVES[depth]:
                KILLER_MOVES[depth].pop()
                KILLER_MOVES[depth].insert(0, move)
            break

    #transposition_table[board_key] = {'depth': depth, 'evaluation': maxscore, 'best_move': next_move}
    return maxscore


def find_move_nega_alphabeta(gamestate: Gamestate, validmoves: list[Move], decision_queue: Queue):
    global next_move, counter
    counter = 0
    timer = time.time()
    random.shuffle(validmoves)
    next_move = None

    for depth in range(1, DEPTH + 1):
        if gamestate.whiteToMove:
            find_bestmove_negamax_aplhabeta_pruned(gamestate, validmoves, alpha=-CHECKMATE, beta=CHECKMATE, depth=depth)
        elif not gamestate.whiteToMove:
            find_bestmove_negamax_aplhabeta_pruned(gamestate, validmoves, alpha=-CHECKMATE, beta=CHECKMATE, depth=depth)
        if time.time() - timer > 30:
            break
    decision_queue.put(next_move)
    print(decision_queue)
    # return next_move


def find_move_minmax(gamestate: Gamestate, validmoves: list[Move]):
    global next_move
    next_move = None
    find_better_move_recursive_minmax(gamestate, validmoves, DEPTH, gamestate.whiteToMove)


def scoreboard_simple(board: list[str]):
    score = 0
    for row in board:
        for square in row:
            if square[0] == "w":
                score += piece_score[square[1]]
            elif square[0] == "b":
                score -= piece_score[square[1]]

    return score


def scoreboard_normal(gamestate: Gamestate):
    if gamestate.checkmate:
        if gamestate.whiteToMove:
            return -CHECKMATE
        elif not gamestate.whiteToMove:
            return CHECKMATE
    elif gamestate.stalemate:
        return 0

    score = 0
    for row in range(len(gamestate.board)):
        for col in range(len(gamestate.board[row])):
            piece = gamestate.board[row][col]
            if piece != "__":
                piece_position_score = 0
                if piece[1] != "K":
                    piece_position_score = piece_position_scores[piece][row][col]
                if piece[0] == "w":
                    score += piece_score[piece[1]] + piece_position_score
                if piece[0] == "b":
                    score -= piece_score[piece[1]] + piece_position_score

    if gamestate.is_check() and gamestate.whiteToMove:
        score += 2
    elif gamestate.is_check() and not gamestate.whiteToMove:
        score -= 2

    if gamestate.whiteToMove:
        return score
    else:
        return -score


    """
    score = 0
    for row in range(len(gamestate.board)):
        for col in range(len(gamestate.board[row])):
            piece = gamestate.board[row][col]
            if piece != "__":
                piece_position_score = 0
                if piece[1] != "K":
                    piece_position_score = piece_position_scores[piece][row][col]
                if piece[0] == "w":
                    score += piece_score[piece[1]] + piece_position_score
                if piece[0] == "b":
                    score -= piece_score[piece[1]] + piece_position_score

    return score
"""


def board_to_key(board) -> tuple:
    # Flatten the board and convert it to a tuple for immutability
    return tuple(item for row in board for item in row)

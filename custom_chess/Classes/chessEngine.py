import typing
import copy
import numpy as np
from multiprocessing import process, Queue
from numpy.typing import NDArray
from custom_chess.Classes.MoveClass import Move
from custom_chess.Classes.CastleRights import CastleRights


class Gamestate:

    def __init__(self):
        self.board = np.array(
            [["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
             ["bp", "bp", "bp", "bp", "bp", "bp", "bp", "bp"],
             ["__", "__", "__", "__", "__", "__", "__", "__"],
             ["__", "__", "__", "__", "__", "__", "__", "__"],
             ["__", "__", "__", "__", "__", "__", "__", "__"],
             ["__", "__", "__", "__", "__", "__", "__", "__"],
             ["wp", "wp", "wp", "wp", "wp", "wp", "wp", "wp"],
             ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]])
        self.moveFunctions = {"p": self.get_pawn_moves, "R": self.get_rook_moves, "N": self.get_knight_moves,
                              "B": self.get_bishop_moves, "Q": self.get_queen_moves, "K": self.get_king_moves}
        self.whiteToMove = True
        self.moveLog = []
        self.blackKingLocation = (0, 4)
        self.whiteKingLocation = (7, 4)
        self.checkmate = False
        self.stalemate = False
        self.inCheckAtt = False
        self.pins = []
        self.checks = []
        self.currentCastlingRight = CastleRights(True, True, True, True)
        self.enpassantPossible = ()
        self.enpassant_possible_log = [self.enpassantPossible]
        self.castleRightsLog = [
            CastleRights(self.currentCastlingRight.white_king_castle, self.currentCastlingRight.black_king_castle,
                         self.currentCastlingRight.white_queen_castle, self.currentCastlingRight.black_queen_castle)]

    def make_move(self, move: Move) -> None:
        self.board[move.startRow][move.startCol] = "__"
        self.board[move.endRow][move.endCol] = move.pieceMoved
        self.moveLog.append(move)
        if move.pieceMoved == "wK":
            self.whiteKingLocation = (move.endRow, move.endCol)
        elif move.pieceMoved == "bK":
            self.blackKingLocation = (move.endRow, move.endCol)
        self.whiteToMove = not self.whiteToMove

        if move.isPawnPromotion:
            # promotePiece = input("Promueve a Q, R, B o N")
            self.board[move.endRow][move.endCol] = move.pieceMoved[0] + "Q"

        if move.isenpassantMove:
            self.board[move.startRow][move.endCol] = "__"

        if move.pieceMoved[1] == "p" and abs(move.startRow - move.endRow) == 2:
            self.enpassantPossible = ((move.startRow + move.endRow) // 2, move.endCol)
        else:
            self.enpassantPossible = ()

        if move.isCastleMove:
            if move.endCol - move.startCol == 2:
                self.board[move.endRow][move.endCol - 1] = self.board[move.endRow][move.endCol + 1]
                self.board[move.endRow][move.endCol + 1] = "__"
            else:
                self.board[move.endRow][move.endCol + 1] = self.board[move.endRow][move.endCol - 2]
                self.board[move.endRow][move.endCol - 2] = "__"

        self.enpassant_possible_log.append(self.enpassantPossible)
        self.update_castle_rights(move)
        self.castleRightsLog.append(
            CastleRights(self.currentCastlingRight.white_king_castle, self.currentCastlingRight.black_king_castle,
                         self.currentCastlingRight.white_queen_castle, self.currentCastlingRight.black_queen_castle))

    def undo_move(self) -> None:
        if len(self.moveLog) != 0:
            move: Move = self.moveLog.pop()
            self.board[move.startRow][move.startCol] = move.pieceMoved
            self.board[move.endRow][move.endCol] = move.pieceCaptured
            self.whiteToMove = not self.whiteToMove

            if move.pieceMoved == "wK":
                self.whiteKingLocation = (move.startRow, move.startCol)
            elif move.pieceMoved == "bK":
                self.blackKingLocation = (move.startRow, move.startCol)

            if move.isenpassantMove:
                self.board[move.endRow][move.endCol] = "__"
                self.board[move.startRow][move.endCol] = move.pieceCaptured

            self.enpassant_possible_log.pop()
            self.enpassantPossible = self.enpassant_possible_log[-1]

            self.castleRightsLog.pop()
            self.currentCastlingRight = copy.deepcopy(self.castleRightsLog[-1])
            if move.isCastleMove:
                if move.endCol - move.startCol == 2:
                    self.board[move.endRow][move.endCol + 1] = self.board[move.endRow][move.endCol - 1]
                    self.board[move.endRow][move.endCol - 1] = "__"
                else:
                    self.board[move.endRow][move.endCol - 2] = self.board[move.endRow][move.endCol + 1]
                    self.board[move.endRow][move.endCol + 1] = "__"
            self.checkmate = False
            self.stalemate = False

    def get_valid_moves_naive(self) -> list[Move]:
        moves = self.get_all_possible_moves()
        for i in range(len(moves) - 1, -1, -1):
            self.make_move(moves[i])
            self.whiteToMove = not self.whiteToMove
            if self.is_check():
                moves.remove(moves[i])
            self.whiteToMove = not self.whiteToMove
            self.undo_move()

        if len(moves) == 0:
            if self.is_check():
                self.checkmate = True
            else:
                self.stalemate = True
        else:
            if self.is_check():
                self.checkmate = False
            else:
                self.stalemate = False
        return moves

    def get_valid_moves_efficient(self) -> list[Move]:
        moves: list[Move] = []
        temp_castle_right = CastleRights(self.currentCastlingRight.white_king_castle,
                                       self.currentCastlingRight.black_king_castle,
                                       self.currentCastlingRight.white_queen_castle,
                                       self.currentCastlingRight.black_queen_castle)
        self.inCheckAtt, self.pins, self.checks = self.check_pins_and_checks()
        if self.whiteToMove:
            king_row = self.whiteKingLocation[0]
            king_col = self.whiteKingLocation[1]
        else:
            king_row = self.blackKingLocation[0]
            king_col = self.blackKingLocation[1]
        if self.inCheckAtt:
            if len(self.checks) == 1:
                moves = self.get_all_possible_moves()
                check = self.checks[0]
                check_row = check[0]
                check_col = check[1]
                piece_checking = self.board[check_row][check_col]
                print("check ", piece_checking)
                valid_squares = []
                if piece_checking[1] == "K":
                    valid_squares = [(check_row, check_col)]
                else:
                    for i in range(1, 8):
                        valid_square = (king_row + check[2] * i, king_col + check[3] * i)
                        valid_squares.append(valid_square)
                        if valid_square[0] == check_row and valid_square[1] == check_col:
                            break
                for i in range(len(moves) - 1, -1, -1):
                    if moves[i].pieceMoved[1] != "K":
                        if not (moves[i].endRow, moves[i].endCol) in valid_squares:
                            moves.remove(moves[i])
            else:
                self.get_king_moves(king_row, king_col, moves)
        else:
            moves = self.get_all_possible_moves()
            if self.whiteToMove:
                self.get_castle_moves(self.whiteKingLocation[0], self.whiteKingLocation[1], moves)
            else:
                self.get_castle_moves(self.blackKingLocation[0], self.blackKingLocation[1], moves)

        if len(moves) == 0:
            if self.is_check():
                self.checkmate = True
            else:
                self.stalemate = True
        else:
            self.checkmate = False
            self.stalemate = False

        self.current_castling_rights = temp_castle_right

        return moves

    def check_pins_and_checks(self):
        pins = []
        checks = []
        in_check = False
        if self.whiteToMove:
            enemy_color = "b"
            ally_color = "w"
            start_row = self.whiteKingLocation[0]
            start_col = self.whiteKingLocation[1]
        else:
            enemy_color = "w"
            ally_color = "b"
            start_row = self.blackKingLocation[0]
            start_col = self.blackKingLocation[1]
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
        for i in range(len(directions)):
            direction = directions[i]
            possible_pin = ()
            for j in range(1, 8):
                end_row = start_row + direction[0] * j
                end_col = start_col + direction[1] * j
                if 0 <= end_row < 8 and 0 <= end_col < 8:
                    end_piece = self.board[end_row][end_col]
                    if end_piece[0] == ally_color and end_piece[1] != "K":
                        if possible_pin == ():
                            possible_pin = (end_row, end_col, direction[0], direction[1])
                        else:
                            break
                    elif end_piece[0] == enemy_color:
                        type_piece = end_piece[1]
                        if (0 <= i <= 3 and type_piece == "R") or \
                                (4 <= i <= 7 and type_piece == "B") or \
                                (j == 1 and type_piece == "p" and ((enemy_color == "w" and 6 <= i <= 7) or (
                                        enemy_color == "b" and 3 == i or i == 5))) or \
                                (type_piece == "Q") or (j == 1 and type_piece == "K"):
                            if possible_pin == ():
                                in_check = True
                                checks.append((end_row, end_col, direction[0], direction[1]))
                                break
                            else:
                                pins.append(possible_pin)
                                break
                        else:
                            break
                else:
                    break
        knight_moves = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
        for move in knight_moves:
            end_row = start_row + move[0]
            end_col = start_col + move[1]
            if 0 <= end_row < 8 and 0 <= end_col < 8:
                end_piece = self.board[end_row][end_col]
                if end_piece[0] == enemy_color and end_piece[1] == "N":
                    in_check = True
                    checks.append((end_row, end_col, move[0], move[1]))
        return in_check, pins, checks

    def is_check(self):
        if self.whiteToMove:
            return self.square_threatened(self.whiteKingLocation[0], self.whiteKingLocation[1])
        else:
            return self.square_threatened(self.blackKingLocation[0], self.blackKingLocation[1])

    def square_threatened(self, row: int, col: int):
        self.whiteToMove = not self.whiteToMove
        opponent_moves = self.get_all_possible_moves()
        self.whiteToMove = not self.whiteToMove
        for move in opponent_moves:
            if move.endRow == row and move.endCol == col:
                return True
        return False

    def get_all_possible_moves(self):
        moves = []
        for i in range(len(self.board)):
            for j in range(len(self.board[i])):
                turn = self.board[i][j][0]
                if (turn == "w" and self.whiteToMove) or (turn == "b" and not self.whiteToMove):
                    piece = self.board[i][j][1]
                    self.moveFunctions[piece](i, j, moves)
        return moves

    def get_pawn_moves(self, row: int, col: int, moves: list[Move]):
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break
        if self.whiteToMove:
            if self.board[row - 1][col] == "__":
                if not piece_pinned or pin_direction == (-1, 0):
                    moves.append(Move((row, col), (row - 1, col), self.board))
                    if row == 6 and self.board[row - 2][col] == "__":
                        moves.append(Move((row, col), (row - 2, col), self.board))
            if col - 1 >= 0:
                if self.board[row - 1][col - 1][0] == "b":
                    if not piece_pinned or pin_direction == (-1, 0):
                        moves.append(Move((row, col), (row - 1, col - 1), self.board))
                if (row - 1, col - 1) == self.enpassantPossible:
                    if not piece_pinned or pin_direction == (-1, 0):
                        moves.append(Move((row, col), (row - 1, col - 1), self.board, enpassant_move=True))
            if col + 1 <= 7:
                if self.board[row - 1][col + 1][0] == "b":
                    if not piece_pinned or pin_direction == (-1, 0):
                        moves.append(Move((row, col), (row - 1, col + 1), self.board))
                if (row - 1, col + 1) == self.enpassantPossible:
                    if not piece_pinned or pin_direction == (-1, 0):
                        moves.append(Move((row, col), (row - 1, col + 1), self.board, enpassant_move=True))
        else:
            if self.board[row + 1][col] == "__":
                if not piece_pinned or pin_direction == (1, 0):
                    moves.append(Move((row, col), (row + 1, col), self.board))
                    if row == 1 and self.board[row + 2][col] == "__":
                        moves.append(Move((row, col), (row + 2, col), self.board))
            if col - 1 >= 0:
                if self.board[row + 1][col - 1][0] == "w":
                    if not piece_pinned or pin_direction == (1, 0):
                        moves.append(Move((row, col), (row + 1, col - 1), self.board))
                if (row + 1, col - 1) == self.enpassantPossible:
                    if not piece_pinned or pin_direction == (-1, 0):
                        moves.append(Move((row, col), (row + 1, col - 1), self.board, enpassant_move=True))
            if col + 1 <= 7:
                if self.board[row + 1][col + 1][0] == "w":
                    if not piece_pinned or pin_direction == (1, 0):
                        moves.append(Move((row, col), (row + 1, col + 1), self.board))
                if (row + 1, col + 1) == self.enpassantPossible:
                    if not piece_pinned or pin_direction == (-1, 0):
                        moves.append(Move((row, col), (row + 1, col + 1), self.board, enpassant_move=True))

    def get_rook_moves(self, row: int, col: int, moves: list[Move]) -> None:
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                if self.board[row][col][1] != "Q":
                    self.pins.remove(self.pins[i])
                break
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1))
        if self.whiteToMove:
            enemy_color = "b"
        else:
            enemy_color = "w"
        for direction in directions:
            for k in range(1, 8):
                end_row = row + direction[0] * k
                end_col = col + direction[1] * k
                if 0 <= end_row < 8 and 0 <= end_col < 8:
                    if not piece_pinned or pin_direction == direction or pin_direction == (-direction[0], -direction[1]):
                        end_piece = self.board[end_row][end_col]
                        if end_piece == "__":
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                        elif end_piece[0] == enemy_color:
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                            break
                        else:
                            break
                    else:
                        break

    def get_knight_moves(self, row: int, col: int, moves: list[Move]) -> None:
        piece_pinned = False
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                self.pins.remove(self.pins[i])
                break
        possibly_moves = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
        if self.whiteToMove:
            enemy_color = "b"
        else:
            enemy_color = "w"
        for m in possibly_moves:
            for k in range(1, 8):
                end_row = row + m[0]
                end_col = col + m[1]
                if 0 <= end_row < 8 and 0 <= end_col < 8:
                    if not piece_pinned:
                        endPiece = self.board[end_row][end_col]
                        if endPiece == "__":
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                        elif endPiece[0] == enemy_color:
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                            break
                        else:
                            break
                    else:
                        break

    def get_bishop_moves(self, row: int, col: int, moves: list[Move]) -> None:
        piece_pinned = False
        pin_direction = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piece_pinned = True
                pin_direction = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break
        directions = ((-1, -1), (-1, 1), (1, -1), (1, 1))
        if self.whiteToMove:
            enemy_color = "b"
        else:
            enemy_color = "w"
        for directory in directions:
            for k in range(1, 8):
                end_row = row + directory[0] * k
                end_col = col + directory[1] * k
                if 0 <= end_row < 8 and 0 <= end_col < 8:
                    if not piece_pinned or pin_direction == directory or pin_direction == (-directory[0], -directory[1]):
                        end_piece = self.board[end_row][end_col]
                        if end_piece == "__":
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                        elif end_piece[0] == enemy_color:
                            moves.append(Move((row, col), (end_row, end_col), self.board))
                            break
                        else:
                            break
                    else:
                        break

    def get_queen_moves(self, row: int, col: int, moves: list[Move]) -> None:
        self.get_bishop_moves(row, col, moves)
        self.get_rook_moves(row, col, moves)

    def get_king_moves(self, row, col, moves) -> None:
        # possiblyMoves = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
        row_moves = (-1, -1, -1, 0, 0, 1, 1, 1)
        col_moves = (-1, 0, 1, -1, 1, -1, 0, 1)
        if self.whiteToMove:
            ally = "w"
        else:
            ally = "b"
        for k in range(8):
            # end_row = row + possiblyMoves[k][0]
            # end_col = col + possiblyMoves[k][1]
            end_row = row + row_moves[k]
            end_col = col + col_moves[k]
            if 0 <= end_row < 8 and 0 <= end_col < 8:
                end_piece = self.board[end_row][end_col]
                if end_piece[0] != ally:
                    if ally == "w":
                        self.whiteKingLocation = (end_row, end_col)
                    else:
                        self.blackKingLocation = (end_row, end_col)
                    in_check, pins, checks = self.check_pins_and_checks()
                    if not in_check:
                        moves.append(Move((row, col), (end_row, end_col), self.board))
                    if ally == "w":
                        self.whiteKingLocation = (row, col)
                    else:
                        self.blackKingLocation = (row, col)

    def update_castle_rights(self, move: Move) -> None:
        if move.pieceMoved == "wK":
            self.currentCastlingRight.white_king_castle = False
            self.currentCastlingRight.white_queen_castle = False
        elif move.pieceMoved == "bK":
            self.currentCastlingRight.black_king_castle = False
            self.currentCastlingRight.black_queen_castle = False
        elif move.pieceMoved == "wR" or move.pieceCaptured == "wR":
            if move.startRow == 7:
                if move.startCol == 0:
                    self.currentCastlingRight.white_queen_castle = False
                elif move.startCol == 7:
                    self.currentCastlingRight.white_king_castle = False
        elif move.pieceMoved == "bR" or move.pieceCaptured == "bR":
            if move.startRow == 7:
                if move.startCol == 0:
                    self.currentCastlingRight.black_queen_castle = False
                elif move.startCol == 7:
                    self.currentCastlingRight.black_King_castle = False

    def get_castle_moves(self, row: int, col: int, moves: list[Move]) -> None:
        if self.square_threatened(row, col):
            return
        if (self.whiteToMove and self.currentCastlingRight.white_king_castle) or (
                not self.whiteToMove and self.currentCastlingRight.black_king_castle):
            self.get_king_side_castle_moves(row, col, moves)
        if (self.whiteToMove and self.currentCastlingRight.white_queen_castle) or (
                not self.whiteToMove and self.currentCastlingRight.black_queen_castle):
            self.get_queen_side_castle_moves(row, col, moves)

    def get_king_side_castle_moves(self, row: int, col: int, moves: list[Move]) -> None:
        if self.board[row][col + 1] == '__' and self.board[row][col + 2] == '__':
            if not self.square_threatened(row, col + 1) and not self.square_threatened(row, col + 2):
                moves.append(Move((row, col), (row, col + 2), self.board, is_castle_move=True))

    def get_queen_side_castle_moves(self, row: int, col: int, moves: list[Move]) -> None:
        if self.board[row][col - 1] == '__' and self.board[row][col - 2] == '__' and self.board[row][col - 3] == '__':
            if not self.square_threatened(row, col - 1) and not self.square_threatened(row, col - 2):
                moves.append(Move((row, col), (row, col - 2), self.board, is_castle_move=True))

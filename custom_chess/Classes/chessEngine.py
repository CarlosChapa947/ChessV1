import typing
import copy
import numpy as np
from multiprocessing import process, Queue
from numpy.typing import NDArray
from custom_chess.Classes.MoveClass import Move
from custom_chess.Classes.CastleRights import Castle_Rights


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
        self.moveFunctions = {"p": self.getPawnMoves, "R": self.getRookMoves, "N": self.getKnightMoves,
                              "B": self.getBishopMoves, "Q": self.get_queen_moves, "K": self.get_king_moves}
        self.whiteToMove = True
        self.moveLog = []
        self.blackKingLocation = (0, 4)
        self.whiteKingLocation = (7, 4)
        self.checkmate = False
        self.stalemate = False
        self.inCheckAtt = False
        self.pins = []
        self.checks = []
        self.currentCastlingRight = Castle_Rights(True, True, True, True)
        self.enpassantPossible = ()
        self.enpassant_possible_log = [self.enpassantPossible]
        self.castleRightsLog = [
            Castle_Rights(self.currentCastlingRight.white_king_castle, self.currentCastlingRight.black_king_castle,
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
            Castle_Rights(self.currentCastlingRight.white_king_castle, self.currentCastlingRight.black_king_castle,
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
        moves = self.getAllPosibleMoves()
        for i in range(len(moves) - 1, -1, -1):
            self.make_move(moves[i])
            self.whiteToMove = not self.whiteToMove
            if self.inCheck():
                moves.remove(moves[i])
            self.whiteToMove = not self.whiteToMove
            self.undo_move()

        if len(moves) == 0:
            if self.inCheck():
                self.checkmate = True
            else:
                self.stalemate = True
        else:
            if self.inCheck():
                self.checkmate = False
            else:
                self.stalemate = False
        return moves

    def get_valid_moves_efficient(self) -> list[Move]:
        moves: list[Move] = []
        tempCastleRight = Castle_Rights(self.currentCastlingRight.white_king_castle,
                                        self.currentCastlingRight.black_king_castle,
                                        self.currentCastlingRight.white_queen_castle,
                                        self.currentCastlingRight.black_queen_castle)
        self.inCheckAtt, self.pins, self.checks = self.checkForPinsAndChecks()
        if self.whiteToMove:
            kingRow = self.whiteKingLocation[0]
            kingCol = self.whiteKingLocation[1]
        else:
            kingRow = self.blackKingLocation[0]
            kingCol = self.blackKingLocation[1]
        if self.inCheckAtt:
            if len(self.checks) == 1:
                moves = self.getAllPosibleMoves()
                check = self.checks[0]
                checkRow = check[0]
                checkCol = check[1]
                pieceChecking = self.board[checkRow][checkCol]
                print("check ", pieceChecking)
                validSquares = []
                if pieceChecking[1] == "K":
                    validSquares = [(checkRow, checkCol)]
                else:
                    for i in range(1, 8):
                        validSquare = (kingRow + check[2] * i, kingCol + check[3] * i)
                        validSquares.append(validSquare)
                        if validSquare[0] == checkRow and validSquare[1] == checkCol:
                            break
                for i in range(len(moves) - 1, -1, -1):
                    if moves[i].pieceMoved[1] != "K":
                        if not (moves[i].endRow, moves[i].endCol) in validSquares:
                            moves.remove(moves[i])
            else:
                self.get_king_moves(kingRow, kingCol, moves)
        else:
            moves = self.getAllPosibleMoves()
            if self.whiteToMove:
                self.get_castle_moves(self.whiteKingLocation[0], self.whiteKingLocation[1], moves)
            else:
                self.get_castle_moves(self.blackKingLocation[0], self.blackKingLocation[1], moves)

        if len(moves) == 0:
            if self.inCheck():
                self.checkmate = True
            else:
                self.stalemate = True
        else:
            self.checkmate = False
            self.stalemate = False

        self.current_castling_rights = tempCastleRight

        return moves

    def checkForPinsAndChecks(self):
        pins = []
        checks = []
        inCheck = False
        if self.whiteToMove:
            enemyColor = "b"
            allyColor = "w"
            startRow = self.whiteKingLocation[0]
            startCol = self.whiteKingLocation[1]
        else:
            enemyColor = "w"
            allyColor = "b"
            startRow = self.blackKingLocation[0]
            startCol = self.blackKingLocation[1]
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1))
        for i in range(len(directions)):
            dir = directions[i]
            possiblePin = ()
            for j in range(1, 8):
                endRow = startRow + dir[0] * j
                endCol = startCol + dir[1] * j
                if 0 <= endRow < 8 and 0 <= endCol < 8:
                    endPiece = self.board[endRow][endCol]
                    if endPiece[0] == allyColor and endPiece[1] != "K":
                        if possiblePin == ():
                            possiblePin = (endRow, endCol, dir[0], dir[1])
                        else:
                            break
                    elif endPiece[0] == enemyColor:
                        typePiece = endPiece[1]
                        if (0 <= i <= 3 and typePiece == "R") or \
                                (4 <= i <= 7 and typePiece == "B") or \
                                (j == 1 and typePiece == "p" and ((enemyColor == "w" and 6 <= i <= 7) or (
                                        enemyColor == "b" and 3 == i or i == 5))) or \
                                (typePiece == "Q") or (j == 1 and typePiece == "K"):
                            if possiblePin == ():
                                inCheck = True
                                checks.append((endRow, endCol, dir[0], dir[1]))
                                break
                            else:
                                pins.append(possiblePin)
                                break
                        else:
                            break
                else:
                    break
        knightMoves = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
        for move in knightMoves:
            endRow = startRow + move[0]
            endCol = startCol + move[1]
            if 0 <= endRow < 8 and 0 <= endCol < 8:
                endPiece = self.board[endRow][endCol]
                if endPiece[0] == enemyColor and endPiece[1] == "N":
                    inCheck = True
                    checks.append((endRow, endCol, move[0], move[1]))
        return inCheck, pins, checks

    def inCheck(self):
        if self.whiteToMove:
            return self.squareThreatened(self.whiteKingLocation[0], self.whiteKingLocation[1])
        else:
            return self.squareThreatened(self.blackKingLocation[0], self.blackKingLocation[1])

    def squareThreatened(self, row: int, col: int):
        self.whiteToMove = not self.whiteToMove
        opponentMoves = self.getAllPosibleMoves()
        self.whiteToMove = not self.whiteToMove
        for move in opponentMoves:
            if move.endRow == row and move.endCol == col:
                return True
        return False

    def getAllPosibleMoves(self):
        moves = []
        for i in range(len(self.board)):
            for j in range(len(self.board[i])):
                turn = self.board[i][j][0]
                if (turn == "w" and self.whiteToMove) or (turn == "b" and not self.whiteToMove):
                    piece = self.board[i][j][1]
                    self.moveFunctions[piece](i, j, moves)
        return moves

    def getPawnMoves(self, row: int, col: int, moves: list[Move]):
        piecePinned = False
        pinDirection = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piecePinned = True
                pinDirection = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break
        if self.whiteToMove:
            if self.board[row - 1][col] == "__":
                if not piecePinned or pinDirection == (-1, 0):
                    moves.append(Move((row, col), (row - 1, col), self.board))
                    if row == 6 and self.board[row - 2][col] == "__":
                        moves.append(Move((row, col), (row - 2, col), self.board))
            if col - 1 >= 0:
                if self.board[row - 1][col - 1][0] == "b":
                    if not piecePinned or pinDirection == (-1, 0):
                        moves.append(Move((row, col), (row - 1, col - 1), self.board))
                if (row - 1, col - 1) == self.enpassantPossible:
                    if not piecePinned or pinDirection == (-1, 0):
                        moves.append(Move((row, col), (row - 1, col - 1), self.board, enpassantMove=True))
            if col + 1 <= 7:
                if self.board[row - 1][col + 1][0] == "b":
                    if not piecePinned or pinDirection == (-1, 0):
                        moves.append(Move((row, col), (row - 1, col + 1), self.board))
                if (row - 1, col + 1) == self.enpassantPossible:
                    if not piecePinned or pinDirection == (-1, 0):
                        moves.append(Move((row, col), (row - 1, col + 1), self.board, enpassantMove=True))
        else:
            if self.board[row + 1][col] == "__":
                if not piecePinned or pinDirection == (1, 0):
                    moves.append(Move((row, col), (row + 1, col), self.board))
                    if row == 1 and self.board[row + 2][col] == "__":
                        moves.append(Move((row, col), (row + 2, col), self.board))
            if col - 1 >= 0:
                if self.board[row + 1][col - 1][0] == "w":
                    if not piecePinned or pinDirection == (1, 0):
                        moves.append(Move((row, col), (row + 1, col - 1), self.board))
                if (row + 1, col - 1) == self.enpassantPossible:
                    if not piecePinned or pinDirection == (-1, 0):
                        moves.append(Move((row, col), (row + 1, col - 1), self.board, enpassantMove=True))
            if col + 1 <= 7:
                if self.board[row + 1][col + 1][0] == "w":
                    if not piecePinned or pinDirection == (1, 0):
                        moves.append(Move((row, col), (row + 1, col + 1), self.board))
                if (row + 1, col + 1) == self.enpassantPossible:
                    if not piecePinned or pinDirection == (-1, 0):
                        moves.append(Move((row, col), (row + 1, col + 1), self.board, enpassantMove=True))

    def getRookMoves(self, row: int, col: int, moves: list[Move]) -> None:
        piecePinned = False
        pinDirection = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piecePinned = True
                pinDirection = (self.pins[i][2], self.pins[i][3])
                if self.board[row][col][1] != "Q":
                    self.pins.remove(self.pins[i])
                break
        directions = ((-1, 0), (0, -1), (1, 0), (0, 1))
        if self.whiteToMove:
            enemyColor = "b"
        else:
            enemyColor = "w"
        for dir in directions:
            for k in range(1, 8):
                endRow = row + dir[0] * k
                endCol = col + dir[1] * k
                if 0 <= endRow < 8 and 0 <= endCol < 8:
                    if not piecePinned or pinDirection == dir or pinDirection == (-dir[0], -dir[1]):
                        endPiece = self.board[endRow][endCol]
                        if endPiece == "__":
                            moves.append(Move((row, col), (endRow, endCol), self.board))
                        elif endPiece[0] == enemyColor:
                            moves.append(Move((row, col), (endRow, endCol), self.board))
                            break
                        else:
                            break
                    else:
                        break

    def getKnightMoves(self, row: int, col: int, moves: list[Move]) -> None:
        piecePinned = False
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piecePinned = True
                self.pins.remove(self.pins[i])
                break
        possiblyMoves = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
        if self.whiteToMove:
            enemyColor = "b"
        else:
            enemyColor = "w"
        for m in possiblyMoves:
            for k in range(1, 8):
                endRow = row + m[0]
                endCol = col + m[1]
                if 0 <= endRow < 8 and 0 <= endCol < 8:
                    if not piecePinned:
                        endPiece = self.board[endRow][endCol]
                        if endPiece == "__":
                            moves.append(Move((row, col), (endRow, endCol), self.board))
                        elif endPiece[0] == enemyColor:
                            moves.append(Move((row, col), (endRow, endCol), self.board))
                            break
                        else:
                            break
                    else:
                        break

    def getBishopMoves(self, row: int, col: int, moves: list[Move]) -> None:
        piecePinned = False
        pinDirection = ()
        for i in range(len(self.pins) - 1, -1, -1):
            if self.pins[i][0] == row and self.pins[i][1] == col:
                piecePinned = True
                pinDirection = (self.pins[i][2], self.pins[i][3])
                self.pins.remove(self.pins[i])
                break
        directions = ((-1, -1), (-1, 1), (1, -1), (1, 1))
        if self.whiteToMove:
            enemyColor = "b"
        else:
            enemyColor = "w"
        for directory in directions:
            for k in range(1, 8):
                endRow = row + directory[0] * k
                endCol = col + directory[1] * k
                if 0 <= endRow < 8 and 0 <= endCol < 8:
                    if not piecePinned or pinDirection == directory or pinDirection == (-directory[0], -directory[1]):
                        endPiece = self.board[endRow][endCol]
                        if endPiece == "__":
                            moves.append(Move((row, col), (endRow, endCol), self.board))
                        elif endPiece[0] == enemyColor:
                            moves.append(Move((row, col), (endRow, endCol), self.board))
                            break
                        else:
                            break
                    else:
                        break

    def get_queen_moves(self, row: int, col: int, moves: list[Move]) -> None:
        self.getBishopMoves(row, col, moves)
        self.getRookMoves(row, col, moves)

    def get_king_moves(self, row, col, moves) -> None:
        # possiblyMoves = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
        rowMoves = (-1, -1, -1, 0, 0, 1, 1, 1)
        colMoves = (-1, 0, 1, -1, 1, -1, 0, 1)
        if self.whiteToMove:
            ally = "w"
        else:
            ally = "b"
        for k in range(8):
            # endRow = row + possiblyMoves[k][0]
            # endCol = col + possiblyMoves[k][1]
            endRow = row + rowMoves[k]
            endCol = col + colMoves[k]
            if 0 <= endRow < 8 and 0 <= endCol < 8:
                endPiece = self.board[endRow][endCol]
                if endPiece[0] != ally:
                    if ally == "w":
                        self.whiteKingLocation = (endRow, endCol)
                    else:
                        self.blackKingLocation = (endRow, endCol)
                    inCheck, pins, checks = self.checkForPinsAndChecks()
                    if not inCheck:
                        moves.append(Move((row, col), (endRow, endCol), self.board))
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
        if self.squareThreatened(row, col):
            return
        if (self.whiteToMove and self.currentCastlingRight.white_king_castle) or (
                not self.whiteToMove and self.currentCastlingRight.black_king_castle):
            self.get_king_side_castle_moves(row, col, moves)
        if (self.whiteToMove and self.currentCastlingRight.white_queen_castle) or (
                not self.whiteToMove and self.currentCastlingRight.black_queen_castle):
            self.get_queen_side_castle_moves(row, col, moves)

    def get_king_side_castle_moves(self, row: int, col: int, moves: list[Move]) -> None:
        if self.board[row][col + 1] == '__' and self.board[row][col + 2] == '__':
            if not self.squareThreatened(row, col + 1) and not self.squareThreatened(row, col + 2):
                moves.append(Move((row, col), (row, col + 2), self.board, isCastleMove=True))

    def get_queen_side_castle_moves(self, row: int, col: int, moves: list[Move]) -> None:
        if self.board[row][col - 1] == '__' and self.board[row][col - 2] == '__' and self.board[row][col - 3] == '__':
            if not self.squareThreatened(row, col - 1) and not self.squareThreatened(row, col - 2):
                moves.append(Move((row, col), (row, col - 2), self.board, isCastleMove=True))

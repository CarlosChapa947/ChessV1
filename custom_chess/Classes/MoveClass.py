import numpy as np
from numpy.typing import NDArray
import uuid


class Move:

    ranksToRows = {"1": 7, "2": 6, "3": 5, "4": 4, "5": 3, "6": 2, "7": 1, "8": 0}
    rowsToRanks = {v: k for k, v in ranksToRows.items()}
    filesToCols = {"a": 0, "b": 1, "c": 2, "d": 3, "e": 4, "f": 5, "g": 6, "h": 7}
    colsToFiles = {v: k for k, v in filesToCols.items()}

    def __init__(self, startCord, endCord, board, enpassantMove=False, isCastleMove=False):
        self.startRow = startCord[0]
        self.startCol = startCord[1]
        self.endRow = endCord[0]
        self.endCol = endCord[1]
        self.pieceMoved = board[self.startRow][self.startCol]
        self.pieceCaptured = board[self.endRow][self.endCol]
        self.moveID = self.startRow * 1000 + self.startCol * 100 + self.endRow * 10 + self.endCol
        self.isPawnPromotion = False
        self.isCastleMove = isCastleMove
        self.promotionChoice = "Q"
        self.isenpassantMove = enpassantMove
        if self.pieceMoved == "wp" and self.endRow == 0:
            self.isPawnPromotion = True
        elif self.pieceMoved == "bp" and self.endRow == 7:
            self.isPawnPromotion = True

        if enpassantMove:
            self.pieceCaptured = board[self.startRow][self.endCol]



    def __eq__(self, other):
        if isinstance(other, Move):
            return self.moveID == other.moveID
        return False

    def getChessNotation(self) -> list:
        return self.getRankFile(self.startRow, self.startCol) + self.getRankFile(self.endRow, self.endCol)

    def getRankFile(self, row: int, col: int) -> list:
        return self.colsToFiles[col] + self.rowsToRanks[row]
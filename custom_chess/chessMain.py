import pygame as p
from multiprocessing import Process, Queue
from custom_chess.Classes import chessEngine
from custom_chess.Classes.MoveClass import Move
from custom_chess.Classes.chessIA import find_random
from custom_chess.Classes.chessIA import find_better_move_greedy
from custom_chess.Classes.chessIA import find_bestmove_negamax
from custom_chess.Classes.chessIA import find_move_nega_alphabeta


p.init()
board_width = 400
board_height = 400
move_panel_width = 200
move_panel_height = board_height
dimension = 8
sqSize = board_height // dimension
maxFPS = 30
Images = {}


def loadImages():
    pieces = ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR", "wp", "bp", "bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"]
    for piece in pieces:
        Images[piece] = p.transform.scale(p.image.load(f"./custom_chess/images/{piece}.png"), (sqSize, sqSize))


def main():
    p.init()
    screen = p.display.set_mode((board_width + move_panel_width, board_height))
    clock = p.time.Clock()
    screen.fill(p.Color("white"))
    gs = chessEngine.Gamestate()
    validMoves = gs.get_valid_moves_efficient()
    moveMade = False
    animate = False
    move_log_font = p.font.SysFont("Arial", 12, True, False)
    loadImages()
    sqSelected = ()
    playerClicks = []
    running = True
    game = True
    player_white = False
    player_black = False
    IA_thinking = False
    move_finder_process = None
    while running:
        human_turn = (gs.whiteToMove and player_white) or (not gs.whiteToMove and player_black)
        for e in p.event.get():
            if e.type == p.QUIT:
                running = False
            elif e.type == p.MOUSEBUTTONDOWN:
                if game and human_turn:
                    location = p.mouse.get_pos()
                    col = location[0] // sqSize
                    row = location[1] // sqSize
                    if sqSelected == (row, col) or col >= 8:
                        sqSelected = ()
                        playerClicks = []
                    else:
                        sqSelected = (row, col)
                        playerClicks.append((row, col))
                    if len(playerClicks) == 2:
                        move = Move(playerClicks[0], playerClicks[1], gs.board)
                        print(move.getChessNotation())
                        for i in range(len(validMoves)):
                            if move == validMoves[i]:
                                gs.make_move(validMoves[i])
                                moveMade = True
                                sqSelected = ()
                                playerClicks = []
                                animate = True
                        if not moveMade:
                            playerClicks = [sqSelected]
            elif e.type == p.KEYDOWN:
                if e.key == p.K_z:
                    gs.undo_move()
                    moveMade = True
                    animate = False
                    game = True
                    sqSelected = ()
                    playerClicks = []

                if e.key == p.K_F1:
                    gs = chessEngine.Gamestate()
                    validMoves = gs.get_valid_moves_efficient()
                    sqSelected = ()
                    playerClicks = []
                    moveMade = False
                    animate = False
                    game = True

        if game and not human_turn:
            if not IA_thinking:
                IA_thinking = True
                decision_queue = Queue()
                decision_queue.empty()
                move_finder_process = Process(target=find_move_nega_alphabeta, args=(gs, validMoves, decision_queue))
                move_finder_process.start()
            if not move_finder_process.is_alive():
                IA_choice = decision_queue.get()
                #IA_choice = find_random(validMoves)
                #IA_choice = find_better_move_greedy(gs, validMoves)
                #IA_choice = find_bestmove_negamax(gs, validMoves)
                #IA_choice = find_move_nega_alphabeta(gs, validMoves)
                if IA_choice == None:
                    print("random")
                    IA_choice = find_random(validMoves)
                gs.make_move(IA_choice)
                moveMade = True
                animate = True
                IA_thinking = False


        if moveMade:
            if animate:
                animatingMove(gs.moveLog[-1], screen, gs.board, clock)
            validMoves = gs.get_valid_moves_efficient()
            moveMade = False
            animate = False
            sqSelected = ()
            playerClicks = []
            print(gs.board)

        drawGameState(screen, gs, validMoves, sqSelected, move_log_font=move_log_font)
        if gs.checkmate or gs.stalemate:
            game = False
            if gs.whiteToMove and gs.checkmate:
                text = "Black wins"
            elif not gs.whiteToMove and gs.checkmate:
                text = "White wins"
            else:
                text = "Draw"
            draw_end_ext(screen, text)

        clock.tick(maxFPS)
        p.display.flip()


def highlight_squares(screen, gamestate, validmoves, sqselected):
    if sqselected != ():
        row, col = sqselected
        if gamestate.board[row][col][0] == "w" and gamestate.whiteToMove:
            s = p.Surface((sqSize, sqSize))
            s.set_alpha(100)
            s.fill(color=p.Color("blue"))
            s.blit(s, (col * sqSize, row * sqSize))
            s.fill(color=p.Color("yellow"))
            for move in validmoves:
                if move.startRow == row and move.startCol == col:
                    screen.blit(s, (sqSize * move.endCol, sqSize * move.endRow))
        elif gamestate.board[row][col][0] == "b" and not gamestate.whiteToMove:
            s = p.Surface((sqSize, sqSize))
            s.set_alpha(100)
            s.fill(color=p.Color("blue"))
            s.blit(s, (col * sqSize, row * sqSize))
            s.fill(color=p.Color("yellow"))
            for move in validmoves:
                if move.startRow == row and move.startCol == col:
                    screen.blit(s, (sqSize * move.endCol, sqSize * move.endRow))

def draw_end_ext(screen, text):
    font = p.font.SysFont("Arial", 32, True, False)
    text_object = font.render(text, 0, p.Color("Black"))
    text_location = p.Rect(0, 0, board_width, board_height).move(board_width / 2 - text_object.get_width() / 2, board_height / 2 - text_object.get_height() / 2)
    screen.blit(text_object, text_location)

def draw_move_log(screen, gs, move_log_font):
    move_log_area = p.Rect(board_width, 0, move_panel_width, move_panel_height)
    p.draw.rect(screen, p.Color("white"), move_log_area)
    movelog: list[Move] = gs.moveLog
    move_text: list[Move] = movelog
    padding = 5
    test_y = padding
    for i in range(len(move_text)):
        if test_y >= move_panel_height:
            screen.fill(p.Color("white"), move_log_area)
            test_y = padding
        text = move_text[i].getChessNotation()
        text_object = move_log_font.render(text, True, p.Color("Black"))
        text_location = move_log_area.move(padding, test_y)
        #text_location = p.Rect(0, 0, withRes, height).move(withRes/2 - text_object.get_width()/2, height / 2 - text_object.get_height() / 2)
        screen.blit(text_object, text_location)
        test_y += text_object.get_height()


def drawGameState(screen, gs, validMoves, sqSeleted, move_log_font):
    drawBoard(screen)
    highlight_squares(screen, gs, validMoves, sqSeleted)
    drawPieces(screen, gs.board)
    draw_move_log(screen, gs, move_log_font)


def drawBoard(screen):
    colors = [p.Color("white"), p.Color("gray")]
    for row in range(dimension):
        for col in range(dimension):
            color = colors[((row + col) % 2)]
            p.draw.rect(screen, color, p.Rect(col * sqSize, row * sqSize, sqSize, sqSize))


def drawPieces(screen, board):
    for row in range(dimension):
        for col in range(dimension):
            piece = board[row][col]
            if piece != "__":
                screen.blit(Images[piece], p.Rect(col * sqSize, row * sqSize, sqSize, sqSize))

def animatingMove(move, screen, board, clock):
    colors = [p.Color("white"), p.Color("gray")]
    delta_row = move.endRow - move.startRow
    delta_col = move.endCol - move.startCol
    framesPerSquare = 10
    frameCount = (abs(delta_row) + abs(delta_col)) * framesPerSquare
    for frame in range(frameCount + 1):
        row = move.startRow + delta_row * frame/frameCount
        col = move.startCol + delta_col * frame/frameCount
        drawBoard(screen)
        drawPieces(screen, board)
        color = colors[(move.endRow + move.endCol) % 2]
        endsquare = p.Rect(move.endCol * sqSize, move.endRow * sqSize, sqSize, sqSize)
        p.draw.rect(screen, color, endsquare)
        if move.pieceCaptured != "__":
            if move.isenpassantMove:
                if move.pieceMoved[0] == "b":
                    enpassant_row = move.endRow + 1
                else:
                    enpassant_row = move.endRow - 1
                endsquare = p.Rect(move.endCol * sqSize, enpassant_row * sqSize, sqSize, sqSize)
            screen.blit(Images[move.pieceCaptured], endsquare)

        screen.blit(Images[move.pieceMoved], p.Rect(col * sqSize, row * sqSize, sqSize, sqSize))
        p.display.flip()
        clock.tick(60)


if __name__ == '__main__':
    main()

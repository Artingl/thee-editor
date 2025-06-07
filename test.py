import pygame
import threading
import time
from pygame.locals import *

# Global variable to track window size
window_size = (800, 600)

def window_watcher():
    global window_size
    while True:
        current_size = pygame.display.get_window_size()
        if current_size != window_size:
            window_size = current_size
            print(f"[Watcher] Detected resize: {window_size}")
            # You can also post a custom event
            pygame.event.post(pygame.event.Event(USEREVENT, {'resize': window_size}))
        time.sleep(0.1)

def main():
    global window_size
    pygame.init()
    screen = pygame.display.set_mode(window_size, RESIZABLE)
    pygame.display.set_caption("Resizable Window with Resize Watcher")

    # Start background thread
    threading.Thread(target=window_watcher, daemon=True).start()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

            elif event.type == VIDEORESIZE:
                print(f"[VIDEORESIZE] Resize event: {event.size}")
                screen = pygame.display.set_mode(event.size, RESIZABLE)

            elif event.type == USEREVENT and 'resize' in event.dict:
                # Respond to background watcher
                print(f"[USEREVENT] Resize from watcher: {event.resize}")
                screen = pygame.display.set_mode(event.resize, RESIZABLE)

        screen.fill((60, 60, 60))
        pygame.draw.rect(screen, (255, 0, 255), (0, 0, 300, 300))
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
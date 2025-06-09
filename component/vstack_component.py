import pygame

from .component import Component


class VStackComponent(Component):
    def __init__(self, app, position):
        super().__init__(app, position)
        self.focused_component = None
        self.current_focused_index = 0

    def add_child_component(self, component):
        if self.focused_component:
            self.focused_component.is_focused = False
        self.focused_component = component
        component.is_focused = True
        self.current_focused_index = len(self.children)
        self.update_stack()
        return super().add_child_component(component)

    def focus_next(self):
        if self.focused_component:
            self.focused_component.is_focused = False
            self.current_focused_index += 1
            if self.current_focused_index >= len(self.children):
                self.current_focused_index = 0

            self.focused_component = self.children[self.current_focused_index]
            self.focused_component.is_focused = True

    def focus_previous(self):
        if self.focused_component:
            self.focused_component.is_focused = False
            self.current_focused_index -= 1
            if self.current_focused_index < 0:
                self.current_focused_index = len(self.children) - 1

            self.focused_component = self.children[self.current_focused_index]
            self.focused_component.is_focused = True

    def remove_focused(self):
        if self.focused_component and len(self.children) > 1:
            current_index = self.current_focused_index
            self.children.pop(current_index).cleanup()
            self.focus_next()

    def update_stack(self):
        if not self.children:
            return
        
        y_offset = 0
        component_height = self.get_height() // len(self.children)
        for component in self.children:
            component.update_dimensions((self.get_width(), component_height), (0, y_offset))
            y_offset += component_height

    def draw(self):
        for i in self.children:
            i.draw_frame(self.surface)
            border_color = (120, 120, 120)
            if i.is_focused:
                border_color = (255, 255, 255)
            pygame.draw.rect(self.surface, border_color, (*i.position, i.get_width(), i.get_height()), 2)

    def get_focused_component(self):
        return self.focused_component

    def key_down_event(self, key, unicode, modifier):
        if self.focused_component:
            self.focused_component.key_down_event(key, unicode, modifier)

    def key_pressed_event(self, key, unicode, modifier):
        if self.focused_component:
            self.focused_component.key_pressed_event(key, unicode, modifier)

    def key_up_event(self, key, unicode, modifier):
        if self.focused_component:
            self.focused_component.key_up_event(key, unicode, modifier)

    def mouse_wheel_event(self, x, y):
        if self.focused_component:
            self.focused_component.mouse_wheel_event(x, y)

    def update_dimensions(self, size, position):
        super().update_dimensions(size, position)
        self.update_stack()

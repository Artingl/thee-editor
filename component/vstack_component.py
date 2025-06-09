import pygame

from .component import Component


class VStackComponent(Component):
    def __init__(self, app, position):
        super().__init__(app, position)
        self.focused_component = None
        self.current_focused_index = 0
        self.height_modifier = []

    def add_child_component(self, component):
        if self.focused_component:
            self.focused_component.is_focused = False
        self.focused_component = component
        component.is_focused = True
        self.current_focused_index = len(self.children)
        self.height_modifier.append(1)
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

    def focus_extend(self, amount=0.2):
        if self.focused_component:
            self.height_modifier[self.current_focused_index] += amount

            for idx in range(len(self.height_modifier)):
                if idx != self.current_focused_index:
                    self.height_modifier[idx] -= amount

                if self.height_modifier[idx] > 3:
                    self.height_modifier[idx] = 3

    def focus_shrink(self, amount=0.2):
        if self.focused_component:
            self.height_modifier[self.current_focused_index] -= amount

            for idx in range(len(self.height_modifier)):
                if idx != self.current_focused_index:
                    self.height_modifier[idx] += amount

                if self.height_modifier[idx] < 0.6:
                    self.height_modifier[idx] = 0.6

    def remove_focused(self):
        if self.focused_component and len(self.children) > 1:
            current_index = self.current_focused_index
            self.children.pop(current_index).cleanup()
            self.height_modifier.pop(self.current_focused_index)
            self.focus_next()

    def update_stack(self):
        if not self.children:
            return
        
        if len(self.height_modifier) == 1:
            self.height_modifier[0] = 1

        y_offset = 0
        for idx, component in enumerate(self.children):
            component_height = round((self.get_height() // len(self.children)) * self.height_modifier[idx])
            component.update_dimensions((self.get_width() - 2, component_height - 2), (1, y_offset + 1))
            y_offset += component_height

    def draw(self):
        for i in self.children:
            i.draw_frame(self.surface)
            border_color = (120, 120, 120)
            if i.is_focused:
                border_color = (255, 255, 255)
            pygame.draw.rect(self.surface, border_color, (*i.position, i.get_width(), i.get_height()), 1)

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

# visual_grid_game.py
import random
import tkinter as tk


class VisualGridHuntGame:
    """A flexible Pacman-style grid environment with support for configurable opponents and larger scales."""

    def __init__(self, width=10, height=10, num_food=10, num_opponents=2, custom_walls=None):
        self.width = width
        self.height = height
        self.agent_pos = [0, 0]  # Starting position (x, y)
        # Agent facing direction (used to provide local, direction-relative percepts)
        self.facing = 'Up'

        if custom_walls is not None:
            self.walls = set(custom_walls)
        else:
            # Generate some default scattered walls for a larger grid
            self.walls = {(2, 2), (2, 3), (5, 5), (6, 5), (3, 7)}

        # Dynamically generate random food positions avoiding walls and agent start
        self.food_positions = set()
        while len(self.food_positions) < num_food:
            fx = random.randint(0, self.width - 1)
            fy = random.randint(0, self.height - 1)
            pos_tuple = (fx, fy)
            if pos_tuple != (0, 0) and pos_tuple not in self.walls:
                self.food_positions.add(pos_tuple)

        # Generate toxic traps in safe cells, avoiding the start, walls, and food
        self.toxic_traps = set()
        max_traps = max(1, min(4, num_food // 2))
        attempts = 0
        while len(self.toxic_traps) < max_traps and attempts < 1000:
            tx = random.randint(0, self.width - 1)
            ty = random.randint(0, self.height - 1)
            trap_pos = (tx, ty)
            if (trap_pos != (0, 0) and trap_pos not in self.walls and trap_pos not in self.food_positions
                    and trap_pos not in self.toxic_traps):
                self.toxic_traps.add(trap_pos)
            attempts += 1

        # Generate adversarial opponents
        self.opponents = []
        while len(self.opponents) < num_opponents:
            ox = random.randint(0, self.width - 1)
            oy = random.randint(0, self.height - 1)
            op_pos = [ox, oy]
            if tuple(op_pos) != (0, 0) and tuple(op_pos) not in self.walls and tuple(op_pos) not in self.food_positions:
                self.opponents.append(op_pos)

        self.score = 0
        self.steps = 0
        self.collision = False

    def get_percept(self) -> dict:
        """Return only local, boolean percepts relative to the agent's current facing direction.

        The percept no longer exposes exact global coordinates like agent_pos or opponent_positions.
        Instead it provides booleans about the cell directly in front of the agent (based on self.facing)
        and booleans describing the current cell (e.g., food_here).
        """
        ax, ay = self.agent_pos

        # Determine the cell ahead based on facing
        dx = dy = 0
        if self.facing == 'Up':
            dy = 1
        elif self.facing == 'Down':
            dy = -1
        elif self.facing == 'Left':
            dx = -1
        elif self.facing == 'Right':
            dx = 1

        ahead_x = ax + dx
        ahead_y = ay + dy

        # Helper to check bounds
        def in_bounds(x, y):
            return 0 <= x < self.width and 0 <= y < self.height

        wall_ahead = False
        food_ahead = False
        toxin_ahead = False
        opponent_ahead = False

        if not in_bounds(ahead_x, ahead_y):
            # Treat out-of-bounds as a wall
            wall_ahead = True
        else:
            ahead_pos = (ahead_x, ahead_y)
            wall_ahead = ahead_pos in self.walls
            food_ahead = ahead_pos in self.food_positions
            toxin_ahead = ahead_pos in self.toxic_traps
            opponent_ahead = any(tuple(op) == ahead_pos for op in self.opponents)

        # Current-cell percepts (booleans only)
        current_pos = tuple(self.agent_pos)
        food_here = current_pos in self.food_positions
        toxin_here = current_pos in self.toxic_traps
        hit_wall = current_pos in self.walls

        return {
            'facing': self.facing,
            'wall_ahead': wall_ahead,
            'food_ahead': food_ahead,
            'toxin_ahead': toxin_ahead,
            'opponent_ahead': opponent_ahead,
            'food_here': food_here,
            'toxin_here': toxin_here,
            'hit_wall': hit_wall,
            'collision': self.collision,
            'score': self.score,
            'remaining_food': len(self.food_positions)
        }

    def execute_action(self, action: str):
        self.steps += 1
        new_pos = list(self.agent_pos)

        # Update facing direction for the agent when a movement action is executed
        if action in ('Up', 'Down', 'Left', 'Right'):
            self.facing = action

        if action == 'Up':
            new_pos[1] = min(self.height - 1, new_pos[1] + 1)
        elif action == 'Down':
            new_pos[1] = max(0, new_pos[1] - 1)
        elif action == 'Left':
            new_pos[0] = max(0, new_pos[0] - 1)
        elif action == 'Right':
            new_pos[0] = min(self.width - 1, new_pos[0] + 1)

        if tuple(new_pos) in self.walls:
            self.score -= 5
        else:
            self.agent_pos = new_pos

        tuple_pos = tuple(self.agent_pos)
        if tuple_pos in self.toxic_traps:
            self.score -= 15
        
        if tuple_pos in self.food_positions:
            self.food_positions.remove(tuple_pos)
            self.score += 20

        for op in self.opponents:
            move = random.choice(['Up', 'Down', 'Left', 'Right', 'Stay'])
            if move == 'Up' and op[1] < self.height - 1:
                op[1] += 1
            elif move == 'Down' and op[1] > 0:
                op[1] -= 1
            elif move == 'Left' and op[0] > 0:
                op[0] -= 1
            elif move == 'Right' and op[0] < self.width - 1:
                op[0] += 1

            if op == self.agent_pos:
                self.score -= 50
                self.collision = True

    def is_done(self) -> bool:
        return len(self.food_positions) == 0 or self.steps >= 60 or self.collision


class SimpleReflexAgent:
    """
    A simple reflex agent that uses strictly IF-THEN logic (Condition-Action rules).
    No internal state or history is stored. Decisions are based solely on current percepts.
    
    This demonstrates the fundamental limitation of reactive agents: they can get
    trapped in infinite loops when facing U-shaped walls or corners.
    """
    
    def sense_and_act(self, percept: dict) -> str:
        """
        Pure condition-action rules. No state, no memory, only immediate reactions.
        
        Rules are evaluated in order of priority:
        1. IF food_here THEN suck (stay in place and consume)
        2. IF toxin_here THEN move away (turn and step forward to escape)
        3. IF wall_ahead THEN turn_left (avoid obstacles)
        4. ELSE move_forward (explore)
        """
        
        # Rule 1: Food at current location
        if percept['food_here']:
            return 'Suck'
        
        # Rule 2: Standing on toxic trap - try to escape
        if percept['toxin_here']:
            return 'TurnLeft'
        
        # Rule 3: Wall directly ahead - turn left to navigate
        if percept['wall_ahead']:
            return 'TurnLeft'
        
        # Rule 4: Default action - move forward
        return 'MoveForward'


class ModelBasedAgent:
    """
    A model-based reflex agent that maintains internal state (memory) about the environment.
    
    It records visited cells and movement history to detect loops and make smarter decisions.
    This agent can escape from U-shaped traps by remembering what has been explored.
    
    Transition Model: Updates visited cells and direction history based on actions taken.
    Sensor Model: Integrates percepts with internal state to make informed decisions.
    """
    
    def __init__(self):
        """Initialize the agent's internal memory state."""
        self.visited_cells = set()           # Track cells visited
        self.last_action = None              # Last action taken
        self.last_facing = 'Up'              # Last facing direction
        self.action_sequence = []            # Sequence of last N actions (for loop detection)
        self.max_sequence_length = 8         # Check for loops in last 8 steps
        self.turn_attempts = 0               # Count consecutive turn attempts
        
    def _relative_position(self, percept: dict) -> tuple:
        """
        Compute a relative position tracker based on facing direction and actions.
        This helps identify which direction has been explored.
        """
        facing = percept['facing']
        return (0, 0, facing)  # Simplified: (x_offset, y_offset, facing)
    
    def _detect_loop(self) -> bool:
        """
        Detect if agent is stuck in a loop by checking if recent actions repeat.
        Returns True if a repeating pattern is detected.
        """
        if len(self.action_sequence) < 4:
            return False
        
        # Check for repeating 2-action patterns (e.g., TurnLeft, MoveForward, TurnLeft, MoveForward)
        recent = self.action_sequence[-4:]
        if recent[0] == recent[2] and recent[1] == recent[3]:
            return True
        
        # Check for repeating 3-action patterns
        if len(self.action_sequence) >= 6:
            recent = self.action_sequence[-6:]
            if recent[0:3] == recent[3:6]:
                return True
        
        return False
    
    def _get_alternate_direction(self, percept: dict) -> str:
        """
        When stuck in a loop, try an alternate direction.
        Rotate right instead of left to break out of corner traps.
        """
        facing = percept['facing']
        facing_map = {'Up': 'Right', 'Right': 'Down', 'Down': 'Left', 'Left': 'Up'}
        return facing_map.get(facing, 'Up')
    
    def sense_and_act(self, percept: dict) -> str:
        """
        Update internal state (Transition Model) and make decisions (Sensor Model).
        
        Priority rules:
        1. IF food_here THEN suck
        2. IF toxin_here THEN turn_right (escape)
        3. IF in_loop AND wall_ahead THEN turn_right (break cycle)
        4. IF wall_ahead THEN turn_left
        5. ELSE move_forward
        """
        
        # ========== TRANSITION MODEL: Update internal state ==========
        current_pos = (percept.get('_agent_x', 0), percept.get('_agent_y', 0))
        self.visited_cells.add(current_pos)
        self.last_facing = percept['facing']
        
        # Record action sequence for loop detection
        if self.last_action is not None:
            self.action_sequence.append(self.last_action)
            if len(self.action_sequence) > self.max_sequence_length:
                self.action_sequence.pop(0)
        
        # ========== SENSOR MODEL: Integrate percepts with state ==========
        loop_detected = self._detect_loop()
        
        # Rule 1: Food at current location
        if percept['food_here']:
            self.last_action = 'Suck'
            return 'Suck'
        
        # Rule 2: Standing on toxic trap - escape by turning right
        if percept['toxin_here']:
            self.last_action = 'TurnRight'
            return 'TurnRight'
        
        # Rule 3: If wall ahead AND we detected a loop, turn right (alternate strategy)
        if percept['wall_ahead'] and loop_detected:
            self.last_action = 'TurnRight'
            return 'TurnRight'
        
        # Rule 4: Wall directly ahead - default to turn left
        if percept['wall_ahead']:
            self.last_action = 'TurnLeft'
            return 'TurnLeft'
        
        # Rule 5: Default - move forward to explore
        self.last_action = 'MoveForward'
        return 'MoveForward'


class GridGameGUI:
    """Tkinter wrapper that dynamically scales cell sizes to keep larger grids on screen."""

    def __init__(self, root, width=10, height=10, num_food=12, num_opponents=2, walls=None, agent=None):
        self.root = root
        self.root.title("IT3012 - Scalable Multi-Agent Grid Hunt")

        self.env = VisualGridHuntGame(width=width, height=height, num_food=num_food, num_opponents=num_opponents,
                                      custom_walls=walls)
        self.agent = agent  # Can be None for random agent, or a reflex/model-based agent instance

        # Dynamically calculate cell size so the total canvas fits nicely within a 600x600 window ceiling
        max_canvas_dim = 600
        self.cell_size = max(20, min(max_canvas_dim // self.env.width, max_canvas_dim // self.env.height))

        canvas_w = self.env.width * self.cell_size
        canvas_h = self.env.height * self.cell_size

        self.canvas = tk.Canvas(root, width=canvas_w, height=canvas_h, bg="white")
        self.canvas.pack()

        self.label = tk.Label(root, text="Score: 0 | Steps: 0", font=("Arial", 14))
        self.label.pack(pady=10)

        agent_type = type(self.agent).__name__ if self.agent else "Random Agent"
        self.btn = tk.Button(root, text=f"Start Simulation ({agent_type})", command=self.run_loop, font=("Arial", 12), 
                             bg="#000066", fg="white")
        self.btn.pack(pady=5)

        self.draw_grid()

    def draw_grid(self):
        self.canvas.delete("all")

        for x in range(self.env.width):
            for y in range(self.env.height):
                x1 = x * self.cell_size
                y1 = (self.env.height - 1 - y) * self.cell_size
                x2 = x1 + self.cell_size
                y2 = y1 + self.cell_size

                color = "#f1f5f9" if (x, y) not in self.env.walls else "#64748b"
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#cbd5e1")

                # Only draw text if cell is large enough
                if self.cell_size >= 40 and (x, y) in self.env.walls:
                    self.canvas.create_text(x1 + self.cell_size / 2, y1 + self.cell_size / 2, text="W", fill="white",
                                            font=("Arial", 8, "bold"))

        for fx, fy in self.env.food_positions:
            offset = self.cell_size * 0.25
            x1 = fx * self.cell_size + offset
            y1 = (self.env.height - 1 - fy) * self.cell_size + offset
            self.canvas.create_oval(x1, y1, x1 + self.cell_size * 0.5, y1 + self.cell_size * 0.5, fill="#f59e0b",
                                    outline="#d97706")

        for tx, ty in self.env.toxic_traps:
            x1 = tx * self.cell_size
            y1 = (self.env.height - 1 - ty) * self.cell_size
            cx = x1 + self.cell_size / 2
            cy = y1 + self.cell_size / 2
            offset = self.cell_size * 0.25
            points = [
                (cx, y1 + offset),
                (x1 + self.cell_size - offset, cy),
                (cx, y1 + self.cell_size - offset),
                (x1 + offset, cy),
            ]
            self.canvas.create_polygon(points, fill="#8b5cf6", outline="#6d28d9", width=2)

        for ox, oy in self.env.opponents:
            offset = self.cell_size * 0.2
            x1 = ox * self.cell_size + offset
            y1 = (self.env.height - 1 - oy) * self.cell_size + offset
            self.canvas.create_rectangle(x1, y1, x1 + self.cell_size * 0.6, y1 + self.cell_size * 0.6, fill="#990000",
                                         outline="#7a0000")

        ax, ay = self.env.agent_pos
        offset = self.cell_size * 0.15
        x1 = ax * self.cell_size + offset
        y1 = (self.env.height - 1 - ay) * self.cell_size + offset
        self.canvas.create_oval(x1, y1, x1 + self.cell_size * 0.7, y1 + self.cell_size * 0.7, fill="#000066",
                                outline="#1e3a8a")

    def run_loop(self):
        self.btn.config(state="disabled")

        def step():
            if not self.env.is_done():
                # Get agent's action based on agent type
                if self.agent:
                    percept = self.env.get_percept()
                    agent_action = self.agent.sense_and_act(percept)
                    
                    # Map agent actions to environment actions
                    if agent_action == 'Suck':
                        action = 'Stay'  # Stay in place (food is consumed in execute_action)
                    elif agent_action == 'TurnLeft':
                        # Turn left based on current facing
                        facing_map = {'Up': 'Left', 'Left': 'Down', 'Down': 'Right', 'Right': 'Up'}
                        action = facing_map.get(self.env.facing, 'Up')
                    elif agent_action == 'TurnRight':
                        # Turn right based on current facing
                        facing_map = {'Up': 'Right', 'Right': 'Down', 'Down': 'Left', 'Left': 'Up'}
                        action = facing_map.get(self.env.facing, 'Up')
                    elif agent_action == 'MoveForward':
                        action = self.env.facing
                    else:
                        action = random.choice(['Up', 'Down', 'Left', 'Right'])
                else:
                    # Random agent
                    action = random.choice(['Up', 'Down', 'Left', 'Right'])
                
                self.env.execute_action(action)

                self.draw_grid()
                self.label.config(text=f"Score: {self.env.score} | Steps: {self.env.steps} | Action: {action}")
                self.root.after(250, step)
            else:
                end_text = f"Collision! Game Over! Final Score: {self.env.score}" if self.env.collision else f"Finished! Final Score: {self.env.score}"
                self.label.config(text=end_text)
                self.btn.config(state="normal")

        step()


if __name__ == "__main__":
    root = tk.Tk()
    
    # Create a U-shaped wall configuration to trap the reflex agent
    u_shaped_walls = {
        (2, 1), (2, 2), (2, 3), (2, 4), (2, 5),  # Left vertical
        (3, 1), (4, 1), (5, 1), (6, 1),          # Bottom horizontal
        (7, 1), (7, 2), (7, 3), (7, 4), (7, 5),  # Right vertical
    }
    
    # Test with ModelBasedAgent (should escape the U-shaped trap!)
    agent = ModelBasedAgent()
    app = GridGameGUI(root, width=10, height=8, num_food=3, num_opponents=0, walls=u_shaped_walls, agent=agent)
    
    # Uncomment to compare with SimpleReflexAgent (will get stuck in loop)
    # agent = SimpleReflexAgent()
    # app = GridGameGUI(root, width=10, height=8, num_food=3, num_opponents=0, walls=u_shaped_walls, agent=agent)
    
    # Uncomment to run with Random Agent for comparison
    # app = GridGameGUI(root, width=10, height=8, num_food=3, num_opponents=0, walls=u_shaped_walls, agent=None)
    
    root.mainloop()

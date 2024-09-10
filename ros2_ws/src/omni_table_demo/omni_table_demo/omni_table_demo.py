import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32MultiArray, String
from geometry_msgs.msg import Twist
from transformers import pipeline
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import math
from typing import List, Dict, Tuple
import logging

# Enums
class Action(Enum):
    MOVE_FORWARD = "move_forward"
    MOVE_BACKWARD = "move_backward"
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    MOVE_FORWARD_LEFT = "move_forward_left"
    MOVE_FORWARD_RIGHT = "move_forward_right"
    MOVE_BACKWARD_LEFT = "move_backward_left"
    MOVE_BACKWARD_RIGHT = "move_backward_right"
    SPIN_CLOCKWISE = "spin_clockwise"
    SPIN_COUNTERCLOCKWISE = "spin_counterclockwise"
    STOP = "stop"

# Constants
DEFAULT_SPEED = 0.2
DIAGONAL_FACTOR = math.cos(math.pi/4)
CMD_VEL_TOPIC = 'rcm/cmd_vel'  # Updated topic name

# Interfaces
class ILanguageModel(ABC):
    @abstractmethod
    def generate(self, prompt: str, max_length: int, num_return_sequences: int) -> List[Dict]:
        pass

class IValueFunction(ABC):
    @abstractmethod
    def get_value(self, action: Action) -> float:
        pass

# Implementations
class GPT2LanguageModel(ILanguageModel):
    def __init__(self):
        self.model = pipeline("text-generation", model="gpt2")

    def generate(self, prompt: str, max_length: int, num_return_sequences: int) -> List[Dict]:
        return self.model(prompt, max_length=max_length, num_return_sequences=num_return_sequences)

class SimpleValueFunction(IValueFunction):
    def __init__(self):
        self.values = {
            Action.MOVE_FORWARD: 0.5,
            Action.MOVE_BACKWARD: 0.4,
            Action.MOVE_LEFT: 0.4,
            Action.MOVE_RIGHT: 0.4,
            Action.MOVE_FORWARD_LEFT: 0.45,
            Action.MOVE_FORWARD_RIGHT: 0.45,
            Action.MOVE_BACKWARD_LEFT: 0.35,
            Action.MOVE_BACKWARD_RIGHT: 0.35,
            Action.SPIN_CLOCKWISE: 0.3,
            Action.SPIN_COUNTERCLOCKWISE: 0.3,
            Action.STOP: 0.1
        }

    def get_value(self, action: Action) -> float:
        return self.values.get(action, 0.0)

@dataclass
class RobotContext:
    description: str = "The robot table is in a quiet room."

class ActionSelector:
    def __init__(self, language_model: ILanguageModel, value_function: IValueFunction):
        self.language_model = language_model
        self.value_function = value_function

    def select_action(self, context: RobotContext, angle: float, confidence: float) -> Action:
        prompt = f"Context: {context.description}\nSound detected at angle {angle} degrees with confidence {confidence}. The robot table should"
        action_proposals = self.language_model.generate(prompt, max_length=50, num_return_sequences=3)

        scores = []
        for proposal in action_proposals:
            for action in Action:
                if action.value in proposal[0]['generated_text'].lower():
                    score = self.value_function.get_value(action) * confidence
                    scores.append((action, score))

        if scores:
            return max(scores, key=lambda x: x[1])[0]
        return Action.STOP

class MotionController:
    @staticmethod
    def get_twist_for_action(action: Action, speed: float = DEFAULT_SPEED) -> Twist:
        twist = Twist()
        if action == Action.MOVE_FORWARD:
            twist.linear.x = speed
        elif action == Action.MOVE_BACKWARD:
            twist.linear.x = -speed
        elif action == Action.MOVE_LEFT:
            twist.linear.y = speed
        elif action == Action.MOVE_RIGHT:
            twist.linear.y = -speed
        elif action == Action.MOVE_FORWARD_LEFT:
            twist.linear.x = speed * DIAGONAL_FACTOR
            twist.linear.y = speed * DIAGONAL_FACTOR
        elif action == Action.MOVE_FORWARD_RIGHT:
            twist.linear.x = speed * DIAGONAL_FACTOR
            twist.linear.y = -speed * DIAGONAL_FACTOR
        elif action == Action.MOVE_BACKWARD_LEFT:
            twist.linear.x = -speed * DIAGONAL_FACTOR
            twist.linear.y = speed * DIAGONAL_FACTOR
        elif action == Action.MOVE_BACKWARD_RIGHT:
            twist.linear.x = -speed * DIAGONAL_FACTOR
            twist.linear.y = -speed * DIAGONAL_FACTOR
        elif action == Action.SPIN_CLOCKWISE:
            twist.angular.z = -speed
        elif action == Action.SPIN_COUNTERCLOCKWISE:
            twist.angular.z = speed
        return twist

class OmniTableRobotSayCan(Node):
    def __init__(self, language_model: ILanguageModel, value_function: IValueFunction):
        super().__init__('omni_table_robot_saycan')
        self.subscription = self.create_subscription(
            Float32MultiArray,
            'sound_localization',
            self.sound_callback,
            10)
        self.publisher = self.create_publisher(Twist, CMD_VEL_TOPIC, 10)  # Updated topic name
        self.context_sub = self.create_subscription(
            String,
            'robot_context',
            self.update_context,
            10)
        self.context = RobotContext()
        self.action_selector = ActionSelector(language_model, value_function)
        self.motion_controller = MotionController()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.info('Omnidirectional Table Robot node with SayCan-inspired decision making initialized')

    def update_context(self, msg: String) -> None:
        self.context.description = msg.data
        self.logger.info(f'Updated context: {self.context.description}')

    def sound_callback(self, msg: Float32MultiArray) -> None:
        angle, confidence = msg.data
        action = self.action_selector.select_action(self.context, angle, confidence)
        twist = self.motion_controller.get_twist_for_action(action)
        self.publisher.publish(twist)
        self.logger.info(f'Executing action: {action.value} based on sound: angle={angle}, confidence={confidence}')

def main(args=None):
    rclpy.init(args=args)
    language_model = GPT2LanguageModel()
    value_function = SimpleValueFunction()
    omni_table_robot = OmniTableRobotSayCan(language_model, value_function)
    try:
        rclpy.spin(omni_table_robot)
    except KeyboardInterrupt:
        pass
    finally:
        omni_table_robot.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
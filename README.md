# Omni Table Demo
A simple ROS2 program to control Hagrid the table robot using Spatial Audio Localization (SAL) and voice commands. 

The program selects and executes the most reasonable command according to the [SayCan framework](https://say-can.github.io/).

## How the program works
1. The program subscribes to SAL data from the robot
2. The SAL data is fed into an large language model (LLM), which then proposes a series of possible actions to execute
3. The program selects the most reasonable action to execute according to a weighted value function
4. Once an action is selected, the program publishes the action to the robot to execute

## Benefits of the program design
1. The action proposals generated by the LLM are wrapped around an `ILanguageModel` interface, allowing for extensibility to change language model and avoid vendor lock in
2. How the actions are executed are wrapped around a `MotionController` class, allowing for unit tests of the robots actions and the ability to change the execution actions for other types of furniture
3. The value function that selects the most probable action are wrapped around a `IValueFunction` interface, allowing for extensibility to change the value function easily 

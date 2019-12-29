#Configuring the orchestrator

## High-level concepts

The orchestrator generally follows the following logic:
* **Spawn the relevant objects**: There are a few different objects that can be spawned: the robot, the bonus cones, and the end point. Based on the configuration, it will spawn these objects.
* **Check if the run is over**: The run can be configured to end on any of the following conditions:
    * **Time**: If the run has been running for a predetermined threshold of time, then the run is considered over.
    * **Goal point reached**: If the goal point is reached within the specified tolerance, then the run is considered over.
    * **Runaway Robot**: If the robot wanders outside a predefined geofence, then the run will be considered over.
    * **Collision**: If the robot collides with an unexpected object (e.g. not a bonus cone), then the run will be considered over.
* **Check if any cones are touched or the goal is reached**: If so, update the statuses.
* **Compute the score on run end.**: Before the run is complete, the score will be zero. Once the run is complete, the score for the run will be computed as the time it took for the bot to reach the goal point in seconds, multiplied by each of the multipliers for the bonus cones reached. For example, if the bot reached the goal in 200 seconds, but touched two bonus cones with multipliers of 0.5 and 0.25 respectively, the final score will be 200 * 0.5 * 0.25 = 25.

The orchestrator code runs synchronously with the control code, so the function run_tick() must be called periodically.

## Orchestrator configuration
The configuration file is a JSON file that specifies the parameters of the competition run. A sample configuration can be found in [RoboMagellanOrchestraotr/TestOrchestratorConfiguration.json](https://github.com/mitchellspryn/RoboMagellanOrchestrator/blob/master/RoboMagellanOrchestrator/TestOrchestrationConfiguration.json). It is intended to be used with the [Three Bridges Map](https://github.com/mitchellspryn/AnnotatedUnrealMaps/blob/master/Docs/Maps.md) from the annotated unreal engines. This map can be downloaded from the [Annotated Unreal Maps' release page](https://github.com/mitchellspryn/AnnotatedUnrealMaps/releases/tag/v1.0). The configuration file has the following schema:

* **timeLimit**: The maximum runtime of the simulation, in seconds.
* **endRunOnCollision**: If true, colliding with another object that is not a cone will end the run.
* **zOffset**: When spawning the robot, the Z coordinate will be computed based on the supplied XY so that the robot is on the ground. Depending on the geometry of your robot, this may cause the bot to end up stuck inside the ground. This value (in meters) will be added to the Z coordinate of the spawn condition to compensate. 
* **arenaBounds**: A list of x,y coordinates that represent the outer bounds of the arena. If the robot's position moves outside this boundary, then the run will be declared over. 
* **startPose**: The beginning pose of the robot. This property is **spawnable**.
* **goalPoint**: The goal pose of the robot. Once reached, the run will be completed, and the score can be computed. This propery is **spawnable**. In addition, there are a few additional fields that must be specified:
    * **positionTolerance**: This is the distance, in meters, that the bot must be from the goal pose to be considered "finished." For example, if this value is specified as "2", then when the bot arrives within 2 meters of the goal while simultaneously satisfying the velocityTolerance, the run will be considered finished.
    * **velocityTolerance**: The maximum velocity the bot can have in the goal pose for the run to be considered "finished." For example, if this value is specified as "0.1", then when the bot is moving slower than 0.1 m/s while simulateneously satisyfing the positionTolernace, then the run will be considered finished.
* **cones**: A list of bonus cones to spawn into the world. Each of these cones are **spawnable**. In addition, there are a few additional fields that must be specified:
    * **coneType**: This defines the texturing to use for the cone. There are two types availble: **bright**, which is a bright orange texture, and **normal**, which is a more muted texture. Depending on your scenario, you may decide between them. 
    * **bonusMultiplier**: The value with which to multiply the final score if the cone is reached. Generally, this value is on the range [0, 1]. For example, when specifying a bonusMultiplier of "0.25", then the final scoure will be multiplied by 0.25 if the cone is reached.

For objects marked **spawnable**, there are two mechanisms that can be used to spawn them. These spawn methods are mutually exclusive, and one must be specified for each spawnable object. The first is by specifying a **poseList** member, which is a list of static points which are selected at random. Each element in the poseList field has the following parameters:
    * **x**: The x coordinate of the spawn point.
    * **y**: The y coordinate of the spawn point.
    * **roll**: The roll of the spawn point.
    * **pitch**: The pitch of the spawn point.
    * **yaw**: The yaw of the spawn point.

Note that roll, pitch, and yaw will only have effect for the "startPose" member. 
The other option is specifying a **spawnRegion** member. When specifying a spawn region, a list of x,y coordinates must be provided. A region within this polygon will be selected at random at the start of the run. The z coordinate will be computed so that the object spawns on the ground. If the object would spawn underwater, a new spawn point is chosen. 

## Orchestrator API
Once the orchestrator configuration file has been authored, it can be used with the provided code to run a simulated competition run. A simple example of the simulation can be found at  [RoboMagellanOrchestraotr/TestOrchestratorRun.py](https://github.com/mitchellspryn/RoboMagellanOrchestrator/blob/master/RoboMagellanOrchestrator/TestOrchestratorRun.py). It is intended to be used with the [Three Bridges Map](https://github.com/mitchellspryn/AnnotatedUnrealMaps/blob/master/Docs/Maps.md) from the annotated unreal engines. This map can be downloaded from the [Annotated Unreal Maps' release page](https://github.com/mitchellspryn/AnnotatedUnrealMaps/releases/tag/v1.0). Note that the simulation should already be running in a separate process before invoking the orchestrator.

The orchestrator exposes the following APIs:
* **Constructor**: Accepts the file path to the configuration json.
* **set_debug_draw_enabled(bool)**: Turns on or off the debug drawing. This will draw the spawn locations for each of the objects and the arena bounds with thick colored lines. In addition, this will draw the potential spawning region for each spawnable object with a spawnableRegion attribute. This can be useful for debugging the configuration file, but should be disabled for production runs as the debug drawings will show up in sensor data (e.g. camera data).
* **set_random_seed(int)**: Can be used to seed the RNG and yield determinstic spawning. 
* **start_new_run(client)**: Spawns the objects and starts a new timed run. This accepts a valid AirSim client as an argument, and assumes that all setup has been done (e.g. setApiControl(true) has been called). Once this call returns, the robot will have been translated to the starting position, and the run time has started.
* **get_run_summary(client)**: Gets a dictionary with various values that give information about the status of the run (e.g. elapsed time, which cones have been contacted, cone locations, etc). In particular, there is a member "runComplete", which signifies if the run is over or not. 
* **get_run_summary_string(client)**: A convenience method for printing the run summary information in a human readable format.
* **run_tick(client)**: This method checks the current state of the simulation, and determines what actions need to be taken (e.g. if a cone has been contacted, or if the simulation should continue running.). This should be called as frequently as possible. 
* **clean_up_run(client)**: Does any post-run cleanup necessary (e.g. despawning spawned objects). This should be called before starting a new run if the simluator is not restarted.
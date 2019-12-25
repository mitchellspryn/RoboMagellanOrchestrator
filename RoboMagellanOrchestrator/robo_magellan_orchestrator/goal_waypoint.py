import airsim
import robo_magellan_orchestrator.spawnable_object as spawnable_object

class GoalWaypoint(spawnable_object.SpawnableObject):
    def __init__(self, init_parameters):
        super(GoalWaypoint, self).__init__(init_parameters)
        
        self.position_tolerance = float(init_parameters['positionTolerance'])
        self.velocity_tolerance = float(init_parameters['velocityTolerance'])

        # Record position / velocity as squared values to avoid square roots
        self.position_tolerance = self.position_tolerance ** 2
        self.velocity_tolerance = self.velocity_tolerance ** 2

        self.goal_center = None
        self.visited = False
        self.visited_time_stamp = None
        self.closest_distance = float('inf')

    def reset(self):
        self.visited = False
        self.visited_time_stamp = None
        self.closest_distance = float('inf')

    def spawn(self, client):
        self.spawn_pose = self.get_valid_spawn_coordinates(client, False)
        self.goal_center = self.spawn_pose.position

    def is_bot_at_goal(self, client):
        if (self.goal_center == None):
            return False

        pose = client.simGetVehiclePose()
        kinematics = client.simGetGroundTruthKinematics()

        distance_from_goal = self.__l2_sq(pose.position, self.goal_center)
        velocity = self.__vec_length_sq(kinematics.linear_velocity)

        self.closest_distance = min(self.closest_distance, distance_from_goal)

        return distance_from_goal <= self.position_tolerance and velocity <= self.velocity_tolerance

    def set_visited(self, time_stamp):
        self.visited = True
        self.visited_time_stamp = time_stamp

    def __l2_sq(self, a, b):
        return ((a.x_val-b.x_val)*(a.x_val-b.x_val)) + ((a.y_val-b.y_val)*(a.y_val-b.y_val)) + ((a.z_val-b.z_val)*(a.z_val-b.z_val))

    def __vec_length_sq(self, a):
        return (a.x_val*a.x_val) + (a.y_val*a.y_val) * (a.z_val*a.z_val)

import uuid

import airsim
import robo_magellan_orchestrator.spawnable_object as spawnable_object

class GoalWaypoint(spawnable_object.SpawnableObject):
    def __init__(self, init_parameters):
        super(GoalWaypoint, self).__init__(init_parameters)
        
        self.position_tolerance = float(init_parameters['positionTolerance'])
        self.velocity_tolerance = float(init_parameters['velocityTolerance'])
        self.cone_type = init_parameters['coneType'].lower().strip()

        if (self.cone_type == 'none'):
            self.cone_type = None
        else:
            self.random_name = str(uuid.uuid4())
            if (self.cone_type == 'normal'):
                self.mesh_name = "StaticMesh'/Game/DT_Spring_Landscape/Meshes/SM_traffic_cone.SM_traffic_cone'"
            elif (self.cone_type == 'bright'):
                self.mesh_name =  "StaticMesh'/Game/DT_Spring_Landscape/Meshes/SM_traffic_cone_bright.SM_traffic_cone_bright'"
            else:
                raise ValueError('Unrecognized cone_type: {0}. Valid options are "normal" and "bright".'.format(self.cone_type)) 

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

        if (self.cone_type != None):
            client.simSpawnStaticMeshObject(self.mesh_name, self.random_name, self.spawn_pose)
            client.simSetSegmentationObjectID(self.random_name, 235)

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

    def delete(self, client):
        if (self.cone_type != None):
            client.simDeleteObject(self.random_name)
            self.reset()

    def __l2_sq(self, a, b):
        return ((a.x_val-b.x_val)*(a.x_val-b.x_val)) + ((a.y_val-b.y_val)*(a.y_val-b.y_val)) + ((a.z_val-b.z_val)*(a.z_val-b.z_val))

    def __vec_length_sq(self, a):
        return (a.x_val*a.x_val) + (a.y_val*a.y_val) * (a.z_val*a.z_val)

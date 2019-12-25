import airsim
import robo_magellan_orchestrator.spawnable_object as spawnable_object

import uuid

class ConeWaypoint(spawnable_object.SpawnableObject):
    def __init__(self, init_parameters):
        super(ConeWaypoint, self).__init__(init_parameters)
        self.bonus_multiplier = init_parameters['bonusMultiplier']
        self.cone_type = init_parameters['coneType'].lower().strip()

        if (self.cone_type == 'normal'):
            self.mesh_name = "StaticMesh'/Game/DT_Spring_Landscape/Meshes/SM_traffic_cone.SM_traffic_cone'"
        elif (self.cone_type == 'bright'):
            self.mesh_name =  "StaticMesh'/Game/DT_Spring_Landscape/Meshes/SM_traffic_cone_bright.SM_traffic_cone_bright'"
        else:
            raise ValueError('Unrecognized cone_type: {0}. Valid options are "normal" and "bright".'.format(self.cone_type))

        self.visited = False
        self.random_name = str(uuid.uuid4())
        self.visited_time_stamp = None

    def reset(self):
        self.visited = False
        self.visited_time_stamp = None

    def spawn(self, client):
        self.spawn_pose = self.get_valid_spawn_coordinates(client, True)
        client.simSpawnStaticMeshObject(self.mesh_name, self.random_name, self.spawn_pose)

    def delete(self, client):
        client.simDeleteObject(self.random_name)
        self.reset()

    def set_visited(self, time_stamp):
        self.visited = True
        self.visited_time_stamp = time_stamp



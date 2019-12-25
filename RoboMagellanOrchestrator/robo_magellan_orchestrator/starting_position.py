import airsim
import airsim.airsim_types as at
import robo_magellan_orchestrator.spawnable_object as spawnable_object

class StartingPosition(spawnable_object.SpawnableObject):
    def __init__(self, init_parameters):
        super(StartingPosition, self).__init__(init_parameters)

    def spawn(self, client, z_offset=0):
        self.spawn_pose = self.get_valid_spawn_coordinates(client, False)

        # The raycast tends to place the bot into the ground. 
        # So, spawn the bot a bit above the ground to compensate
        new_pose_vec = at.Vector3r(x_val=self.spawn_pose.position.x_val,
                                   y_val=self.spawn_pose.position.y_val,
                                   z_val=self.spawn_pose.position.z_val + z_offset)

        self.spawn_pose = at.Pose(position_val=new_pose_vec, orientation_val=self.spawn_pose.orientation)

        client.simSetVehiclePose(self.spawn_pose, True)

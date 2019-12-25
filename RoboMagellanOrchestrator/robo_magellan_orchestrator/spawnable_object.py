import shapely
import shapely.geometry
import numpy as np
import math

import airsim
import airsim.airsim_types as at
import robo_magellan_orchestrator.raycast_utils as raycast_utils

class SpawnableObject(object):
    def __init__(self, init_parameters):
        if 'poseList' in init_parameters:
            self.pose_list = self.__parse_pose_list(init_parameters['poseList'])
        else:
            self.pose_list = None

        if 'spawnRegion' in init_parameters:
            self.spawn_region = self.__parse_spawn_region(init_parameters['spawnRegion'])
        else:
            self.spawn_region = None

        if (self.spawn_region == None and self.pose_list == None):
            raise ValueError('Either "poseList" or "spawnRegion" must be specified for all spawnable objects.')
        if (self.spawn_region != None and self.pose_list != None):
            raise ValueError('Both "poseList" and "spawnRegion" cannot be specified for a spawnable object.')

    def get_valid_spawn_coordinates(self, client, align_with_ground):
        if (self.pose_list != None):
            return self.__get_spawn_from_list(client, align_with_ground)
        else:
            return self.__get_spawn_from_region(client, align_with_ground)

    def __get_spawn_from_list(self, client, align_with_ground):
        while True:
            spawn_xy = np.random.choice(self.pose_list)
            spawn_z, normal = raycast_utils.get_ground(spawn_xy.position.x_val, spawn_xy.position.y_val, client)

            if (spawn_z != None and normal != None):
                out_vec = at.Vector3r(x_val=spawn_xy.position.x_val, y_val=spawn_xy.position.y_val, z_val = spawn_z)
                
                if (align_with_ground):
                    out_rot = normal
                else:
                    out_rot = spawn_xy.orientation

                return at.Pose(position_val=out_vec, orientation_val=out_rot)

    def __get_spawn_from_region(self, client, align_with_ground):
        while True:
            x, y = self.__get_xy_from_rejection_sampling(self.spawn_region)
            spawn_z, normal = raycast_utils.get_ground(x, y, client)

            if (spawn_z != None and normal != None):
                out_vec = at.Vector3r(x_val=x, y_val=y, z_val=spawn_z)
                out_rot = normal

                return at.Pose(position_val=out_vec, orientation_val=out_rot)

    def __get_xy_from_rejection_sampling(self, polygon):
        min_x, min_y, max_x, max_y = polygon.bounds
        while True:
            x = ((max_x - min_x) * np.random.random()) + min_x
            y = ((max_y - min_y) * np.random.random()) + min_y
            point = shapely.geometry.Point(x, y)

            if (polygon.contains(point)):
                return (x,y)

    def __parse_pose_list(self, pose_list):
        valid_poses = []
        for pose_value in pose_list:
            vec = at.Vector3r(x_val=float(pose_value['x']), y_val=float(pose_value['y']), z_val=1000.0) # no Z, spawn is done with downward raycast to ground

            yaw = 0
            pitch = 0
            roll = 0

            if ('yaw' in pose_value):
                yaw = float(pose_value['yaw'])
            if ('pitch' in pose_value):
                pitch = float(pose_value['pitch'])
            if ('roll' in pose_value):
                roll = float(pose_value['roll'])

            rot = self.__to_quat(yaw, pitch, roll)
            pose = at.Pose(position_val=vec, orientation_val=rot)
            valid_poses.append(pose)

        return valid_poses

    def __parse_spawn_region(self, spawn_region):
        spawn_polygon_vertices = []
        for spawn_vertex in spawn_region:
            spawn_polygon_vertices.append((spawn_vertex['x'], spawn_vertex['y']))

        return shapely.geometry.polygon.Polygon(spawn_polygon_vertices)

    def __to_quat(self, yaw, pitch, roll):
        cy = math.cos(yaw * 0.5);
        sy = math.sin(yaw * 0.5);
        cp = math.cos(pitch * 0.5);
        sp = math.sin(pitch * 0.5);
        cr = math.cos(roll * 0.5);
        sr = math.sin(roll * 0.5);

        w = cy * cp * cr + sy * sp * sr;
        x = cy * cp * sr - sy * sp * cr;
        y = sy * cp * sr + cy * sp * cr;
        z = sy * cp * cr - cy * sp * sr;

        q = at.Quaternionr(x_val = -x, y_val = -y, z_val = z, w_val = w)
        
        return q

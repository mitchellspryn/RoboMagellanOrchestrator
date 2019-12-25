import datetime
import sys
import os
import json
import shapely
import uuid
import random
import numpy as np

import airsim
import airsim.airsim_types as at

import robo_magellan_orchestrator.starting_position as starting_position
import robo_magellan_orchestrator.cone_waypoint as cone_waypoint
import robo_magellan_orchestrator.goal_waypoint as goal_waypoint
import robo_magellan_orchestrator.raycast_utils as raycast_utils

class RoboMagellanCompetitionOrchestrator(object):
    def __init__(self, config_file_path):
        with open(config_file_path, 'r') as f:
            config_text = f.read()
        config_values = json.loads(config_text)

        if ('arenaBounds' not in config_values):
            raise ValueError('"arenaBounds" not specified.')
        self.arena_bounds = self.__parse_arena_bounds(config_values['arenaBounds'])

        if ('startPose' not in config_values):
            raise ValueError('"startPose" not specified.')
        self.start_pose = starting_position.StartingPosition(config_values['startPose'])

        if ('goalPoint' not in config_values):
            raise ValueError('"goalPoint" not specified.')
        self.goal_point = goal_waypoint.GoalWaypoint(config_values['goalPoint'])

        if ('cones' not in config_values):
            raise ValueError('"cones" not specified.')
        self.cones = self.__parse_cones(config_values['cones'])

        if ('timeLimit' not in config_values):
            raise ValueError('"timeLimit" not specified.')
        self.time_limit = datetime.timedelta(seconds=float(config_values['timeLimit']))

        self.debug_print_status = False
        if ('debugPrintStatus' in config_values):
            self.debug_print_status = config_values['debugPrintStatus']

        self.debug_draw = False
        if ('debugDraw' in config_values):
            self.debug_draw = config_values['debugDraw']

        self.end_run_on_collision = False
        if ('endRunOnCollision' in config_values):
            self.end_run_on_collision = config_values['endRunOnCollision']

        self.z_offset = 0
        if ('zOffset' in config_values):
            self.z_offset = float(config_values['zOffset'])

        self.start_time = None
        self.end_time = None
        self.max_end_time = None
        self.last_collision_time_stamp = None
        self.run_end_reason = None

    def set_debug_draw_enabled(self, draw_debug):
        self.debug_draw = draw_debug

    def set_random_seed(self, random_seed):
        random.seed(random_seed)
        np.random.seed(random_seed)

    def start_new_run(self, client):
        self.goal_point.reset()
        self.goal_point.spawn(client)
        
        for cone in self.cones:
            cone.reset()
            cone.spawn(client)

        self.start_pose.spawn(client, self.z_offset)

        debug_draw_request = at.DrawableShapeRequest(shapes={}, persist_unmentioned=False)

        if (self.debug_draw):
            debug_draw_request = self.__get_debug_shapes_to_draw(client)

        client.simSetDrawableShapes(debug_draw_request)

        self.start_time = datetime.datetime.utcnow()
        self.end_time = None
        self.max_end_time = self.start_time + self.time_limit
        self.run_complete = False
        self.elapsed_seconds = 0

    def run_tick(self, client):
        if (self.end_time != None or self.run_complete):
            return

        now = datetime.datetime.utcnow()
        self.elapsed_seconds = (now - self.start_time).seconds
        if (now > self.max_end_time):
            self.end_time = now
            self.run_complete = True
            self.run_end_reason = 'time limit exceeded.'
            return

        pose = client.simGetVehiclePose()
        pose_point = shapely.geometry.Point(pose.position.x_val, pose.position.y_val)

        if (not self.arena_bounds.contains(pose_point)):
            self.end_time = now
            self.run_complete = True
            self.run_end_reason = 'out of bounds.'

        collision_info = client.simGetCollisionInfo()
        if (collision_info.has_collided and collision_info.time_stamp != self.last_collision_time_stamp):
            object_name = collision_info.object_name
            collided_with_cone = False
            
            for cone in self.cones:
                if cone.random_name == object_name:
                    if not(cone.visited):
                        cone.set_visited(self.elapsed_seconds)
                    collided_with_cone = True

            if not collided_with_cone and self.end_run_on_collision:
                self.end_time = now
                self.run_complete = True
                self.run_end_reason = 'collision with {0}.'.format(object_name)
                return

        if (self.goal_point.is_bot_at_goal(client)):
            if not (self.goal_point.visited):
                self.goal_point.set_visited(self.elapsed_seconds)
                self.end_time = now
                self.run_complete = True
                self.run_end_reason = 'goal reached.'

    def get_run_score(self, client):
        if (not self.run_complete 
            or self.end_time is None
            or not self.goal_point.visited):
            return 0

        starting_score = (self.end_time - self.start_time).seconds
        for cone in self.cones:
            if (cone.visited):
                starting_score = starting_score * cone.bonus_multiplier

        return starting_score

    def get_run_summary(self, client):
        now = datetime.datetime.utcnow()

        summary = {}
        summary['runComplete'] = self.run_complete
        summary['runStartTime'] = self.start_time
        summary['runEndTime'] = self.end_time
        summary['now'] = now
        summary['elapsedTime'] = (now - self.start_time).seconds
        summary['score'] = self.get_run_score(client)
        summary['runEndReason'] = self.run_end_reason

        summary['coneInfo'] = []
        
        for cone in self.cones:
            cone_info = {}
            cone_info['id'] = cone.random_name
            cone_info['pose'] = cone.spawn_pose
            cone_info['visited'] = cone.visited
            cone_info['visitedTimeStamp'] = cone.visited_time_stamp
            cone_info['bonusMultiplier'] = cone.bonus_multiplier

            summary['coneInfo'].append(cone_info)

        summary['goalInfo'] = {}
        summary['goalInfo']['pose'] = self.goal_point.spawn_pose
        summary['goalInfo']['visited'] = self.goal_point.visited
        summary['goalInfo']['visitedTimeStamp'] = self.goal_point.visited_time_stamp
        summary['goalInfo']['closestDistance'] = self.goal_point.closest_distance

        return summary

    def get_run_summary_string(self, client):
        summary = self.get_run_summary(client)

        summary_text = '==============================================\n'
        summary_text += 'Summary \n'
        summary_text += 'Current time: {0}.\n'.format(summary['now'])
        summary_text += 'RunStartTime: {0}.\n'.format(summary['runStartTime'])
        summary_text += 'Elapsed time: {0} seconds.\n'.format(summary['elapsedTime'])

        if (summary['runComplete']):
            summary_text += 'RunEndTime: {0}.\n Score: {1:.4f}\nRun End Reason: {2}'.format(summary['runEndTime'], summary['score'], summary['runEndReason'])
        else:
            summary_text += 'The run is still ongoing. Score cannot be computed.\n'

        summary_text += '\n'
        summary_text += 'Cone Statuses:\n'
        for cone_info in summary['coneInfo']:
            summary_text += '\tCone name: {0}.\n'.format(cone_info['id'])

            pose_vec = cone_info['pose'].position
            summary_text += '\t\tCone position: <{0:.2f}, {1:.2f}, {2:.2f}>.\n'.format(pose_vec.x_val, pose_vec.y_val, pose_vec.z_val)
            summary_text += '\t\tCone multiplier: {0}.\n'.format(cone_info['bonusMultiplier'])

            if (cone_info['visited']):
                summary_text += '\t\tCone was visited at time: {0:.1f}.\n'.format(cone_info['visitedTimeStamp'])
            else:
                summary_text += '\t\tCone has not been visited.'

            summary_text += '\n'

        summary_text += 'Goal Status:\n'
        goal_pose = summary['goalInfo']['pose'].position
        summary_text += '\tGoal position: <{0:.2f}, {1:.2f}, {2:.2f}>\n'.format(goal_pose.x_val, goal_pose.y_val, goal_pose.z_val)
        if (summary['goalInfo']['visited']):
            summary_text += '\tGoal was visited at time {0:.1f}.\n'.format(summary['goalInfo']['visitedTimeStamp'])
        else:
            summary_text += '\tGoal has not been visited. The closest distance achieved during the run was {0:.3f} m.\n'.format(summary['goalInfo']['closestDistance'])

        summary_text += '==============================================\n'

        return summary_text

    def clean_up_run(self, client):
        for cone in self.cones:
            cone.delete(client)

    def __parse_arena_bounds(self, arena_bounds_config):
        arena_bounds_vertices = []
        for vertex in arena_bounds_config:
            arena_bounds_vertices.append((vertex['x'], vertex['y']))

        return shapely.geometry.polygon.Polygon(arena_bounds_vertices)

    def __parse_cones(self, cones_config):
        cones = []
        for cone_config in cones_config:
            cones.append(cone_waypoint.ConeWaypoint(cone_config))

        return cones

    def __get_debug_shapes_to_draw(self, client):
        debug_alpha = 100
        debug_thickness = 10
        shapes = at.DrawableShapeRequest(shapes={}, persist_unmentioned=False)

        # Arena bounds
        shapes = self.__build_debug_polygon(self.arena_bounds, (0, 0, 255, debug_alpha), shapes, client, thickness=debug_thickness)

        # Cone spawn bounds
        for cone in self.cones:
            cone_z, _ = raycast_utils.get_ground(cone.spawn_pose.position.x_val, cone.spawn_pose.position.y_val, client)
            shapes = client.addDrawableShapeLine(shapes, 
                                                 str(uuid.uuid4()),
                                                 '',
                                                 cone.spawn_pose.position.x_val,
                                                 cone.spawn_pose.position.y_val,
                                                 cone_z + 0.4,
                                                 cone.spawn_pose.position.x_val,
                                                 cone.spawn_pose.position.y_val,
                                                 10,
                                                 debug_thickness,
                                                 0, 
                                                 255,
                                                 0,
                                                 debug_alpha)

            if (cone.spawn_region is not None):
                shapes = self.__build_debug_polygon(cone.spawn_region, (255, 255, 0, debug_alpha), shapes, client, thickness=debug_thickness)

        # Goal pose
        # Do raycast to get normal to determine how to orient the circle
        goal_pose_z, normal = raycast_utils.get_ground(self.goal_point.spawn_pose.position.x_val, self.goal_point.spawn_pose.position.y_val, client)
        shapes = client.addDrawableShapeCircle(shapes, 
                                               str(uuid.uuid4()),
                                               '',
                                               self.goal_point.spawn_pose.position.x_val,
                                               self.goal_point.spawn_pose.position.y_val,
                                               self.goal_point.spawn_pose.position.z_val + 0.1,
                                               normal.x_val,
                                               normal.y_val, 
                                               normal.z_val,
                                               self.goal_point.position_tolerance ** 0.5,
                                               debug_thickness,
                                               64,
                                               255, 
                                               0,
                                               0,
                                               debug_alpha)

        if (self.goal_point.spawn_region is not None):
            shapes = self.__build_debug_polygon(self.goal_point.spawn_region, (255, 0, 255, debug_alpha), shapes, client, thickness=debug_thickness)

        # Spawn pose
        # Do raycast to get normal to determine how to orient the circle
        spawn_z, normal = raycast_utils.get_ground(self.start_pose.spawn_pose.position.x_val, self.start_pose.spawn_pose.position.y_val, client)
        shapes = client.addDrawableShapeCircle(shapes, 
                                               str(uuid.uuid4()),
                                               '',
                                               self.start_pose.spawn_pose.position.x_val,
                                               self.start_pose.spawn_pose.position.y_val,
                                               self.start_pose.spawn_pose.position.z_val,
                                               normal.x_val,
                                               normal.y_val,
                                               normal.z_val,
                                               0.5,
                                               debug_thickness,
                                               64, 
                                               0,
                                               255,
                                               255,
                                               debug_alpha)

        if (self.start_pose.spawn_region is not None):
            shapes = self.__build_debug_polygon(self.start_pose.spawn_region, (0, 0, 0, debug_alpha), shapes, client, thickness=debug_thickness)

        return shapes

    def __build_debug_polygon(self, polygon, color_rgba, existing_shapes, client, spacing=0.3, num=3, thickness=40):
        # The first and last point will be the same
        polygon_coords = list(polygon.exterior.coords)

        for i in range(0, len(polygon_coords) - 1, 1):
            first_point = polygon_coords[i]
            second_point = polygon_coords[i+1]

            first_point_z, _ = raycast_utils.get_ground(first_point[0], first_point[1], client)
            second_point_z, _ = raycast_utils.get_ground(second_point[0], second_point[1], client)

            existing_shapes = client.addDrawableShapeLine(existing_shapes,
                                                            str(uuid.uuid4()),
                                                            '',
                                                            first_point[0],
                                                            first_point[1],
                                                            first_point_z,
                                                            first_point[0],
                                                            first_point[1],
                                                            first_point_z + (spacing*num),
                                                            thickness, 
                                                            color_rgba[0],
                                                            color_rgba[1],
                                                            color_rgba[2],
                                                            color_rgba[3])

            for i in range(1, num+1, 1):
                existing_shapes = client.addDrawableShapeLine(existing_shapes,
                                                                str(uuid.uuid4()),
                                                                '',
                                                                first_point[0],
                                                                first_point[1],
                                                                first_point_z + (i*spacing),
                                                                second_point[0],
                                                                second_point[1],
                                                                second_point_z + (i*spacing),
                                                                thickness, 
                                                                color_rgba[0],
                                                                color_rgba[1],
                                                                color_rgba[2],
                                                                color_rgba[3])

        return existing_shapes


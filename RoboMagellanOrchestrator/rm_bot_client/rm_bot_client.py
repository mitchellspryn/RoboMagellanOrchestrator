import math

import airsim
import airsim.airsim_types as at

class RmBotClient(airsim.UrdfBotClient, object):
    def __init__(self):
        super(RmBotClient, self).__init__()
        self.confirmConnection()
        self.enableApiControl(True)

        self.fl_joint_name = 'main_box_to_wheel_fl'
        self.fr_joint_name = 'main_box_to_wheel_fr'
        self.bl_joint_name = 'main_box_to_wheel_bl'
        self.br_joint_name = 'main_box_to_wheel_br'

    def drive(self, left_throttle, right_throttle):
        front_right_update_obj = at.UrdfBotControlledMotionComponentControlSignal(component_name=self.fr_joint_name, control_signal_values={'Value': right_throttle})
        front_left_update_obj = at.UrdfBotControlledMotionComponentControlSignal(component_name=self.fl_joint_name, control_signal_values={'Value': left_throttle})
        back_right_update_obj = at.UrdfBotControlledMotionComponentControlSignal(component_name=self.br_joint_name, control_signal_values={'Value': right_throttle})
        back_left_update_obj = at.UrdfBotControlledMotionComponentControlSignal(component_name=self.bl_joint_name, control_signal_values={'Value': left_throttle})

        self.updateControlledMotionComponentControlSignal(front_right_update_obj)
        self.updateControlledMotionComponentControlSignal(front_left_update_obj)
        self.updateControlledMotionComponentControlSignal(back_right_update_obj)
        self.updateControlledMotionComponentControlSignal(back_left_update_obj)

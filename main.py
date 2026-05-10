from src.backend.PluginManager.PluginBase import PluginBase
from src.backend.PluginManager.ActionHolder import ActionHolder

from .actions.TargetToggleAction.TargetToggleAction import TargetToggleAction


class PipeWeaverTargetStatus(PluginBase):
    def __init__(self):
        super().__init__()
        self.lm = self.locale_manager
        self.lm.set_to_os_default()

        self.target_toggle_action_holder = ActionHolder(
            plugin_base=self,
            action_base=TargetToggleAction,
            action_id="com_hubelix_PipeWeaverTargetStatus::TargetToggleAction",
            action_name="PipeWeaver Target Toggle",
        )
        self.add_action_holder(self.target_toggle_action_holder)

        self.register(
            plugin_name="PipeWeaver Target Status",
            github_repo="https://github.com/maxlhuber/streamcontroller-pipeweaver-target-status",
            plugin_version="0.1.1",
            app_version="1.5.0-beta.12",
        )

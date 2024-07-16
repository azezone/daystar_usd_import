# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio
import os
import omni.ext
import omni.kit.ui
import omni.kit.app
import omni.usd
import omni.kit.window.content_browser as content
from omni.kit.menu.utils import MenuItemDescription
from .export_options_window import ExportOptionsWindow
from .exporter import Exporter
import carb
from .dwtool import DWTool


def get_instance():
    global _global_instance
    return _global_instance


class AssetImporterExtension(omni.ext.IExt):
    EXPORT_MENU_NAME = "ExportToDW"

    def on_startup(self):
        carb.log_info(f"**********on_startup**********")
        global _global_instance
        _global_instance = self

        self._context_icon_menu_items = []
        self._app = omni.kit.app.get_app()
        self._exporter = Exporter()
        self._exporter.on_startup()
        self._export_option_window = None
        self._new_content_window = None
        self._file_menu_list = []
        self._register_menus()
        self.dwTool =DWTool()
        # self._update_sub = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(self.on_update)

    def on_shutdown(self):
        carb.log_info(f"**********on_shutdown**********")
        global _global_instance
        _global_instance = None

        self._unregister_menus()
        if self._export_option_window:
            self._export_option_window.destroy()
        self._export_option_window = None
        self._new_content_window = None
        self._exporter.on_shutdown()
        self._exporter = None

        # if self._update_sub:
        #     self._update_sub.unsubscribe()
        #     self._update_sub = None

    # def on_update(self,delta_time):
    #     carb.log_info(f"**********on_update*********")

    def _unregister_menus(self):
        if self._file_menu_list:
            omni.kit.menu.utils.remove_menu_items(self._file_menu_list, "File")
            self._file_menu_list.clear()

    def _register_menus(self):
        def _on_file_export():
            usd_context = omni.usd.get_context()
            stage = usd_context.get_stage()
            self._on_file_export_menu_clicked(stage)
            # async def start_export():
            #     omni.kit.commands.execute("SelectAll", type="Material")
            #     await omni.kit.app.get_app().next_update_async()
            #     await omni.kit.app.get_app().next_update_async()
            #     omni.kit.undo.undo()
            #     omni.kit.commands.execute("SelectAll", type="Shader")
            #     await omni.kit.app.get_app().next_update_async()
            #     await omni.kit.app.get_app().next_update_async()
            #     omni.kit.undo.undo()
            #     await omni.kit.app.get_app().next_update_async()

            #     usd_context = omni.usd.get_context()
            #     stage = usd_context.get_stage()
            #     self._on_file_export_menu_clicked(stage)

            # asyncio.ensure_future(start_export())

        def enable_export_menu():
            return omni.usd.get_context().get_stage() is not None

        self._file_menu_list = [
            MenuItemDescription(
                name=self.EXPORT_MENU_NAME,
                glyph="none.svg",
                appear_after="Save Flattened As...",
                enable_fn=enable_export_menu,
                onclick_fn=_on_file_export,
            )
        ]

        omni.kit.menu.utils.add_menu_items(self._file_menu_list, "File")

    def _get_current_dir_in_content_window(self):
        if not self._new_content_window:
            self._new_content_window = content.get_content_window()
        return self._new_content_window.get_current_directory()

    def _on_file_export_menu_clicked(self, stage):
        current_dir = self._get_current_dir_in_content_window()
        carb.log_info(f"current_dir:{current_dir}")
        script_path = os.path.abspath(__file__)
        carb.log_info(f"script_path:{script_path}")
        display_name = stage.GetRootLayer().GetDisplayName()
        usd_path = stage.GetRootLayer().identifier.replace("\\", "/")
        carb.log_info(f"usd_path:{usd_path}")
        root_path = os.path.dirname(script_path)
        root_path = root_path.replace("file:/","")
        root_path = os.path.join(root_path,"../../../../data")
        carb.log_info(f"root_path:{root_path}")

        file_name, _ = os.path.splitext(display_name)
        if not self._export_option_window:
            self._export_option_window = ExportOptionsWindow(None)
        
        self.out_put_path = os.path.join(root_path, f"temp.glb")
        self.target_file_name = file_name
        self.out_put_path = self.out_put_path.replace("\\", "/")
        carb.log_info(f"out_put_path:{self.out_put_path}")
        if os.path.exists(self.out_put_path):
            carb.log_info("remove file....." + self.out_put_path)
            os.remove(self.out_put_path)
        # usd_path = stage.GetRootLayer().identifier.replace("\\", "/")
        # self._export_option_window.set_farm_export_fn(lambda: (usd_path, out_put_path))
        self._export_option_window.show(self.out_put_path)
        self._export_option_window.set_import_fn(
            lambda context: self._exporter.create_usd_export_task(
                stage, self.out_put_path, context, self._asset_convert_finished)
        )

    def _asset_convert_finished(self,success):
        carb.log_info(f"asset_convert_finished:{success}")
        self.dwTool.uploadAssetToDW( self.target_file_name,self.out_put_path)

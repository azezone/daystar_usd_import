import os
import asyncio
import tempfile
import carb
import omni.client
import omni.kit.window.content_browser as content
import omni.kit.asset_converter as converter
import omni.kit.notification_manager as nm
from .utils import Utils
from omni.kit.usd.collect.collector import FlatCollectionTextureOptions
from omni.kit.tool.collect import get_instance as get_collect_instance

from .progress_popup import ProgressPopup
from pxr import Usd, UsdUtils, UsdShade


class Exporter:
    def on_startup(self):
        self._waiting_popup_convert = None

    def on_shutdown(self):
        pass

    def _show_waiting_popup_convert(self):
        if not self._waiting_popup_convert:
            self._waiting_popup_convert = ProgressPopup("Converting...", status_text="Preparing...")

        self._waiting_popup_convert.status_text = "Preparing..."
        self._waiting_popup_convert.progress = 0.0
        self._waiting_popup_convert.show()

    async def _start_usd_export_internal(self, stage: Usd.Stage, output_path, asset_convert_context,convert_callback, is_collected=False):
        def convert_progress_callback(progress, total):
            self._waiting_popup_convert.progress = float(progress) / total

        self._show_waiting_popup_convert()

        usd_path = stage.GetRootLayer().identifier
        usd_path = usd_path.replace("\\", "/")
        usd_file_name = os.path.basename(usd_path)
        self._waiting_popup_convert.status_text = f"Exporting {usd_file_name}..."
        carb.log_info(f"Exporting {usd_path} to {output_path}...")

        stage_cache = UsdUtils.StageCache.Get()
        stage_id = stage_cache.GetId(stage).ToString()
        if not stage_id:
            stage_id = stage_cache.Insert(stage)

        if not stage_id:
            carb.log_error(f"Failed to export {usd_path} since it's not cached in UsdStageCache.")
            nm.post_notification(
                f"Failed to export {os.path.basename(usd_file_name)} since it's not cached in UsdStageCache.",
                status=nm.NotificationStatus.WARNING,
            )
            return
        if not is_collected:
            converter_task = converter.get_instance().create_converter_task(
                stage_id, output_path, convert_progress_callback, asset_convert_context
            )
        else:
            # for collected stage, we use the path to converter
            converter_task = converter.get_instance().create_converter_task(
                usd_path, output_path, convert_progress_callback, asset_convert_context
            )
        self._waiting_popup_convert.set_cancel_fn(lambda: converter_task.cancel())
        success = await converter_task.wait_until_finished()
        if not success:
            nm.post_notification(
                f"Failed to export {usd_file_name}.\n" "Please check console for more details.",
                status=nm.NotificationStatus.WARNING,
            )
        self._waiting_popup_convert.set_cancel_fn(None)
        self._waiting_popup_convert.progress = 0.0
        self._waiting_popup_convert.hide()
        self._refresh_current_directory()
        if convert_callback:
            convert_callback(success)

    def create_usd_export_task(self, stage: Usd.Stage, output_path, asset_converter_context,convert_callback):
        usd_path = stage.GetRootLayer().identifier
        usd_path = usd_path.replace("\\", "/")
        usd_file_name = os.path.basename(usd_path)

        # OM-44603: collect the usd_path and open the collected path in a new stage
        # and then bake it's material and then export the baked stage
        # Check the file is usd and is exist
        if asset_converter_context.bake_mdl_material and \
            Utils.is_usd(usd_path) and \
            omni.client.stat(usd_path)[0] == omni.client.Result.OK:

            collect_instance = get_collect_instance()
            manager = omni.kit.app.get_app().get_extension_manager()
            manager.set_extension_enabled_immediate("omni.mdl.distill_and_bake", True)
            with tempfile.TemporaryDirectory() as tmp_dir:
                def export_internal():
                    try:
                        import omni.mdl.distill_and_bake
                        collected_file = os.path.realpath(tmp_dir) + "\\" + usd_file_name
                        new_stage = Usd.Stage.Open(collected_file)
                        for prim in new_stage.Traverse():
                            if UsdShade.Material(prim):
                                distiller = omni.mdl.distill_and_bake.MdlDistillAndBake(prim, baking_to_new_material=asset_converter_context.export_mdl_gltf_extension)
                                distiller.distill()
                        new_stage.Save()
                        asyncio.ensure_future(self._start_usd_export_internal(new_stage, output_path, asset_converter_context, convert_callback, True))
                    except ImportError:
                        return asyncio.ensure_future(self._start_usd_export_internal(stage, output_path, asset_converter_context,convert_callback))

                collect_instance._start_collecting(usd_path,tmp_dir,False,True,False,FlatCollectionTextureOptions.FLAT, export_internal)
        else:
            return asyncio.ensure_future(self._start_usd_export_internal(stage, output_path, asset_converter_context,convert_callback))

    def _refresh_current_directory(self):
        content_window = content.get_content_window()
        if content_window:
            content_window.refresh_current_directory()
